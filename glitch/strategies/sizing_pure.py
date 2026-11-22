"""PROPUESTA (28-oct-2026; NEEDS HUMAN REVIEW, CLAUDE.md regla 4: toca sizing de capital). Tres palancas de tamaño, todas funciones PURAS y deterministas
(regla 1: nada de LLM en el camino de riesgo), todas APAGADAS por defecto (con el default el comportamiento es identico al actual).

1. Finish-line (Combine, Cerebro 1 / MES): usa todos los contratos configurados mientras falta mucho para la meta y se achica solo cuando un TP del tamaño
   configurado ya cubriria el faltante. Solo REDUCE respecto a CFG.nc. La meta efectiva incluye la regla de consistencia de Topstep (mejor dia <= 55 % de la
   meta original; si se excede, la meta sube a mejor_dia / 0.55): faltante = max(meta, mejor_dia / 0.55) − P&L del intento.
2. Regla de tamaño de la XFA (Cerebro 2 / MGC): `hi` micros mientras el saldo de la XFA (balance − balance inicial) < U, luego `lo`.
3. Bracket de la XFA: 364 (hoy) o 728 ticks (SL = TP), los dos unicos valores evaluados.

Respuestas de Topstep Support (pegadas por Eric, 28-oct-2026): cambiar el tamaño de un dia al otro segun el saldo / la distancia a la meta NO es conducta
prohibida ni disparador del Responsible Trading Program; un stop mayor que el MLL esta permitido (el MLL se vigila en tiempo real con P&L no realizado) y los
brackets no estan prohibidos. Los umbrales numericos del RTP NO estan publicados (DESCONOCIDO).
"""
from __future__ import annotations

import math
from typing import Optional

MODES = ("fixed", "finish_line")
CONSISTENCY_PCT = 0.55                       # Topstep: mejor dia <= 55 % de la meta original (respuesta de Support, 28-oct-2026)
XFA_BRACKETS = (364, 728)                    # unicos valores evaluados (SL = TP en ticks de MGC)
# Geometrías (SL, TP) en ticks de MGC modeladas en experimentos/estructura (SEGURO_MGC, 1-nov-2026): las dos de hoy y dos con TP mayor que el SL. Nada fuera de esta lista se acepta.
# (364, 182) se agrega el 20-nov-2026 (LUNES8B/LUNES9B/LUNES11 en experimentos/estructura): TP MENOR que el SL = perfil «perdedor mayor que ganador», motivo citado del RTP (umbrales no publicados).
# (500, 250) se agrega el 21-nov-2026 (LUNES16/LUNES17): misma bandera TP < SL; con 12 micros el MLL liquida a ~167 ticks en contra, antes del SL de 500. «500/200» NO es una geometria modelada y se rechaza.
XFA_GEOMETRIES = ((364, 364), (728, 728), (364, 728), (120, 360), (364, 182), (500, 250))
XFA_DIRECTIONS = ("alternate", "always_short", "always_long")
XFA_PAYOUT_DROP_TOL_USD = 100.0              # una baja de saldo >= esto entre cierres, no explicada por el P&L del trade, se toma como cobro hecho (el cobro minimo son $125)
XFA_START_BALANCE_USD = 50_000.0             # XFA 50K


# ── 1. Finish-line ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def tp_net_per_contract(tp_ticks: int, tick_value_usd: float, commission_roundturn: float, slip_ticks: float) -> float:
    """$ netos de un TP por contrato, con slippage de entrada adverso supuesto (el TP se ancla a la referencia, el fill entra peor)."""
    return (tp_ticks - slip_ticks) * tick_value_usd - commission_roundturn


def combine_need_usd(attempt_pnl: float, best_day_usd: float, profit_target: float, cons_pct: float = CONSISTENCY_PCT) -> float:
    """Faltante para pasar = max(meta, mejor_dia / cons_pct) − P&L del intento. Puede ser <= 0 (ya cruzo la meta: falta el dia de bloqueo o el 2.º dia)."""
    return max(float(profit_target), max(float(best_day_usd), 0.0) / cons_pct) - float(attempt_pnl)


