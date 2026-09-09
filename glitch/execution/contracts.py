"""
Glitch — Resolucion dinamica de contrato front-month (25-ago-2026)
=====================================================================
UNICA fuente de verdad de "que ticker exacto tradear hoy para el
producto X" -- importada por TODOS los schedulers en vivo
(scheduler/combo2d_scheduler.py, scheduler/geometry_scheduler.py).
Antes cada scheduler mantenia su propia copia (o, peor, un dict
hardcodeado que alguien tenia que acordarse de actualizar cada
trimestre a mano -- ver auditoria del 25-ago-2026).

Metodologia (misma que scripts/fetch_mes_2y.py, ver CLAUDE.md del repo
Kito): `date=<hoy>` point-in-time, `active=true`, excluir spreads/combos,
el "front month" = el contrato outright con vencimiento mas cercano.

Usa `requests` directo, NO la SDK `massive` -- la SDK se cuelga en
silencio en `list_futures_contracts` para algunos productos (confirmado
con MBT durante la extension a 7 productos de Camino B, sin excepcion
visible). `requests` directo con paginacion explicita y limite de
paginas no se cuelga.
"""
from __future__ import annotations
import os
import re
import datetime as dt
from typing import Callable, Optional

import numpy as np
import requests

MASSIVE_API_KEY = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
if not MASSIVE_API_KEY:
    raise RuntimeError(
        "FATAL: falta MASSIVE_API_KEY (o POLYGON_API_KEY) en el entorno. "
        "Sin fallback -- nunca hardcodear la key (ver auditoria 25-ago-2026)."
    )

BASE = "https://api.massive.com"
HEADERS = {"Authorization": f"Bearer {MASSIVE_API_KEY}"}

# Puntos de control para la alerta de vencimiento (09-sep-2026) -- antes
# alertaba TODOS los dias dentro de la ventana de 10 dias habiles,
# multiplicado por cada servicio que comparte el mismo contrato
# (GEOMETRY-MES y COMBO2D ambos alertando sobre MESU6 el mismo dia,
# todos los dias) -- reportado como spam. Ver GLITCH_RESEARCH_LOG.md,
# "Dos problemas reportados...", opcion (b) elegida sobre dedup via
# estado compartido (opcion a, requeria coordinacion entre servicios con
# riesgo de condicion de carrera) o consolidacion en un solo mensaje
# (opcion c, la mas invasiva arquitectonicamente).
FRONT_MONTH_ALERT_CHECKPOINTS = (10, 5, 2, 1)  # dias habiles restantes

# Mismo calendario de feriados que los 3 schedulers (duplicado
# deliberadamente, mismo criterio ya aplicado en cada uno -- dato
# estatico trivial, bajo riesgo de duplicacion). Usado SOLO para
# calcular el dia habil anterior (ver _previous_trading_day) -- no para
# decidir si ESTE modulo debe hacer nada, eso lo decide is_trading_day()
# de cada scheduler. Si algun scheduler actualiza su propio calendario
# sin actualizar este, la deteccion de checkpoints salteados podria
# desalinearse -- riesgo aceptado, mismo que ya existe entre los 3
# schedulers.
_HOLIDAYS = {
    (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
    (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)
}

_TICKER_RE_CACHE: dict[str, "re.Pattern"] = {}


def _is_trading_day(d: dt.date) -> bool:
    if d.weekday() >= 5:
        return False
    return (d.year, d.month, d.day) not in _HOLIDAYS


def _previous_trading_day(d: dt.date) -> dt.date:
    """
    Dia habil anterior a `d` (fin de semana + feriados). Usado para
    detectar si un checkpoint de vencimiento se salto por un feriado
    entre dos corridas reales del scheduler (busday_count de numpy NO
    conoce los feriados custom del calendario del proyecto, solo fines
    de semana -- un feriado puede hacer que `days_left` salte 2 en vez
    de 1 entre dos corridas reales, saltandose un checkpoint exacto).
    Puramente calculado desde la fecha de hoy -- sin estado persistido.
    """
    prev = d - dt.timedelta(days=1)
    while not _is_trading_day(prev):
        prev -= dt.timedelta(days=1)
    return prev


def _valid_outright_ticker(product: str, ticker: str) -> bool:
    """PRODUCT + 1 letra de mes (F,G,H,J,K,M,N,Q,U,V,X,Z) + 1-2 digitos de año."""
    if product not in _TICKER_RE_CACHE:
        _TICKER_RE_CACHE[product] = re.compile(rf"^{re.escape(product)}[FGHJKMNQUVXZ]\d{{1,2}}$")
    return bool(_TICKER_RE_CACHE[product].match(ticker))


def _get(path: str, params: dict, max_pages: int = 20) -> list[dict]:
    url = BASE + path
    out = []
    for _ in range(max_pages):
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("results", []))
        next_url = data.get("next_url")
        if not next_url:
            break
        url = next_url if next_url.startswith("http") else BASE + next_url
        params = {}
    return out


