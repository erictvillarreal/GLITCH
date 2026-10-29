"""
Glitch — Diagnostico MINIMO del bug de delay imposible en
probe_massive_mgc_delay.py (07-sep-2026)
========================================================================
El probe de delay devolvio ~319,174 minutos (7+ meses) -- imposible
como delay real de mercado. Sospecha principal, con evidencia de codigo
(no adivinada): probe_massive_mgc_delay.py paso window_start_gte/lte
como DATETIME COMPLETO con offset de timezone
(`dt.datetime.now(timezone.utc).isoformat()` -> algo como
"2026-09-07T09:00:00+00:00") -- un formato NUNCA probado contra esta
API en este repo. fetch_mes_2y.py y fetch_mgc_correct_window.py (los
dos scripts que SI funcionaron, confirmado con datos reales) SIEMPRE
pasaron esos mismos parametros como fecha SOLA
(`fecha.date().isoformat()` -> "2026-09-07", sin hora ni offset).

Este script prueba VARIAS variantes lado a lado contra el MISMO
contrato y las IMPRIME CRUDAS (no las interpreta, no calcula ningun
delay) -- para ver evidencia real de cual formato funciona antes de
arreglar el probe original a ciegas:

  A) window_start_gte/lte como FECHA SOLA (formato ya probado) +
     sort=asc + limit alto -- tomar el ultimo resultado.
  B) window_start_gte/lte como DATETIME COMPLETO con offset (lo que
     probablemente causo el bug) -- mismo query que el probe original,
     para reproducir el problema con evidencia.
  C) SIN window_start_gte/lte en absoluto, solo sort=desc + limit=1 --
     pedir directamente "la barra mas reciente que tengas", sin
     construir ningun rango de fechas.

Tambien imprime el conteo total de resultados de cada variante y las
primeras/ultimas 2 filas crudas -- suficiente para ver si el filtro de
fecha se esta aplicando en absoluto.

USO (misma Terminal donde MASSIVE_API_KEY ya esta exportada):
    cd /Users/anelvillarreal/Desktop/Kito/GLITCH-clean/glitch
    python scripts/diagnose_massive_aggs_query.py
"""
from __future__ import annotations
import os
import sys
import json
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

MASSIVE_API_KEY = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
if not MASSIVE_API_KEY:
    print("ERROR: falta MASSIVE_API_KEY (o POLYGON_API_KEY) en el entorno.")
    sys.exit(1)

from execution.contracts import resolve_front_month  # noqa: E402

BASE = "https://api.massive.com"
HEADERS = {"Authorization": f"Bearer {MASSIVE_API_KEY}"}


def raw_get(params: dict) -> dict:
    """Devuelve la respuesta CRUDA completa (no solo 'results') -- para
    ver tambien next_url/status/cualquier campo de error que la API
    incluya, no solo los datos."""
    ticker = params.pop("_ticker")
    url = f"{BASE}/futures/v1/aggs/{ticker}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    print(f"  URL final consultada: {r.url}")
    print(f"  HTTP status: {r.status_code}")
    try:
        return r.json()
    except Exception as e:
        print(f"  [ERROR] respuesta no es JSON valido: {e}")
        print(f"  Cuerpo crudo (primeros 500 chars): {r.text[:500]}")
        return {}


def summarize(label: str, data: dict):
    results = data.get("results", [])
    print(f"\n--- {label} ---")
    print(f"  Cantidad de resultados: {len(results)}")
    print(f"  next_url presente: {'si' if data.get('next_url') else 'no'}")
    if not results:
        print(f"  Respuesta completa (sin resultados, puede tener pista del problema): "
              f"{json.dumps({k: v for k, v in data.items() if k != 'results'}, default=str)[:400]}")
        return
    now_utc = dt.datetime.now(dt.timezone.utc)
    for tag, row in [("primer resultado", results[0]), ("ultimo resultado", results[-1])]:
        ts = dt.datetime.fromtimestamp(row["window_start"] / 1e9, tz=dt.timezone.utc)
        edad = (now_utc - ts).total_seconds() / 60
        print(f"  {tag}: window_start_ns={row['window_start']}  -> {ts.isoformat()}  "
              f"(edad vs ahora: {edad:.1f} min = {edad/60/24:.1f} dias)")


def main():
    ticker, last_trade_date = resolve_front_month("MGC")
    print(f"Contrato front-month resuelto: {ticker} (last_trade_date={last_trade_date})")
    now_utc = dt.datetime.now(dt.timezone.utc)
    today_str = now_utc.date().isoformat()
    yesterday_str = (now_utc.date() - dt.timedelta(days=1)).isoformat()

    # A) Formato FECHA SOLA (el unico ya probado en este repo)
    data_a = raw_get({
        "_ticker": ticker, "resolution": "1min",
        "window_start_gte": yesterday_str, "window_start_lte": today_str,
        "sort": "window_start.asc", "limit": 5000,
    })
    summarize("A) fecha sola (yesterday->today), sort=asc, limit=5000", data_a)

    # B) Formato DATETIME COMPLETO con offset -- lo que uso el probe original
    data_b = raw_get({
        "_ticker": ticker, "resolution": "1min",
        "window_start_gte": (now_utc - dt.timedelta(hours=3)).isoformat(),
        "window_start_lte": now_utc.isoformat(),
        "sort": "window_start.asc", "limit": 5000,
    })
    summarize("B) datetime completo con offset (formato del probe original)", data_b)

    # C) Sin rango de fechas -- pedir directamente lo mas reciente
    data_c = raw_get({
        "_ticker": ticker, "resolution": "1min",
        "sort": "window_start.desc", "limit": 1,
    })
    summarize("C) sin rango de fechas, sort=desc, limit=1 (pedir 'lo mas reciente' directo)", data_c)

    print("\n" + "=" * 90)
    print("Comparar las 3 variantes arriba -- la(s) que devuelva(n) una 'edad' de minutos")
    print("(no de meses) es la que hay que usar en el probe corregido.")
    print("=" * 90)


if __name__ == "__main__":
    main()