def nc_for_day(mode: str, nc_cap: int, *, need_usd: float, tp_ticks: int, tick_value_usd: float,
               commission_roundturn: float, slip_assumed_ticks: float = 3.0) -> int:
    """Contratos para HOY. need_usd = combine_need_usd(...) (puede ser <= 0 si ya paso: se opera 1)."""
    if mode not in MODES:
        raise ValueError(f"modo invalido: {mode!r}")
    if nc_cap < 1:
        raise ValueError("nc_cap debe ser >= 1")
    if mode == "fixed":
        return int(nc_cap)
    per = tp_net_per_contract(tp_ticks, tick_value_usd, commission_roundturn, slip_assumed_ticks)
    if per <= 0:
        return int(nc_cap)              # TP no cubre costos: no hay base para achicar, se conserva la config validada
    n = math.ceil(max(need_usd, 0.0) / per - 1e-9)
    return int(min(max(n, 1), nc_cap))


# ── 2. Regla de tamaño de la XFA ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def parse_xfa_size_rule(raw: Optional[str]) -> Optional[tuple]:
    """'hi:U:lo' (p. ej. '5:1500:1') -> (hi, U, lo) o None si esta vacia/ausente. Lanza ValueError si esta mal formada (el llamador decide: el Pi se
    niega a arrancar la regla y conserva el tamaño de la señal)."""
    if raw is None or not raw.strip():
        return None
    parts = raw.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"regla de tamaño invalida {raw!r}: formato 'hi:U:lo'")
    hi, u, lo = int(parts[0]), float(parts[1]), int(parts[2])
    if not (1 <= lo < hi <= 12):            # 12 = escalado de MGC en la XFA con saldo < $1,500 (help.topstep.com); la regla evaluada es 5 -> 1
        raise ValueError(f"regla de tamaño invalida {raw!r}: se exige 1 <= lo < hi <= 12")
    if not (0 < u <= 10_000):
        raise ValueError(f"regla de tamaño invalida {raw!r}: U debe estar en (0, 10000]")
    return hi, u, lo


def xfa_nc_for_balance(balance_usd: float, start_balance_usd: float, hi: int, u_usd: float, lo: int) -> int:
    """hi micros mientras (balance − balance inicial) < U; si no, lo. Es la regla `np.where(st.b < U, hi, lo)` evaluada en opt_xfa_reglas.py."""
    return int(hi if (float(balance_usd) - float(start_balance_usd)) < float(u_usd) else lo)


def parse_xfa_lastday(raw: Optional[str]) -> Optional[tuple]:
    """'AAAA-MM-DD:n' (p. ej. '2026-11-27:12') -> (fecha, n) o None si esta vacia. En esa fecha (hora de Chicago) el Pi opera n micros mientras no se haya
    cobrado todavia (palanca del viernes, LUNES9B). Lanza ValueError si esta mal formada (el Pi la deja APAGADA y lo registra)."""
    if raw is None or not raw.strip():
        return None
    parts = raw.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"palanca de ultimo dia invalida {raw!r}: formato 'AAAA-MM-DD:n'")
    import datetime as _dt
    d = _dt.date.fromisoformat(parts[0].strip())
    n = int(parts[1])
    if not 1 <= n <= 12:
        raise ValueError(f"palanca de ultimo dia invalida {raw!r}: n debe estar entre 1 y 12")
    return d, n


def xfa_payout_detected(expected_balance: Optional[float], balance_now: Optional[float], tol_usd: float = XFA_PAYOUT_DROP_TOL_USD) -> bool:
    """True si el saldo actual esta por DEBAJO del esperado (saldo previo al trade + P&L del trade) por mas de la tolerancia: lo que lo explica es un cobro (o un
    retiro) hecho entre cierres. Sin dato (None) -> False: no se adivina. Un falso positivo solo achica el tamaño (falla seguro)."""
    if expected_balance is None or balance_now is None:
        return False
    return float(balance_now) < float(expected_balance) - float(tol_usd)


