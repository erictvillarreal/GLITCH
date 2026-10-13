"""Alerta de margen — funciones PURAS. Practice: cojin = saldo + no realizado - piso del MLL; alerta si < $1,500 (pedido de Eric, 12-oct). Combine: exposicion de
liquidacion = distancia en TICKS entre el precio y el precio de liquidacion del MLL con la posicion abierta; amarillo <= 20 ticks, rojo <= 10 ticks.
El PISO del MLL NO viene de la API (NO VERIFICADO): se lleva con un libro propio de maximos de cierre (EOD) -- ver update_eod_ledger()."""
from __future__ import annotations
from typing import Optional

PRACTICE_MIN_CUSHION_USD = 1500.0
COMBINE_YELLOW_TICKS, COMBINE_RED_TICKS = 20.0, 10.0
REALERT_HOURS = 6.0


def mll_floor(kind: str, eod_high: float, start_balance: float, mll_distance: float) -> float:
    """Piso del MLL trailing EOD. Combine: se traba en el saldo inicial (piso = start - 0 al llegar). Practice (150K): mismo mecanismo con su propio mll_distance."""
    return min(eod_high - mll_distance, start_balance)


def update_eod_ledger(ledger: dict, eod_balance: float, date: str, start_balance: float) -> dict:
    """Actualiza el maximo de cierre (una vez por dia). El libro es {'eod_high': x, 'last_date': d}; sin historial se parte de start_balance."""
    out = dict(ledger or {})
    out.setdefault("eod_high", start_balance)
    if date != out.get("last_date"):
        out["eod_high"] = max(out["eod_high"], eod_balance)
        out["last_date"] = date
    return out


def cushion_usd(balance: float, unrealized: float, floor: float) -> float:
    return balance + unrealized - floor


def liquidation_ticks(cushion: float, nc: int, tick_value_usd: float) -> Optional[float]:
    if nc <= 0:
        return None
    return cushion / (nc * tick_value_usd)


def level(kind: str, cushion: float, nc: int = 0, tick_value_usd: float = 0.0) -> str:
    if kind == "practice":
        return "rojo" if cushion < PRACTICE_MIN_CUSHION_USD else "verde"
    ticks = liquidation_ticks(cushion, nc, tick_value_usd)
    if ticks is None:
        return "verde"          # sin posicion abierta no hay exposicion de liquidacion
    return "rojo" if ticks <= COMBINE_RED_TICKS else ("amarillo" if ticks <= COMBINE_YELLOW_TICKS else "verde")


def decide(kind: str, cushion: float, nc: int, tick_value_usd: float, date: str, now_ts: float, prev: dict) -> tuple:
    """Devuelve (nivel, accion, nuevo_estado). accion: 'alert' | 'escalate' | 'recovered' | 'none'. Una alerta por nivel y dia (+ re-aviso cada REALERT_HOURS si sigue en rojo); el estado
    solo debe persistirse si el mensaje SE ENVIO (mismo criterio que pi/ops/watchdog.py)."""
    lvl = level(kind, cushion, nc, tick_value_usd)
    prev_lvl = prev.get("level", "verde") if prev.get("date") == date else "verde"
    order = {"verde": 0, "amarillo": 1, "rojo": 2}
    if lvl == "verde":
        if prev_lvl != "verde":
            return lvl, "recovered", {"date": date, "level": "verde"}
        return lvl, "none", prev
    if order[lvl] > order[prev_lvl]:
        return lvl, ("escalate" if prev_lvl != "verde" else "alert"), {"date": date, "level": lvl, "last_alert_ts": now_ts}
    if lvl == "rojo" and now_ts - float(prev.get("last_alert_ts", 0)) >= REALERT_HOURS * 3600:
        return lvl, "alert", {"date": date, "level": lvl, "last_alert_ts": now_ts}
    return lvl, "none", prev
