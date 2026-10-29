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
