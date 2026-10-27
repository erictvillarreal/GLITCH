"""PROPUESTA -- NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: toca el registro de ejecucion).

C3: slippage REAL de entrada en ticks. Convencion: positivo = ADVERSO (peor que la referencia pre-trade con la que se anclan TP/SL).
  LONG compra en `fill` > `ref` -> adverso; SHORT vende en `fill` < `ref` -> adverso.   slip_ticks = side * (fill - ref) / tick_size
Calculo manual para cualquier dia (lun 19 / mar 20-oct): side * (precio de fill de TopstepX - referencia del mensaje [OPEN] del Pi) / 0.25.
"""
from __future__ import annotations

from typing import Optional


def slippage_ticks(side: int, ref_price: Optional[float], fill_price: Optional[float], tick_size: float) -> Optional[float]:
    if side not in (1, -1) or ref_price is None or fill_price is None or tick_size <= 0:
        return None
    for v in (ref_price, fill_price):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            return None
    return round(side * (fill_price - ref_price) / tick_size, 2)


# ── G1a (24-oct-2026): tiempos de ejecucion -----------------------------------------------------------------------------------
_FILL_TIME_KEYS = ("fillTimestamp", "filledAt", "executionTimestamp", "updateTimestamp", "creationTimestamp")   # NO VERIFICADO cual trae Order/search


def parse_iso(ts) -> Optional[float]:
    """ISO-8601 (con 'Z' o desfase) -> epoch en segundos; None si no se puede."""
    import datetime as _dt
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def extract_fill_time(order_record: Optional[dict]) -> Optional[str]:
    """Primera marca de tiempo conocida del registro de la orden (la clave exacta del fill no esta verificada: se guarda cual se uso)."""
    if not order_record:
        return None
    for k in _FILL_TIME_KEYS:
        v = order_record.get(k)
        if isinstance(v, str) and parse_iso(v) is not None:
            return f"{k}={v}"
    return None


def build_exec_record(*, side: int, nc: int, tick_size: float, ref_price: float, t_signal_seen: float, t_ref_bar: Optional[str], t_ref_local: float,
                      t_send: float, t_ack: float, fill_price: Optional[float], fill_time: Optional[str], bid: Optional[float] = None,
                      ask: Optional[float] = None, t_prev_empty_poll: Optional[float] = None) -> dict:
    """Registro de ejecucion por orden de entrada. Tiempos locales en epoch (s); latencias en ms; `bid`/`ask` son None mientras no haya feed en vivo (SignalR)."""
    t_fill = parse_iso(fill_time.split("=", 1)[1]) if fill_time and "=" in fill_time else None
    t_bar = parse_iso(t_ref_bar)
    rec = {
        "side": side, "nc": nc, "ref_price": ref_price, "t_ref_bar": t_ref_bar, "t_ref_local": round(t_ref_local, 3),
        "t_signal_seen": round(t_signal_seen, 3), "t_send": round(t_send, 3), "t_ack": round(t_ack, 3),
        "fill_price": fill_price, "t_fill": fill_time, "bid": bid, "ask": ask,
        "slip_ticks": slippage_ticks(side, ref_price, fill_price, tick_size),
        "lat_signal_to_send_ms": round((t_send - t_signal_seen) * 1000),
        "lat_ref_to_send_ms": round((t_send - t_ref_local) * 1000),
        "lat_send_to_ack_ms": round((t_ack - t_send) * 1000),
        "lat_send_to_fill_ms": round((t_fill - t_send) * 1000) if t_fill is not None else None,
        "ref_bar_age_s": round(t_ref_local - t_bar, 1) if t_bar is not None else None,
        "poll_window_s": round(t_signal_seen - t_prev_empty_poll, 1) if t_prev_empty_poll is not None else None,   # cota superior del retraso por polling
    }
    return rec


def exit_slip_ticks(side: int, result: str, tp_price, sl_price, exit_price, tick_size: float):
    """Slippage de SALIDA respecto del disparador, en ticks, + = adverso (peor que el disparador). TP (limite): negativo = mejora de precio. SL (stop de mercado): positivo = deslizamiento.
    FLATTEN / UNKNOWN no tienen disparador: None. Parte H (24-oct-2026), H2."""
    if side not in (1, -1) or tick_size <= 0 or exit_price is None or result not in ("TP", "SL"):
        return None
    trig = tp_price if result == "TP" else sl_price
    if trig is None:
        return None
    return round(side * (trig - exit_price) / tick_size, 2)