def xfa_nc_plan(balance_usd: float, start_balance_usd: float, hi: int, u_usd: float, lo: int, *, latched: bool = False, post_nc: int = 1,
                lastday: Optional[tuple] = None, today=None) -> tuple:
    """(nc, motivo) del Pi para hoy. Base = regla hi:U:lo por saldo. (1) cobro hecho (candado): min(base, post_nc), sin excepciones; (2) palanca de ultimo dia: si hoy es la
    fecha y la base sigue siendo `hi` (todavia no se llego a U), n micros; (3) si no, la base. El saldo restante tras un cobro suele quedar < U: sin el candado la regla
    volveria a `hi` con el piso del MLL en $0."""
    base = xfa_nc_for_balance(balance_usd, start_balance_usd, hi, u_usd, lo)
    if latched:
        return int(min(base, post_nc)), f"cobro hecho (candado): {min(base, post_nc)} micros"
    if lastday is not None and today is not None and today == lastday[0] and base == hi:
        return int(lastday[1]), f"ultimo dia {lastday[0]}: {lastday[1]} micros"
    return int(base), f"regla {hi}:{u_usd:g}:{lo}: {base} micros"


def xfa_direction_from_env(raw_dir: Optional[str], raw_until: Optional[str], today, default: str = "alternate") -> tuple:
    """(direccion, nota) del scheduler MGC. GLITCH_XFA_DIRECTION (always_short | always_long | alternate; alias short | long) SOLO se aplica si GLITCH_XFA_DIRECTION_UNTIL
    (AAAA-MM-DD, inclusive) es una fecha valida y `today` no la pasa: asi un override olvidado vuelve solo a `default`. Sin variable: (default, None). Cualquier error -> (default, motivo)."""
    if raw_dir is None or not raw_dir.strip():
        return default, None
    d = {"short": "always_short", "long": "always_long"}.get(raw_dir.strip().lower(), raw_dir.strip().lower())
    if d not in XFA_DIRECTIONS:
        return default, f"GLITCH_XFA_DIRECTION={raw_dir!r} no valida (alternate | always_short | always_long): se usa {default}"
    import datetime as _dt
    try:
        until = _dt.date.fromisoformat((raw_until or "").strip())
    except ValueError:
        return default, f"GLITCH_XFA_DIRECTION={raw_dir!r} exige GLITCH_XFA_DIRECTION_UNTIL=AAAA-MM-DD (fecha valida): se ignora y se usa {default}"
    if today > until:
        return default, f"GLITCH_XFA_DIRECTION={d} expiro el {until}: se usa {default}"
    return d, f"GLITCH_XFA_DIRECTION={d} activa hasta {until} (inclusive)"


# ── 3. Bracket de la XFA ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def xfa_bracket_from_env(raw: Optional[str], default: int = 364) -> int:
    """Bracket (SL = TP en ticks) de la señal MGC. Solo los valores evaluados; cualquier otra cosa -> el default (el llamador lo registra)."""
    if raw is None or not raw.strip():
        return default
    try:
        v = int(raw.strip())
    except ValueError:
        return default
    return v if v in XFA_BRACKETS else default


def xfa_geometry_from_env(sl_raw: Optional[str], tp_raw: Optional[str], default_sl: int = 364, default_tp: int = 364) -> tuple:
    """(sl, tp, ok) de la señal MGC a partir de GLITCH_XFA_BRACKET_TICKS (SL) y GLITCH_XFA_TP_TICKS (TP). Sin variables: el default. Con solo SL, TP = SL (comportamiento de hoy).
    Solo se aceptan las geometrías de XFA_GEOMETRIES; cualquier otra combinación o valor ilegible devuelve el default con ok=False (el llamador lo registra y la señal no cambia)."""
    def _int(raw):
        if raw is None or not raw.strip():
            return None
        try:
            return int(raw.strip())
        except ValueError:
            return -1
    sl, tp = _int(sl_raw), _int(tp_raw)
    if sl is None and tp is None:
        return default_sl, default_tp, True
    sl = default_sl if sl is None else sl
    tp = sl if tp is None and sl_raw is not None and sl_raw.strip() else (default_tp if tp is None else tp)
    if (sl, tp) in XFA_GEOMETRIES:
        return sl, tp, True
    return default_sl, default_tp, False
