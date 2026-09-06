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

CORREGIDO (07-sep-2026) tras un primer intento que devolvio un delay
IMPOSIBLE (~319,174 min, 7+ meses): diagnosticado con
scripts/diagnose_massive_aggs_query.py, que probo 3 variantes de query
lado a lado con evidencia cruda. Resultado: pedir un RANGO de fechas
(`window_start_gte`/`window_start_lte`) con `sort=window_start.asc` y
tomar el ultimo resultado NO devuelve la barra mas reciente -- ni con
fechas solas (el formato ya probado en fetch_mes_2y.py) ni con
datetime completo -- hay un problema de paginacion/ordenamiento de la
API con ese patron especifico. Unica variante que SI funciona:
`sort=window_start.desc` + `limit=1`, SIN ningun rango de fechas --
pedir directamente "la barra mas reciente que tengas". Ver
GLITCH_RESEARCH_LOG.md, 07-sep-2026, "Leccion de API reusable" -- mismo
tipo de comportamiento ya visto antes en esta sesion con el endpoint de
contracts (point-in-time funciona, rango amplio + sort=asc no).

IMPORTANTE -- correr ENTRE SEMANA, en horario de mercado activo: un
primer intento de esta version corregida midio ~1.8 dias de "delay",
pero se corrio en fin de semana (2026-09-06 = sabado) -- eso NO es el
delay real de Massive, es tiempo transcurrido desde el cierre del
mercado el viernes. Gold cotiza casi 24h (domingo 5pm CT a viernes 4pm
CT, corte diario de 1h 4-5pm CT) -- correr esto lunes-viernes, evitando
el corte diario, para que la medicion sea comparable con el "10
minutos" nominal del plan Starter de Massive.

USO (correr en la Terminal donde MASSIVE_API_KEY ya esta exportada,
ENTRE SEMANA en horario de mercado activo):
    cd /Users/anelvillarreal/Desktop/Kito/GLITCH-clean/glitch
    python scripts/probe_massive_mgc_delay.py
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
    """
    Devuelve (barra_mas_reciente, resolucion_realmente_usada).

    PATRON CORRECTO (confirmado con diagnose_massive_aggs_query.py):
    sort=window_start.desc + limit=1, SIN window_start_gte/lte -- pedir
    un RANGO de fechas con sort=asc y tomar el ultimo resultado NO
    devuelve la barra mas reciente en este endpoint (problema de
    paginacion/ordenamiento de la API con ese patron especifico, no un
    problema de formato de fecha). No repetir el patron roto en
    scripts futuros que necesiten "el dato mas reciente" de Massive.
    """
    for resolution in RESOLUTIONS_TO_TRY:
        results = _get(f"/futures/v1/aggs/{ticker}", {
            "resolution": resolution, "sort": "window_start.desc", "limit": 1,
        })
        if results:
            return results[0], resolution
    raise RuntimeError(f"Sin barras recientes para {ticker} en ninguna resolucion probada {RESOLUTIONS_TO_TRY} "
                        f"-- ¿mercado cerrado (corte diario 4-5pm CT, o fin de semana) o ticker incorrecto?")


def _weekday_warning():
    """Advertencia defensiva -- un primer intento midio ~1.8 dias de
    'delay' que en realidad era tiempo desde el cierre del viernes,
    porque se corrio en sabado. Gold cierra Vie 4pm CT y reabre Dom
    5pm CT -- fuera de esa ventana, cualquier 'delay' medido aqui es
    tiempo de mercado cerrado, no delay real de la API."""
    now_ct = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=5)  # aprox CT (sin DST fino, suficiente para el aviso)
    weekday = now_ct.weekday()  # 0=lunes .. 5=sabado, 6=domingo
    if weekday == 5 or (weekday == 6 and now_ct.hour < 17) or (weekday == 4 and now_ct.hour >= 16):
        print("!" * 80)
        print("ADVERTENCIA: parece que el mercado de MGC esta CERRADO ahora mismo")
        print("(gold cierra Vie 16:00 CT, reabre Dom 17:00 CT). Cualquier 'delay' medido")
        print("en este momento sera tiempo de mercado cerrado, NO el delay real de la API.")
        print("Correr esto lunes-viernes, en horario de mercado activo.")
        print("!" * 80 + "\n")


def main():
    _weekday_warning()
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
