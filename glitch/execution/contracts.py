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
FRONT_MONTH_EXPIRY_ALERT_DAYS = 10  # dias habiles minimos antes de avisar

_TICKER_RE_CACHE: dict[str, "re.Pattern"] = {}


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


def check_expiry_alerts(cache: dict, send_fn: Callable[[str], None], label: str) -> None:
    """Avisa via send_fn si algun contrato en `cache` vence en <10 dias habiles."""
    for product, (ticker, ltd_str) in cache.items():
        ltd = dt.datetime.strptime(ltd_str, "%Y-%m-%d").date()
        days_left = int(np.busday_count(dt.date.today(), ltd))
        if days_left < FRONT_MONTH_EXPIRY_ALERT_DAYS:
            send_fn(f"""⚠️ GLITCH - {label} | CONTRATO PROXIMO A VENCER
{product}: {ticker}
Vence: {ltd_str} ({days_left} dias habiles restantes)
ACCION: verificar que el roll dinamico tome el siguiente contrato automaticamente""")
