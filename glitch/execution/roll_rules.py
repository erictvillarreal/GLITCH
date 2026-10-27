"""
Glitch — Regla de roll del oro (J4-f, 26-oct-2026): funciones PURAS, sin red y sin variables de entorno.
Movidas SIN cambios desde execution/contracts.py (T4, 12-oct-2026) para que pi/pi_executor.py pueda usarlas: execution/contracts.py exige MASSIVE_API_KEY al
importarse (los schedulers de Railway la tienen; el Pi NO -- ver el comentario de arranque de pi_executor.py) y por eso el Pi no puede importarlo.
execution/contracts.py las re-exporta con los mismos nombres. NEEDS HUMAN REVIEW.
"""
import datetime as dt
import re

_MONTH_CODES = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}

# Regla de roll por producto (T4, 12-oct-2026; NEEDS HUMAN REVIEW). Topstep exige operar el front month = el vencimiento de mayor VOLUMEN
# (help.topstep.com/8284108), no el de vencimiento mas cercano. Para el oro (GC/MGC) la liquidez migra del contrato bimestral que entra en mes de
# entrega al siguiente ANTES del primer dia de aviso (FND = ultimo dia habil del mes previo al de entrega): MGCV6 (oct-2026) se quedo sin barras el
# 1-oct-2026 (incidente de 700+ min sin datos, GLITCH_RESEARCH_LOG.md) -- justo despues de su FND (30-sep). `resolve_front_month` elegia el vencimiento
# mas cercano, o sea MGCV6 hasta su ultimo dia de negociacion (~28-oct). Regla determinista (no depende de la API): se descarta el contrato cuando
# faltan <= `bdays_before_fnd` dias habiles (solo fines de semana; feriados no modelados) para su FND. Los meses activos limitan los candidatos
# (oro: feb/abr/jun/ago/oct/dic); si el filtro dejara cero candidatos, se vuelve al comportamiento anterior.
ROLL_RULES = {
    "MGC": {"active_months": {2, 4, 6, 8, 10, 12}, "bdays_before_fnd": 2},
    "GC": {"active_months": {2, 4, 6, 8, 10, 12}, "bdays_before_fnd": 2},
}


def _ticker_month_year(product: str, ticker: str, ref_year: int):
    m = re.match(rf"^{re.escape(product)}([FGHJKMNQUVXZ])(\d{{1,2}})$", ticker)
    if not m:
        return None
    month = _MONTH_CODES[m.group(1)]
    yy = int(m.group(2))
    year = (ref_year // 100) * 100 + yy if yy >= 10 else (ref_year // 10) * 10 + yy
    if year < ref_year - 5:
        year += 10
    return month, year


def _add_business_days(d: dt.date, n: int) -> dt.date:
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        d += dt.timedelta(days=step)
        if d.weekday() < 5:
            left -= 1
    return d


def first_notice_day(year: int, month: int) -> dt.date:
    """FND de un contrato de metales con entrega en (year, month): ultimo dia habil (lun-vie) del mes anterior."""
    first = dt.date(year, month, 1)
    d = first - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def apply_roll_rule(product: str, candidates: list, today: dt.date) -> list:
    """candidates: [(ticker, last_trade_date_iso)] ordenados por vencimiento. Aplica ROLL_RULES[product] si existe; si el filtro vaciara la lista, devuelve la original."""
    rule = ROLL_RULES.get(product)
    if not rule:
        return candidates
    kept = []
    for ticker, ltd in candidates:
        my = _ticker_month_year(product, ticker, today.year)
        if my is None:
            continue
        month, year = my
        if month not in rule["active_months"]:
            continue
        cutoff = _add_business_days(first_notice_day(year, month), -rule["bdays_before_fnd"])
        if today >= cutoff:
            continue
        kept.append((ticker, ltd))
    return kept or candidates
