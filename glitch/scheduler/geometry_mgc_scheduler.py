"""
GLITCH — Geometry MGC/XFA Scheduler (Cerebro 2, paper trading real) — 07-sep-2026
====================================================================================
Paper-trading en vivo del candidato de geometria pura MGC/150K
(strategies/geometry_pure.py::CANDIDATES["MGC_XFA_150K"]) -- SL=TP=364
ticks, nc=6, alternando sin señal predictiva, WR=0.50 objetivo (validado
empiricamente: 49.97% con la ventana horaria original, 50.20% con la
ventana corregida 7:00-15:00 CT -- ver GLITCH_RESEARCH_LOG.md, 06/07-sep-2026).

DIFERENCIA DELIBERADA con scheduler/geometry_scheduler.py (MES/G2):

1. Fuente de precio en vivo: MASSIVE, no Yahoo. Decision explicita del
   usuario (04-sep-2026) -- la suscripcion de Massive ya esta pagada y
   su delay es medible/consistente (a diferencia del de Yahoo, que fue
   erratico y costo 2.5 semanas de incidentes con MES=F). geometry_scheduler.py
   NO se puede reusar tal cual para MGC porque esta hardcodeado a
   yfinance (`SPECS["MGC"].yf_ticker` es `None` -- deliberadamente, ver
   ProductSpec, el scheduler de Yahoo se niega a adivinar un simbolo).
   Este archivo usa execution.contracts.get_front_month() (misma fuente
   de verdad que TODOS los schedulers) + una consulta directa a la API
   de Massive para el precio actual, con el patron YA CORREGIDO
   (sort=window_start.desc + limit=1, SIN rango de fechas -- ver
   scripts/probe_massive_mgc_delay.py y GLITCH_RESEARCH_LOG.md,
   "Leccion de API reusable", 07-sep-2026. El patron de rango+sort=asc
   NO devuelve el dato mas reciente en este endpoint, no repetir eso.)

2. Ventana de apertura: 7:00 CT (ventana de mayor liquidez REAL de
   gold, confirmada con evidencia -- ver GLITCH_RESEARCH_LOG.md,
   "HALLAZGO -- la ventana horaria de MGC..." 07-sep-2026), NO 9:30 CT
   (esa es la convencion de equity index que geometry_scheduler.py usa
   para MES). Flatten obligatorio a las 14:30 CT (mismo margen de 30
   minutos antes del cierre de la ventana validada, 15:00 CT, que
   geometry_scheduler.py ya usa para MES).

3. ENTRY_WAIT_MINUTES: CONFIRMADO (09-sep-2026). El margen de espera
   post-apertura antes de buscar el primer precio de entrada se midio
   con `scripts/probe_massive_mgc_delay.py` en 2 corridas, en horarios
   distintos del dia (manana y tarde/noche): 9.43 min y 9.50 min
   promedio respectivamente, maximo observado 9.94 min -- diferencia
   de 0.07 min entre corridas, rangos solapados. Delay de Massive
   confirmado ESTABLE entre momentos del dia, a diferencia del de
   Yahoo (que fue erratico y costo 2.5 semanas de incidentes con
   MES=F). ENTRY_WAIT_MINUTES=13 incluye margen de seguridad sobre el
   maximo observado. Ver GLITCH_RESEARCH_LOG.md, 08/09-sep-2026, para
   el detalle de ambas corridas. Este scheduler SE NIEGA A ARRANCAR
   (falla ruidosamente, con alerta a Telegram) si ENTRY_WAIT_MINUTES
   alguna vez vuelve a quedar en None -- mismo principio de "fallar
   explicito, no adivinar" ya aplicado a MASSIVE_API_KEY/yf_ticker/etc.
   en el resto del repo.

4. Reporte de progreso: WR empirico vs WR teorico (0.50), no pass_rate
   de Combine -- este candidato es de geometria pura para XFA, no para
   pasar el Combine (ver GLITCH_RESEARCH_LOG.md, "HALLAZGO ESTRUCTURAL
   CENTRAL DE CEREBRO 2" -- el pass_rate de Combine de ESTE candidato
   es solo 46.9%/47.5%, un numero completamente distinto que NO debe
   confundirse con el WR reportado aqui). Este scheduler paper-tradea
   la GEOMETRIA (TP/SL/FLATTEN dia a dia) -- NO simula la maquina de
   estados completa de Combine+XFA (eso ya esta modelado por separado
   en core/funded_account.py + core/prop_firm.py + el Monte Carlo de
   flujo de caja, scripts/cerebro2_cashflow_monte_carlo.py).

DRY_RUN=true siempre por default -- pasar a DRY_RUN=false es una
decision explicita separada, no el default de este codigo.

NO push a main todavia -- vive en cerebro2-dev hasta decision explicita
de merge/deploy (ver GLITCH_RESEARCH_LOG.md, 07-sep-2026).

Railway Cron: horario propuesto basado en la ventana de liquidez ya
confirmada (7:00-14:30 CT) -- ajustar el lunes si hace falta, no
bloqueante para dejarlo preparado. Ejemplo (UTC, CT=UTC-5 en horario de
verano -- verificar DST vigente al momento de configurar el cron real):
    0 12 * * 1-5    (12:00 UTC = 7:00 CT durante CDT)
"""
import os
import sys
import logging
import time
import datetime as dt
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# CHEQUEO UNIFICADO DE ARRANQUE -- mismo patron y mismo motivo que
# combo2d_scheduler.py/geometry_scheduler.py. Debe correr ANTES de
# telegram_bot/execution.contracts/execution.gist_store. Namespace de
# Gist NUEVO Y SEPARADO ("geometry_mgc_log.json") -- nunca reusar las
# claves de geometry_mes_log/combo2d_log (ver checklist del usuario,
# 07-sep-2026, punto 5).
from execution.env_check import require_env

