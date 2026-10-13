"""Metricas de friccion por sesion — funciones PURAS. Convencion de signo: positivo = adverso para el trader. Los precios llegan ya extraidos por el script de entrada
(pi/ops/friction_collect.py); aqui solo se hace la aritmetica y el semaforo."""
from __future__ import annotations
import re
from typing import Optional

from monitoring.thresholds import classify, worst, GREEN, YELLOW, RED, NODATA, HARD_RED_EVENTS


def entry_slip_ticks(side: int, ref_price: float, fill_price: float, tick: float) -> float:
    """side=+1 compra / -1 venta. Compra que llena MAS ARRIBA que la referencia = adverso (+)."""
    return side * (fill_price - ref_price) / tick


def flatten_slip_ticks(side: int, ref_price: float, exit_fill: float, tick: float) -> float:
    """Salida a mercado: para una posicion larga, vender MAS ABAJO que la referencia = adverso (+)."""
    return side * (ref_price - exit_fill) / tick


def tp_cross_ticks(side: int, tp_price: float, extreme_after_entry: float, tp_filled: bool, tick: float) -> Optional[float]:
    """Ticks que el precio CRUZO el TP sin que el limite se llenara. None si no hubo toque; 0 si se lleno. `extreme_after_entry` = maximo (largo) o minimo (corto) del
    precio entre la entrada y la salida, de las barras de 1 min."""
    if tp_filled:
        return 0.0
    crossed = side * (extreme_after_entry - tp_price) / tick
    return crossed if crossed >= 0 else None


def stop_slip_usd_per_contract(side: int, stop_price: float, exit_fill: float, tick_value_usd: float, tick: float) -> float:
    """Exceso del llenado de un stop sobre su precio, USD por contrato (positivo = peor que el stop)."""
    return side * (stop_price - exit_fill) / tick * tick_value_usd


_ERR_RE = re.compile(r"\b(ERROR|CRITICAL)\b")
_HARD_PATTERNS = {
    "unprotected_bracket": re.compile(r"sin (SL|stop|proteccion)|bracket.*(no se coloco|fallo)|entrada sin proteccion", re.I),
    "duplicate_order": re.compile(r"orden duplicada|duplicate order", re.I),
    "unreconciled_position": re.compile(r"posicion (huerfana|no conciliada|sin registro)|untracked position", re.I),
    "wrong_account": re.compile(r"cuenta .*(no coincide|vetada|denylist)|account .*not allowed", re.I),
}


def scan_executor_log(lines, date_prefix: str) -> dict:
    """Cuenta fallos y eventos rojos duros en las lineas de pi_executor.log de UN dia (las lineas empiezan con la fecha CT 'YYYY-MM-DD').
    Los patrones son heuristicas sobre el formato de log actual: NO VERIFICADO contra una corrida real hasta el ensayo en Practice."""
    errors = 0; hard = {k: 0 for k in HARD_RED_EVENTS}
    for ln in lines:
        if not ln.startswith(date_prefix):
            continue
        if _ERR_RE.search(ln):
            errors += 1
        for k, rx in _HARD_PATTERNS.items():
            if rx.search(ln):
                hard[k] += 1
    return {"errors": errors, "hard": hard}


def build_record(date: str, product: str, nc: int, side: int, tick: float, tick_value_usd: float, *, ref_price=None, entry_fill=None, tp_price=None,
                 tp_filled=None, extreme_after_entry=None, exit_type=None, exit_fill=None, exit_ref=None, stop_price=None, commission_total=None,
                 log_scan=None, flat_by_1435=None) -> dict:
    """Registro diario de friccion (una fila por sesion y producto). Todos los campos opcionales pueden faltar (None): la metrica queda 'sin datos', nunca se inventa."""
    rec = {"date": date, "product": product, "nc": nc, "side": side}
    rec["entry_slip_ticks"] = None if None in (ref_price, entry_fill) else round(entry_slip_ticks(side, ref_price, entry_fill, tick), 3)
    rec["tp_cross_ticks"] = None if None in (tp_price, extreme_after_entry, tp_filled) else tp_cross_ticks(side, tp_price, extreme_after_entry, bool(tp_filled), tick)
    rec["flatten_slip_ticks"] = (round(flatten_slip_ticks(side, exit_ref, exit_fill, tick), 3)
                                 if exit_type == "FLATTEN" and None not in (exit_ref, exit_fill) else None)
    rec["stop_slip_usd_per_ct"] = (round(stop_slip_usd_per_contract(side, stop_price, exit_fill, tick_value_usd, tick), 2)
                                   if exit_type == "SL" and None not in (stop_price, exit_fill) else None)
    rec["exit_type"] = exit_type
    rec["commission_per_contract_rt"] = None if commission_total is None or not nc else round(commission_total / nc, 3)
    rec["api_errors"] = None if log_scan is None else log_scan["errors"]
    rec["hard_red"] = {} if log_scan is None else {k: v for k, v in log_scan["hard"].items() if v}
    if flat_by_1435 is False:
        rec["hard_red"]["open_after_1435"] = 1
    return rec


def record_colors(rec: dict) -> dict:
    return {m: classify(m, rec.get(m)) for m in ("entry_slip_ticks", "tp_cross_ticks", "flatten_slip_ticks", "stop_slip_usd_per_ct")}


def aggregate(records: list) -> dict:
    """Promedios/peores casos sobre una ventana de registros (p. ej. las ultimas 4 semanas) para el semaforo semanal."""
    def vals(k): return [r[k] for r in records if r.get(k) is not None]
    def mean(x): return sum(x) / len(x) if x else None
    sessions = len(records)
    fails = sum(r.get("api_errors") or 0 for r in records)
    hard = sum(sum((r.get("hard_red") or {}).values()) for r in records)
    out = {"sessions": sessions, "entry_n": len(vals("entry_slip_ticks")),
           "entry_slip_ticks": mean(vals("entry_slip_ticks")),
           "tp_cross_ticks": max(vals("tp_cross_ticks")) if vals("tp_cross_ticks") else None,
           "flatten_slip_ticks": mean(vals("flatten_slip_ticks")),
           "stop_slip_usd_per_ct": mean(vals("stop_slip_usd_per_ct")),
           "api_failures_per_20": (fails * 20.0 / sessions) if sessions else None,
           "hard_red_events": hard}
    out["colors"] = {m: classify(m, out[m]) for m in ("entry_slip_ticks", "tp_cross_ticks", "flatten_slip_ticks", "stop_slip_usd_per_ct", "api_failures_per_20")}
    return out