def resolve_front_month(product: str) -> tuple[str, str]:
    """
    Contrato outright (no spread/combo) con vencimiento mas cercano,
    vigente HOY. Devuelve (ticker, last_trade_date_iso).

    Lanza si no encuentra ninguno -- fallar ruidosamente es preferible a
    tradear un ticker adivinado o quedarse con uno vencido.
    """
    today_str = dt.date.today().isoformat()
    results = _get("/futures/v1/contracts",
                    {"product_code": product, "date": today_str, "active": "true", "limit": 250})
    candidates = []
    for c in results:
        if c.get("type") and c["type"] != "single":
            continue  # excluir combos/spreads explicitamente
        ticker = c.get("ticker")
        ltd = c.get("last_trade_date")
        if ticker and ltd and _valid_outright_ticker(product, ticker):
            candidates.append((ticker, ltd))
    if not candidates:
        raise RuntimeError(f"resolve_front_month: sin contratos activos validos para {product} en {today_str}")
    candidates.sort(key=lambda x: x[1])
    return candidates[0]


def get_front_month(product: str, cache: dict) -> str:
    """Resuelve (con cache pasado explicitamente por el llamador -- sin estado global oculto) el ticker."""
    if product not in cache:
        cache[product] = resolve_front_month(product)
    return cache[product][0]


def check_expiry_alerts(cache: dict, send_fn: Callable[[str], None], prefix: str) -> None:
    """
    Avisa via send_fn si algun contrato en `cache` cruzo un checkpoint de
    FRONT_MONTH_ALERT_CHECKPOINTS desde la ultima corrida real (no cada
    dia dentro de la ventana de 10 dias habiles -- ver
    GLITCH_RESEARCH_LOG.md, 09-sep-2026). `prefix` es el identificador
    COMPLETO ya construido por el llamador (ej. "S10GLITCH - COMBINE -
    MES", "S10GLITCH - XFA - MGC", "S10GLITCH - COMBO2D - MNQ") -- mismo
    prefijo que ya usa cada scheduler en sus propios mensajes de
    OPEN/CLOSE/SUMMARY. Esta funcion NO construye el prefijo por su
    cuenta -- se pasa completo, no hardcodeado.

    Deteccion de checkpoint SIN estado persistido: compara `days_left`
    de HOY contra `days_left` calculado para el dia habil anterior
    (_previous_trading_day) -- si algun checkpoint cae estrictamente
    entre esos dos valores, se considera "cruzado" y dispara la alerta,
    incluso si un feriado hizo que el conteo saltara 2 en vez de 1 (el
    checkpoint NO se pierde por el salto).
    """
    today = dt.date.today()
    prev_trading_day = _previous_trading_day(today)
    for product, (ticker, ltd_str) in cache.items():
        ltd = dt.datetime.strptime(ltd_str, "%Y-%m-%d").date()
        days_left = int(np.busday_count(today, ltd))
        days_left_prev = int(np.busday_count(prev_trading_day, ltd))
        crossed = [c for c in FRONT_MONTH_ALERT_CHECKPOINTS if days_left <= c < days_left_prev]
        if crossed:
            checkpoint_hit = max(crossed)
            send_fn(f"""{prefix}
STATUS: CONTRATO PROXIMO A VENCER
{product}: {ticker}
Vence: {ltd_str} ({days_left} dias habiles restantes, checkpoint {checkpoint_hit})
ACCION: verificar que el roll dinamico tome el siguiente contrato automaticamente
{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}""")