require_env(
    [("MASSIVE_API_KEY", "POLYGON_API_KEY"), "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    "GEOMETRY-MGC-XFA",
)

import requests  # noqa: E402 -- despues del chequeo de env, mismo orden que el resto del repo

from scheduler.telegram_bot import send  # noqa: E402
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index  # noqa: E402
from execution.contracts import get_front_month, check_expiry_alerts  # noqa: E402
from execution.gist_store import load_log as _gist_load_log, save_log as _gist_save_log  # noqa: E402
from core.prop_firm import TOPSTEP_150K  # noqa: E402

CT = ZoneInfo("America/Chicago")
# Logging con timestamp SIEMPRE en America/Chicago -- mismo fix del
# 07-sep-2026 aplicado a geometry_scheduler.py/combo2d_scheduler.py/
# glitch_scheduler.py en main, ver execution/ct_logging.py y
# GLITCH_RESEARCH_LOG.md para el por que (el patron anterior dependia
# silenciosamente del TZ del contenedor).
from execution.ct_logging import setup_ct_logging
log = setup_ct_logging("geometry_mgc")

# ── Config ────────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Fijo, NO switcheable via env var como geometry_scheduler.py -- este es
# un servicio de Railway DEDICADO a este candidato especifico, no un
# scheduler generico multi-producto. Si en el futuro se quiere esa
# flexibilidad, refactorizar entonces -- explicito ahora es mejor que
# implicito con un solo candidato real.
PRODUCT_KEY = "MGC_XFA_150K"
DISPLAY_LABEL = "GEOMETRY-MGC-XFA"  # usado solo en logs internos (log.info), no en mensajes de Telegram -- ver PREFIX abajo
CFG = CANDIDATES[PRODUCT_KEY]

# Rediseño de templates de Telegram (09-sep-2026) -- mismo estandar en los
# 3 schedulers, ver GLITCH_RESEARCH_LOG.md. PREFIX identifica el mensaje
# como Cerebro 2/XFA de un vistazo, sin ambiguedad con Cerebro 1/COMBINE
# (geometry_scheduler.py) ni con COMBO2D.
PREFIX = f"S10GLITCH - XFA - {CFG.spec.product_code}"

LOG_FILE = "geometry_mgc_log.json"  # namespace nuevo y separado, ver docstring
POLL_INTERVAL = 60  # segundos entre polls, mismo valor que geometry_scheduler.py

# WR objetivo de diseño (gambler's ruin, RR=1.0 simetrico) -- validado
# empiricamente: 49.97% (ventana horaria original), 50.20% (ventana
# corregida 7:00-15:00 CT). Ver GLITCH_RESEARCH_LOG.md, 06/07-sep-2026.
# NO es un pass_rate de Combine (ese es 46.9%/47.5%, numero distinto,
# ver docstring del modulo).
THEORETICAL_WR = 0.50

# CONFIRMADO (N=2 corridas, horarios distintos, 09-sep-2026): promedio
# 9.43-9.50 min, maximo observado 9.94 min, margen de 13 min incluye
# buffer de seguridad. Ver GLITCH_RESEARCH_LOG.md para el detalle de
# ambas corridas -- mismo estandar de "medir, no asumir" ya aplicado a
# Yahoo, ahora cerrado para Massive/MGC: la primera corrida (08-sep,
# manana) dio 9.43 min promedio (rango 9.07-9.78); la segunda (09-sep,
# tarde/noche, horario deliberadamente distinto de la primera) dio
# 9.50 min promedio (rango 9.06-9.94) -- diferencia de solo 0.07 min
# entre promedios, rangos solapados. Delay de Massive confirmado
# ESTABLE entre momentos del dia, no erratico como el de Yahoo.
ENTRY_WAIT_MINUTES = 13  # CONFIRMADO (N=2 corridas, 09-sep-2026) -- ver comentario arriba

RTH_OPEN_HOUR, RTH_OPEN_MINUTE = 7, 0    # ventana de mayor liquidez de MGC confirmada, no 9:30
FLATTEN_HOUR, FLATTEN_MINUTE = 14, 30    # mismo margen de 30min antes del cierre de ventana (15:00 CT) que MES

# "Dias vs. Estimado" (template de Telegram, 09-sep-2026) --
# dias_calendario_esperados = dias_promedio_resolucion (avg de TODOS los
# intentos de Combine resueltos, pase o truene -- SimResult.avg_resolution_days)
# x (1 / pass_rate) (intentos esperados hasta pasar). MISMA formula y mismo
# motor (simulation/monte_carlo.py::TopstepMonteCarloSimulator, ya
# auditado) que el numero equivalente de G2 (4.49 dias, ver
# GLITCH_RESEARCH_LOG.md, "Duracion recomendada del periodo de paper
# trading", 25-ago-2026) -- NO un numero de servilleta, calculado
# formalmente con scripts/mgc_dias_esperados.py (09-sep-2026), reusando la
# misma distribucion/geometria de scripts/cerebro2_cashflow_monte_carlo.py
# (SL=TP=364 ticks, nc=6, TOPSTEP_150K). Con WR=0.5020 (empirico, ventana
# horaria corregida -- dataset de referencia actual para este candidato):
# pass_rate=47.35%, avg_pass_days=7.58, avg_blown_days=5.66,
# dias_promedio_resolucion=6.57, dias_calendario_esperados=13.8726.
# Redondeado a 13.9. (Con WR=0.50 teorico el resultado es casi identico,
# 13.99 -- insensible a cual WR se use.)
DIAS_ESPERADOS = 13.9

# Logica de reinicio de intento de Combine (09-sep-2026, ver
# GLITCH_RESEARCH_LOG.md) -- misma logica que geometry_scheduler.py,
# umbrales confirmados contra core/prop_firm.py (fuente ya auditada), NO
# hardcodeados a mano: este candidato usa una cuenta 150K (ver
# PRODUCT_KEY="MGC_XFA_150K" arriba), TOPSTEP_150K.profit_target=$9,000,
# TOPSTEP_150K.mll_distance=$4,500 -- DISTINTOS de los $3,000/$2,000 de
# G2 (cuenta 50K). Confirmar SIEMPRE el tamaño de cuenta real de cada
# candidato antes de reusar estos numeros en un candidato nuevo.
PROFIT_TARGET = TOPSTEP_150K.profit_target      # $9,000
MLL_THRESHOLD = -TOPSTEP_150K.mll_distance      # -$4,500

_front_month_cache: dict[str, tuple[str, str]] = {}


def _fail_if_entry_wait_not_confirmed():
    """Falla ruidosamente (Telegram + exit) si ENTRY_WAIT_MINUTES sigue
    sin confirmar -- NO arrancar con un margen adivinado. Ver docstring
    del modulo, punto 3, y el checklist del usuario 07-sep-2026 punto 3:
    'que el codigo falle explicitamente si se intenta desplegar sin ese
    valor confirmado, no que corra con un default adivinado'."""
    if ENTRY_WAIT_MINUTES is None:
        msg = (f"{PREFIX}\nSTATUS: ERROR\n"
               f"ERROR: ENTRY_WAIT_MINUTES sin confirmar (sigue en None).\n"
               f"Correr scripts/probe_massive_mgc_delay.py lunes-viernes en horario "
               f"de mercado activo y setear el valor real antes de desplegar.")
        log.error(msg.replace("\n", " | "))
        try:
            send(msg)
        except Exception as e:
            log.error(f"No se pudo enviar alerta de Telegram (ademas del error principal): {e}")
        sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────
def ct_now(): return dt.datetime.now(CT)


def utc_now_str():
    """Timestamp UTC para los mensajes de Telegram (template 09-sep-2026)
    -- distinto de ct_now(), que sigue usandose para el timing operativo
    del scheduler (apertura, flatten, etc). No afecta setup_ct_logging()
    (execution/ct_logging.py) -- los logs del servidor siguen en CT."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_log():
    return _gist_load_log(LOG_FILE)


def save_log(l):
    _gist_save_log(LOG_FILE, l)


def is_trading_day():
    """
    Calendario de feriados duplicado deliberadamente desde
    geometry_scheduler.py/combo2d_scheduler.py -- mismo razonamiento
    (dato estatico trivial, bajo riesgo de duplicacion). NOTA: este es
    el calendario de feriados de EQUITY INDEX/CME general -- no se
    verifico si COMEX metales observa exactamente los mismos feriados
    (ej. algunos exchanges de commodities operan en dias que equity no).
    Simplificacion deliberada para el deploy inicial -- refinar si se
    observa un feriado real donde MGC si opera y este scheduler se
    queda afuera sin necesidad.
    """
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)
    }
    return (now.year, now.month, now.day) not in holidays


def _current_intento(paper_log: list) -> int:
    """Misma logica que geometry_scheduler.py::_current_intento -- ver
    ese archivo para el razonamiento completo. Duplicado deliberadamente
    (no importado de geometry_scheduler.py) -- este scheduler NO debe
    acoplarse a codigo de Cerebro 1, mismo principio ya establecido en
    el docstring de geometry_scheduler.py."""
    resolved = [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN")]
    if not resolved:
        return 1
    return max(e.get("intento", 1) for e in resolved)


def _attempt_entries(paper_log: list, intento: int) -> list:
    return [e for e in paper_log
            if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(paper_log: list, intento: int) -> float:
    return sum(e.get('pnl', 0) for e in _attempt_entries(paper_log, intento))


def _attempt_days_elapsed(paper_log: list, intento: int, today_str: str) -> int:
    """0 si el intento todavia no tiene ningun ciclo resuelto (justo
    despues de un reinicio) -- distinto de _paper_progress()['days_elapsed']
    (historico, devuelve 1 en ese caso)."""
    entries = _attempt_entries(paper_log, intento)
    dates_seen = sorted({e["date"] for e in entries if e.get("date")})
    if not dates_seen:
        return 0
    first_date = dt.datetime.strptime(dates_seen[0], "%Y-%m-%d").date()
    today = dt.datetime.strptime(today_str, "%Y-%m-%d").date()
    return (today - first_date).days + 1


def _check_attempt_reset(attempt_pnl_after: float, profit_target: float, mll_threshold: float) -> Optional[str]:
    """Misma logica que geometry_scheduler.py::_check_attempt_reset --
    funcion PURA, testeable en aislamiento. mll_threshold ya viene
    NEGATIVO (ver MLL_THRESHOLD arriba)."""
    if attempt_pnl_after >= profit_target:
        return "PASE"
    if attempt_pnl_after <= mll_threshold:
        return "QUIEBRE"
    return None


def _paper_progress(paper_log: list, today_str: str) -> dict:
    """Misma logica que geometry_scheduler.py::_paper_progress -- WR en
    vez de pass_rate (ver THEORETICAL_WR arriba)."""
    resolved = [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN")]
    dates_seen = sorted({e["date"] for e in paper_log if e.get("date")})

    if dates_seen:
        first_date = dt.datetime.strptime(dates_seen[0], "%Y-%m-%d").date()
        today = dt.datetime.strptime(today_str, "%Y-%m-%d").date()
        days_elapsed = (today - first_date).days + 1
    else:
        days_elapsed = 1

    n_cycles = len(resolved)
    # WR condicional (TP/(TP+SL)), excluye FLATTEN -- mismo criterio ya
    # aplicado en scripts/validate_mgc_wr_empirical.py para no diluir
    # el denominador con time-exits/flattens.
    n_tp = sum(1 for e in resolved if e.get("result") == "TP")
    n_sl = sum(1 for e in resolved if e.get("result") == "SL")
    wr_empirico = n_tp / (n_tp + n_sl) if (n_tp + n_sl) > 0 else None

    prior_resolved = [e for e in resolved if e.get("date") != today_str]
    yesterday = prior_resolved[-1] if prior_resolved else None

    return {
        "days_elapsed": days_elapsed, "n_cycles": n_cycles,
        "wr_empirico": wr_empirico, "yesterday": yesterday,
    }


def fetch_latest_price(ticker: str) -> Optional[float]:
    """
    Precio actual via Massive -- patron YA CORREGIDO (ver docstring del
    modulo): sort=window_start.desc + limit=1, SIN rango de fechas. El
    patron de rango+sort=asc (usado para descargas historicas) NO
    devuelve el dato mas reciente en este endpoint -- no repetir ese
    error aqui.
    """
    api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    for resolution in ("1min", "5min"):
        try:
            r = requests.get(
                f"https://api.massive.com/futures/v1/aggs/{ticker}",
                headers=headers,
                params={"resolution": resolution, "sort": "window_start.desc", "limit": 1},
                timeout=20,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if results:
                return float(results[0]["close"])
        except Exception as e:
            log.error(f"fetch_latest_price {ticker} ({resolution}): {e}")
    return None


def run():
    log.info("=" * 60)
    log.info(f"GLITCH — {DISPLAY_LABEL} ({CFG.spec.label})")
    log.info(f"DRY_RUN={DRY_RUN}  NC={CFG.nc}  SL={CFG.sl_ticks}  TP={CFG.tp_ticks}  "
              f"direction={CFG.direction}  ENTRY_WAIT_MINUTES={ENTRY_WAIT_MINUTES}")
    log.info("=" * 60)

    _fail_if_entry_wait_not_confirmed()

    if not is_trading_day():
        log.info("No es dia de trading — saliendo")
        return

    today_str = str(dt.date.today())
    paper_log = load_log()
    # Logica de reinicio de intento (09-sep-2026, ver GLITCH_RESEARCH_LOG.md)
    # -- resuelve la limitacion documentada anteriormente ("Equity/Dias
    # vs. Estimado acumulados sin limite de intento"). WR/Ciclos NO se
    # reinician -- siguen siendo historicos de TODOS los intentos.
    intento_actual = _current_intento(paper_log)
    attempt_pnl_before = _attempt_pnl(paper_log, intento_actual)

    # ── 1. Resuelve el contrato en uso ──
    try:
        ticker = get_front_month(CFG.spec.product_code, _front_month_cache)
        log.info(f"Contrato en uso ({CFG.spec.product_code}): {ticker}")
        check_expiry_alerts(_front_month_cache, send, PREFIX)
    except Exception as e:
        log.error(f"No se pudo resolver front-month para {CFG.spec.product_code}: {e}")
        send(f"{PREFIX}\nSTATUS: ERROR\nERROR: front-month resolution failed: {e}")
        return

    # ── 2. Señal: sin predictiva, funcion pura de la fecha ──
    day_idx = trading_day_index(dt.date.today())
    side = decide_side(day_idx, CFG.direction)
    direction_str = {1: "LONG", -1: "SHORT"}[side]
    log.info(f"Direccion (day_index={day_idx}, mode={CFG.direction}): {direction_str}")

    # ── 2b. Reporte de arranque ──
    progress = _paper_progress(paper_log, today_str)

    if progress["yesterday"] is not None:
        y = progress["yesterday"]
        yesterday_line = f"{y['date']}: {y.get('direction', '?')} → {y['result']}  PnL=${y.get('pnl', 0):+,.2f}"
    else:
        yesterday_line = "(sin ciclo previo registrado)"

    if progress["wr_empirico"] is not None:
        gap_pp = (progress["wr_empirico"] - THEORETICAL_WR) * 100
        wr_line = f"{progress['wr_empirico']:.1%} empirico vs {THEORETICAL_WR:.1%} teorico ({gap_pp:+.1f}pp)"
    else:
        wr_line = "sin ciclos resueltos todavia"

    kickoff = (f"{PREFIX} | INICIO DE DIA\n"
               f"Dia {progress['days_elapsed']} de paper  |  Ciclos completados: {progress['n_cycles']}\n"
               f"Señal de hoy: {direction_str} (day_index={day_idx}, mode={CFG.direction})\n"
               f"Resultado de ayer: {yesterday_line}\n"
               f"WR acumulado: {wr_line}\n"
               f"{utc_now_str()}")
    send(kickoff)
    log.info(kickoff.replace("\n", " | "))

    # ── 3. Espera apertura (7:00 CT) + margen de propagacion de Massive ──
    while ct_now().hour * 60 + ct_now().minute < RTH_OPEN_HOUR * 60 + RTH_OPEN_MINUTE:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura ({RTH_OPEN_HOUR}:{RTH_OPEN_MINUTE:02d} CT)...")
        time.sleep(15)

    wait_until = RTH_OPEN_HOUR * 60 + RTH_OPEN_MINUTE + ENTRY_WAIT_MINUTES
    while ct_now().hour * 60 + ct_now().minute < wait_until:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando margen de propagacion de Massive "
                  f"({ENTRY_WAIT_MINUTES} min post-apertura)...")
        time.sleep(15)

    entry_price = None
    for attempt in range(20):
        entry_price = fetch_latest_price(ticker)
        if entry_price is not None:
            log.info(f"  {ticker}: precio recibido en intento {attempt+1}/20: {entry_price:.4f}")
            break
        log.info(f"  Esperando precio {ticker} ({attempt+1}/20)...")
        time.sleep(30)

    if entry_price is None:
        gave_up_at = ct_now().strftime("%H:%M:%S")
        msg = (f"{PREFIX}\nSTATUS: ERROR\n"
               f"ERROR: no entry data available\n"
               f"Se rindio tras {attempt + 1} intentos a las {gave_up_at} CT")
        send(msg)
        paper_log.append({"date": today_str, "signal": True, "side": side,
                          "pnl": 0, "note": "no_data_entry",
                          "attempts_made": attempt + 1, "gave_up_at_ct": gave_up_at})
        save_log(paper_log)
        return

    tp_price, sl_price = CFG.barrier_prices(entry_price, side)
    tp_usd, sl_usd = CFG.dollar_tp_sl()

    log.info(f"Entrada: {direction_str} @ {entry_price:.4f}")
    log.info(f"TP={tp_price:.4f} (+${tp_usd:.0f})  SL={sl_price:.4f} (-${sl_usd:.0f})  NC={CFG.nc}")

    msg = (f"{PREFIX}\n"
           f"[OPEN]\n"
           f"Symbol: {CFG.spec.label} ({ticker})\n"
           f"Direction: {direction_str}\n"
           f"Entry: {entry_price:,.4f}\n"
           f"Contracts: {CFG.nc}\n"
           f"TP: {tp_price:,.4f}\n"
           f"SL: {sl_price:,.4f}\n"
           f"{utc_now_str()}")
    send(msg)

    # ── 4. Monitorea la posicion -- flatten obligatorio a las 14:30 CT ──
    result = None
    exit_price = entry_price

    while True:
        now = ct_now()
        t = now.hour * 60 + now.minute

        if t >= FLATTEN_HOUR * 60 + FLATTEN_MINUTE:
            price = fetch_latest_price(ticker)
            exit_price = price if price is not None else entry_price
            result = "FLATTEN"
            log.info(f"[{now.strftime('%H:%M')} CT] Cierre forzado de sesion @ {exit_price:.4f}")
            break

        price = fetch_latest_price(ticker)
        if price is None:
            log.info(f"[{now.strftime('%H:%M')} CT] Sin datos, reintentando...")
            time.sleep(POLL_INTERVAL)
            continue

        unreal = (price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * CFG.nc

        if side == 1:
            if price <= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price >= tp_price:
                exit_price = tp_price; result = "TP"; break
        else:
            if price >= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price <= tp_price:
                exit_price = tp_price; result = "TP"; break

        log.info(f"[{now.strftime('%H:%M')} CT] {direction_str} @ {price:.4f} | "
                  f"unreal=${unreal:+.2f} | TP={tp_price:.4f} SL={sl_price:.4f}")
        time.sleep(POLL_INTERVAL)

    # ── 5. PnL y notificacion ──
    pnl = (exit_price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * CFG.nc
    log.info(f"EXIT {result} @ {exit_price:.4f} | PnL={pnl:+.2f}")

    msg = (f"{PREFIX}\n"
           f"[CLOSE] [{result}]\n"
           f"Symbol: {CFG.spec.label} ({ticker})\n"
           f"Contracts: {CFG.nc}\n"
           f"PnL: ${pnl:+,.2f}\n"
           f"Dia de paper: {progress['days_elapsed']}\n"
           f"{utc_now_str()}")
    send(msg)

    paper_log.append({
        "date": today_str, "signal": True, "side": side,
        "direction": direction_str, "entry": entry_price,
        "exit": exit_price, "result": result,
        "pnl": round(pnl, 2), "sl_ticks": CFG.sl_ticks, "tp_ticks": CFG.tp_ticks,
        "nc": CFG.nc, "dry_run": DRY_RUN, "product": PRODUCT_KEY,
        "intento": intento_actual,
    })
    save_log(paper_log)

    # ── 5b. Verificar reinicio de intento (PASE/QUIEBRE) -- 09-sep-2026,
    #         ver GLITCH_RESEARCH_LOG.md. Mensaje separado del resumen
    #         diario normal, enviado el mismo dia que ocurre. ──
    attempt_pnl_after = attempt_pnl_before + pnl
    event = _check_attempt_reset(attempt_pnl_after, PROFIT_TARGET, MLL_THRESHOLD)
    if event is not None:
        attempt_days = _attempt_days_elapsed(paper_log, intento_actual, today_str)
        historic_progress = _paper_progress(paper_log, today_str)  # ya incluye el ciclo de hoy
        if historic_progress["wr_empirico"] is not None:
            gap_pp = (historic_progress["wr_empirico"] - THEORETICAL_WR) * 100
            hist_wr_line = f"{historic_progress['wr_empirico']:.1%} vs {THEORETICAL_WR:.1%} ({gap_pp:+.1f}pp)"
        else:
            hist_wr_line = "—"

        reset_msg = (f"{PREFIX} [INTENTO #{intento_actual} COMPLETADO: {event}]\n"
                     f"PnL final del intento: ${attempt_pnl_after:+,.2f}\n"
                     f"Dias que tomo este intento: {attempt_days}\n"
                     f"WR acumulado historico: {hist_wr_line}\n"
                     f"Iniciando intento #{intento_actual + 1} desde $0\n"
                     f"{utc_now_str()}")
        send(reset_msg)
        log.info(reset_msg.replace("\n", " | "))
        intento_actual += 1  # para el resumen diario de abajo -- ya pertenece al intento nuevo

    progress = _paper_progress(paper_log, today_str)  # historico -- recalculado, incluye el ciclo de hoy

    if progress["wr_empirico"] is not None:
        gap_pp = (progress["wr_empirico"] - THEORETICAL_WR) * 100
        wr_line = f"{progress['wr_empirico']:.1%} vs {THEORETICAL_WR:.1%} ({gap_pp:+.1f}pp)"
    else:
        wr_line = "—"

    # Acotado al intento actual (ya incrementado arriba si hubo
    # PASE/QUIEBRE hoy) -- si el intento acaba de reiniciarse, Equity y
    # Dias vs. Estimado caen naturalmente en 0.00/0, consistente con
    # "Iniciando intento #N+1 desde $0" del mensaje de reinicio de arriba.
    #
    # Next Payout / Payout Total: placeholder deliberado -- este scheduler
    # no implementa la regla de elegibilidad real de Topstep (5 dias
    # ganadores de $150+ neto, O balance >= $55k). Implementar eso es
    # logica nueva, fuera de alcance de este cambio.
    attempt_equity = _attempt_pnl(paper_log, intento_actual)
    attempt_days = _attempt_days_elapsed(paper_log, intento_actual, today_str)

    summary = (f"{PREFIX}\n"
               f"Next Payout: sin tracking de elegibilidad implementado todavia\n"
               f"Payout Total: sin tracking de elegibilidad implementado todavia\n"
               f"Equity: ${attempt_equity:,.2f}\n"
               f"PnL Hoy: ${pnl:+,.2f}\n"
               f"WR: {wr_line}\n"
               f"Dias vs. Estimado: {attempt_days} / {DIAS_ESPERADOS} esperados\n"
               f"{utc_now_str()}")
    send(summary)
    log.info("Done — saliendo")


if __name__ == "__main__":
    run()
