"""
Glitch — Medicion EMPIRICA del delay real de Massive para MGC
(07-sep-2026)
========================================================================
Ultimo bloqueo tecnico antes de diseñar el punto de entrada del
scheduler en vivo de MGC/150K. Mismo principio de "medir, no asumir"
que ya costo caro con el "10 minutos" de marketing de Yahoo -- NO se
asume ningun numero de Massive tampoco, se mide directamente.

Metodo: resuelve el contrato front-month real de MGC (reutiliza
execution/contracts.py::resolve_front_month -- misma fuente de verdad
que usan los schedulers en vivo, no logica nueva), pide la barra mas
reciente disponible via la API de Massive, y compara el FIN de esa
barra (no el inicio -- comparar contra el inicio confunde el delay real
con el ancho de la barra) contra la hora real (UTC) en el momento de la
consulta. Repite 6 veces, ~25s de separacion (~2.5 minutos totales),
para ver si el delay es CONSISTENTE dentro de una misma corrida (a
diferencia de Yahoo, que era erratico) -- no es una medicion de una
sola muestra.

Intenta resolucion "1min" primero (mas fino, menos confusion entre
ancho de barra y delay real); si la API no la soporta o devuelve vacio,
cae a "5min" automaticamente y lo reporta explicitamente -- no falla en
silencio con un numero de resolucion distinto al que realmente se usó.

USO (correr en la Terminal donde MASSIVE_API_KEY ya esta exportada):
    cd /Users/anelvillarreal/Desktop/Kito/GLITCH-clean/glitch
    python scripts/probe_massive_mgc_delay.py

Nota: gold cotiza casi 24h (domingo 5pm CT a viernes 4pm CT, con un
corte diario de 1h 4-5pm CT) -- correr esto fuera de ese corte diario
para que la medicion sea representativa de un momento con datos
fluyendo activamente, no de un hueco de mercado cerrado.
"""
from __future__ import annotations
import os
import sys
import time
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

MASSIVE_API_KEY = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
if not MASSIVE_API_KEY:
    print("ERROR: falta MASSIVE_API_KEY (o POLYGON_API_KEY) en el entorno.")
    sys.exit(1)

from execution.contracts import resolve_front_month  # noqa: E402 -- despues del chequeo de API key

BASE = "https://api.massive.com"
HEADERS = {"Authorization": f"Bearer {MASSIVE_API_KEY}"}

N_SAMPLES = 6
SECONDS_BETWEEN_SAMPLES = 25
RESOLUTIONS_TO_TRY = ["1min", "5min"]


def _get(path: str, params: dict) -> list[dict]:
    r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])


def _resolution_seconds(resolution: str) -> int:
    return {"1min": 60, "5min": 300}[resolution]


def fetch_latest_bar(ticker: str) -> tuple[dict, str]:
    """Devuelve (barra_mas_reciente, resolucion_realmente_usada)."""
    now_utc = dt.datetime.now(dt.timezone.utc)
    window_start = (now_utc - dt.timedelta(hours=3)).isoformat()
    window_end = now_utc.isoformat()

    for resolution in RESOLUTIONS_TO_TRY:
        results = _get(f"/futures/v1/aggs/{ticker}", {
            "resolution": resolution, "window_start_gte": window_start, "window_start_lte": window_end,
            "sort": "window_start.asc", "limit": 5000,
        })
        if results:
            return results[-1], resolution
    raise RuntimeError(f"Sin barras recientes para {ticker} en ninguna resolucion probada {RESOLUTIONS_TO_TRY} "
                        f"-- ¿mercado cerrado (corte diario 4-5pm CT) o ticker incorrecto?")


def main():
    ticker, last_trade_date = resolve_front_month("MGC")
    print(f"Contrato front-month resuelto: {ticker} (last_trade_date={last_trade_date})")
    print(f"Tomando {N_SAMPLES} muestras, {SECONDS_BETWEEN_SAMPLES}s de separacion "
          f"(~{N_SAMPLES * SECONDS_BETWEEN_SAMPLES / 60:.1f} min totales)\n")

    delays_sec = []
    for i in range(N_SAMPLES):
        query_time = dt.datetime.now(dt.timezone.utc)
        try:
            bar, resolution_used = fetch_latest_bar(ticker)
        except Exception as e:
            print(f"  [muestra {i+1}] ERROR: {e}")
            time.sleep(SECONDS_BETWEEN_SAMPLES)
            continue

        bar_start = dt.datetime.fromtimestamp(bar["window_start"] / 1e9, tz=dt.timezone.utc)
        bar_end = bar_start + dt.timedelta(seconds=_resolution_seconds(resolution_used))
        delay = (query_time - bar_end).total_seconds()
        delays_sec.append(delay)

        print(f"  [muestra {i+1}] {query_time.isoformat()}  resolucion={resolution_used}  "
              f"barra_mas_reciente=[{bar_start.isoformat()} -> {bar_end.isoformat()}]  "
              f"delay={delay:.1f}s ({delay/60:.2f} min)")

        if i < N_SAMPLES - 1:
            time.sleep(SECONDS_BETWEEN_SAMPLES)

    if not delays_sec:
        print("\nSin muestras validas -- no se pudo medir el delay (ver errores arriba).")
        sys.exit(1)

    print(f"\n{'='*80}\nRESUMEN\n{'='*80}")
    print(f"N muestras validas: {len(delays_sec)}")
    print(f"Delay minimo:   {min(delays_sec):.1f}s ({min(delays_sec)/60:.2f} min)")
    print(f"Delay maximo:   {max(delays_sec):.1f}s ({max(delays_sec)/60:.2f} min)")
    print(f"Delay promedio: {sum(delays_sec)/len(delays_sec):.1f}s ({sum(delays_sec)/len(delays_sec)/60:.2f} min)")
    spread = max(delays_sec) - min(delays_sec)
    print(f"Variacion (max-min) dentro de esta corrida: {spread:.1f}s")
    if spread < 30:
        print("-> Delay CONSISTENTE dentro de esta corrida (variacion <30s).")
    else:
        print("-> Delay VARIABLE dentro de esta corrida -- no asumir un numero fijo sin mas mediciones.")
    print("\nRECORDATORIO: esto es UNA corrida en UN momento del dia. Repetir en otro momento "
          "(ej. apertura, mediodia, cierre) antes de fijar el margen de espera del scheduler en vivo.")


if __name__ == "__main__":
    main()
