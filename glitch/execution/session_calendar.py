"""
Glitch — Calendario de sesion: flatten condicional en dias de cierre anticipado (25-sep-2026)
================================================================================================
Fuente oficial: help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours -- "Close all positions 15 minutes
before early close (e.g., close by 11:45 CT for a 12:00 CT close)". Las posiciones abiertas pasada esa hora se liquidan
automaticamente. Los schedulers de produccion hacian flatten FIJO a las 14:30 CT sin excepcion -- en los dias de cierre anticipado
que SI se operan (27-nov y 24-dic-2026) la posicion habria sido liquidada por Topstep antes de que el scheduler la cerrara,
sin registro fiel del resultado.

Aqui vive UNICAMENTE el dato de calendario (fuente unica para ambos schedulers, sin acoplarlos entre si). Los feriados de mercado
cerrado siguen en is_trading_day() de cada scheduler.

EARLY_CLOSE_BY_CT = hora oficial "Close positions by" (CT). El flatten del scheduler es esa hora menos FLATTEN_MARGIN_MIN (30
min, mismo margen de siempre: 14:30 vs el corte normal de 15:10 CT).
26-nov-2026 (Thanksgiving) figura aqui como defensa en profundidad: hoy is_trading_day() ya lo excluye por completo.
Topstep solo publico 2026 y el 1-ene-2027 (cerrado); agregar fechas nuevas cuando se publiquen.
"""
import datetime as dt

NORMAL_FLATTEN_MIN = 14 * 60 + 30
FLATTEN_MARGIN_MIN = 30
EARLY_CLOSE_BY_CT = {
    dt.date(2026, 11, 26): (11, 45),
    dt.date(2026, 11, 27): (12, 0),
    dt.date(2026, 12, 24): (12, 0),
}


def flatten_minutes_ct(d: dt.date) -> int:
    """Minutos desde medianoche CT a partir de los cuales hay que hacer flatten ese dia."""
    close_by = EARLY_CLOSE_BY_CT.get(d)
    if close_by is None:
        return NORMAL_FLATTEN_MIN
    return min(NORMAL_FLATTEN_MIN, close_by[0] * 60 + close_by[1] - FLATTEN_MARGIN_MIN)


def is_flatten_time(now: dt.datetime) -> bool:
    """now = datetime en CT."""
    return now.hour * 60 + now.minute >= flatten_minutes_ct(now.date())
