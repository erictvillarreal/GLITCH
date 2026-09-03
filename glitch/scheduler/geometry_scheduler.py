"""
GLITCH — Geometry Scheduler (Camino B, producto-agnostico) — 25-ago-2026
==========================================================================
Entrada SIN señal predictiva: alterna long/short (default validado) a la
apertura RTH. Salida via barreras fijas en ticks (SL/TP) o flatten
obligatorio de fin de sesion. Ver strategies/geometry_pure.py para la
logica de decision (unica fuente de verdad, compartida con cualquier
backtest futuro) y el porque de cada parametro.

CEREBRO 1 (lo que este modulo resuelve) vs. CEREBRO 2 (pausado, NO
tocar) — diferencia critica:

Cerebro 1 = pasar el Combine. Objetivo: maximizar pass_rate/dias_resolucion
dentro de una ventana ACOTADA de 15 dias, con perdida limitada a la fee
del intento (~$49-149). La geometria de este modulo (Camino B) explota
que esta ventana acotada + perdida acotada permite pasar con alta
probabilidad AUNQUE la estrategia subyacente pierda dinero en promedio
(EV negativo neto de comision) -- la convexidad del payout hace el
trabajo, no una prediccion de mercado.

Cerebro 2 = maximizar payouts reales una vez fondeado (cuenta XFA).
Objetivo DISTINTO: el horizonte es INDEFINIDO (sin ventana de 15 dias que
acote el riesgo), y el umbral relevante no es "$3,000 acumulados" sino
"5 dias de >=$150 netos". Una estrategia con EV negativo o cero que
funciona para pasar el Combine NO sobrevive en Cerebro 2 -- sin la
ventana de tiempo que te protege, el MLL eventualmente alcanza cualquier
estrategia sin edge real positivo.

Cerebro 2 esta PAUSADO porque depende de una pregunta sin resolver: ¿el
MLL de la cuenta XFA se resetea a $0 SOLO la primera vez que se solicita
un payout, o CADA vez? Esto se reporto una vez (fuente: help.topstep.com,
cita parcial) pero NUNCA se verifico el texto completo ni la URL exacta
contra la fuente oficial. Son dos economias completamente distintas para
Cerebro 2 y no se puede diseñar nada confiable sin resolver esto primero.

Regla practica: si una tarea es sobre pasar el Combine (geometria de
ticks, combines_por_año, pass_rate_15d) es Cerebro 1 -- procede. Si es
sobre payouts, XFA, simulate_xfa_lifetime, o el colchon post-payout -- es
Cerebro 2 -- DETENTE y pregunta antes de avanzar, no asumas que el exito
de Cerebro 1 aplica ahi. NO conectar este scheduler a logica de Cerebro 2.

Rotar de producto = cambiar la env var GLITCH_PRODUCT (MES/MGC/M2K/...),
no tocar este archivo. Ver strategies/geometry_pure.py::CANDIDATES.

Arranca en DRY_RUN=true (paper) siempre por default -- pasar a DRY_RUN=false
es una decision explicita separada, no el default de este codigo.

Railway Cron: definir antes de conectar (mismo horario que combo2d,
25 14 * * 1-5, es un punto de partida razonable -- ajustar segun el
producto elegido y su horario RTH real).
"""
import os
import sys
import logging
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# CHEQUEO UNIFICADO DE ARRANQUE (01-sep-2026) -- mismo motivo y mismo
# patron que combo2d_scheduler.py, ver ese archivo y
# GLITCH_RESEARCH_LOG.md para el contexto completo. Debe correr ANTES
# de telegram_bot/execution.contracts/execution.gist_store.
from execution.env_check import require_env

_PRODUCT_KEY_FOR_STARTUP_CHECK = os.getenv("GLITCH_PRODUCT", "MES")  # plain os.getenv, sin dependencias -- seguro de leer aqui
require_env(
    [("MASSIVE_API_KEY", "POLYGON_API_KEY"), "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    f"GEOMETRY-{_PRODUCT_KEY_FOR_STARTUP_CHECK}",
)

from scheduler.telegram_bot import send
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index
from execution.contracts import get_front_month, check_expiry_alerts
from execution.gist_store import load_log as _gist_load_log, save_log as _gist_save_log

CT = ZoneInfo("America/Chicago")
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO,
    format="%(asctime)s CT [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("geometry")

# ── Config ────────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

PRODUCT_KEY = _PRODUCT_KEY_FOR_STARTUP_CHECK  # ya calculado arriba, antes del chequeo unificado
if PRODUCT_KEY not in CANDIDATES:
    log.error(f"FATAL: GLITCH_PRODUCT={PRODUCT_KEY!r} no esta en CANDIDATES "
              f"({sorted(CANDIDATES)}). Ver strategies/geometry_pure.py.")
    sys.exit(1)
CFG = CANDIDATES[PRODUCT_KEY]

if CFG.spec.yf_ticker is None:
    log.error(f"FATAL: {PRODUCT_KEY} no tiene yf_ticker verificado en ProductSpec -- "
              f"NO se va a adivinar un simbolo de yfinance para el feed de precio en vivo. "
              f"Verificar y setear ProductSpec.yf_ticker antes de correr este producto.")
    sys.exit(1)

LOG_FILE = f"geometry_{PRODUCT_KEY.lower()}_log.json"  # nombre del archivo DENTRO del gist compartido -- ver execution/gist_store.py
POLL_INTERVAL = 60  # segundos entre polls

# Benchmark teorico para el reporte diario de pass_rate -- ver
# GLITCH_RESEARCH_LOG.md, "Duracion recomendada del periodo de paper
# trading": G2 (SL=100/TP=40, alternar, nc=40) da pass_rate_15d=0.8144
# via Monte Carlo (n_paths=8000, seed=42). El criterio de graduacion a
# DRY_RUN=false exige que el pass_rate EMPIRICO de paper no caiga mas de
# ~15-20pp por debajo de esto -- esa evaluacion la hace un humano al
# cierre del periodo, este reporte solo la deja visible dia a dia.
THEORETICAL_PASS_RATE = 0.8144

_front_month_cache: dict[str, tuple[str, str]] = {}


def _paper_progress(paper_log: list, today_str: str) -> dict:
    """
    Deriva el progreso del periodo de paper SIN estado separado -- la
    fecha de la primera entrada en paper_log ES el dia 1, no hay que
    llevar un contador aparte que se pueda desincronizar del log real.
    """
    resolved = [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN")]
    dates_seen = sorted({e["date"] for e in paper_log if e.get("date")})

    if dates_seen:
        first_date = datetime.strptime(dates_seen[0], "%Y-%m-%d").date()
        today = datetime.strptime(today_str, "%Y-%m-%d").date()
        days_elapsed = (today - first_date).days + 1
    else:
        days_elapsed = 1  # primera corrida de la vida del scheduler

    n_cycles = len(resolved)
    wins = sum(1 for e in resolved if e.get("result") == "TP")
    pass_rate_empirico = wins / n_cycles if n_cycles > 0 else None

    # Entrada mas reciente ANTERIOR a hoy con resultado -- "el dia anterior"
    prior_resolved = [e for e in resolved if e.get("date") != today_str]
    yesterday = prior_resolved[-1] if prior_resolved else None

    return {
        "days_elapsed": days_elapsed,
        "n_cycles": n_cycles,
        "pass_rate_empirico": pass_rate_empirico,
        "yesterday": yesterday,
    }


# ── Helpers ───────────────────────────────────────────────────────────────
def ct_now(): return datetime.now(CT)


# REFACTOR (27-ago-2026): ya NO leen/escriben el filesystem local -- ver
# el mismo cambio en combo2d_scheduler.py y execution/gist_store.py.
def load_log():
    return _gist_load_log(LOG_FILE)


def save_log(l):
    _gist_save_log(LOG_FILE, l)


def is_trading_day():
    """
    Calendario de feriados duplicado deliberadamente desde
    combo2d_scheduler.py (a diferencia de la señal/ATR/front-month, esto
    es un dato estatico trivial -- el riesgo de duplicacion es bajo,
    no amerita otro modulo compartido).
    """
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)
    }
    return (now.year, now.month, now.day) not in holidays


def fetch_intraday(ticker):
    """Descarga barras de hoy en 1min para precio actual (mismo patron que combo2d_scheduler.py)."""
    try:
        d = yf.Ticker(ticker).history(period="5d", interval="1m", prepost=False)
        if d.empty: return None
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        import pandas as pd
        d['dt']  = pd.to_datetime(d[tcol], utc=True).dt.tz_convert(CT)
        d['t']   = d['dt'].dt.hour*60 + d['dt'].dt.minute
        d['day'] = d['dt'].dt.date
        today = date.today()
        rth = d[(d['day']==today) & (d['t']>=9*60+30) & (d['t']<=14*60+30)].copy()
        return rth.reset_index(drop=True)
    except Exception as e:
        log.error(f"fetch_intraday {ticker}: {e}")
        return None


def run():
    log.info("=" * 60)
    log.info(f"GLITCH — Geometry Scheduler ({CFG.spec.label})")
    log.info(f"DRY_RUN={DRY_RUN}  NC={CFG.nc}  SL={CFG.sl_ticks}  TP={CFG.tp_ticks}  "
              f"direction={CFG.direction}")
    log.info("=" * 60)

    if not is_trading_day():
        log.info("No es dia de trading — saliendo")
        return

    now = ct_now()
    today_str = str(date.today())
    paper_log = load_log()

    # ── 1. Resuelve el contrato en uso (para logging/alertas de vencimiento --
    #        ver docstring de arriba: el feed de precio en vivo usa el simbolo
    #        continuo de yfinance, no requiere el ticker exacto de Massive) ──
    try:
        ticker = get_front_month(CFG.spec.product_code, _front_month_cache)
        log.info(f"Contrato en uso ({CFG.spec.product_code}): {ticker}")
        check_expiry_alerts(_front_month_cache, send, f"GEOMETRY-{PRODUCT_KEY}")
    except Exception as e:
        log.error(f"No se pudo resolver front-month para {CFG.spec.product_code}: {e}")
        send(f"GLITCH - GEOMETRY-{PRODUCT_KEY}\nSTATUS: ERROR\nERROR: front-month resolution failed: {e}")
        return

    # ── 2. Señal: sin predictiva, funcion pura de la fecha (ver geometry_pure.py) ──
    day_idx = trading_day_index(date.today())
    side = decide_side(day_idx, CFG.direction)
    direction_str = {1: "LONG", -1: "SHORT"}[side]
    log.info(f"Direccion (day_index={day_idx}, mode={CFG.direction}): {direction_str}")

    # ── 2b. Reporte de arranque: señal de hoy + resultado de ayer + progreso
    #         del periodo de paper. Se manda YA, sin esperar a que resuelva
    #         el trade de hoy -- el usuario necesita esto para juzgar el
    #         criterio de graduacion sin tener que revisar logs a mano. ──
    progress = _paper_progress(paper_log, today_str)

    if progress["yesterday"] is not None:
        y = progress["yesterday"]
        yesterday_line = f"{y['date']}: {y.get('direction', '?')} → {y['result']}  PnL=${y.get('pnl', 0):+,.2f}"
    else:
        yesterday_line = "(sin ciclo previo registrado)"

    if progress["pass_rate_empirico"] is not None:
        gap_pp = (progress["pass_rate_empirico"] - THEORETICAL_PASS_RATE) * 100
        pass_rate_line = (f"{progress['pass_rate_empirico']:.1%} empirico vs "
                           f"{THEORETICAL_PASS_RATE:.1%} teorico ({gap_pp:+.1f}pp)")
    else:
        pass_rate_line = "sin ciclos resueltos todavia"

    kickoff = (f"GLITCH - GEOMETRY-{PRODUCT_KEY} | INICIO DE DIA\n"
               f"Dia {progress['days_elapsed']} de paper  |  Ciclos completados: {progress['n_cycles']}\n"
               f"Señal de hoy: {direction_str} (day_index={day_idx}, mode={CFG.direction})\n"
               f"Resultado de ayer: {yesterday_line}\n"
               f"Pass rate acumulado: {pass_rate_line}\n"
               f"{datetime.now(CT).strftime('%Y-%m-%d %H:%M CT')}")
    send(kickoff)
    log.info(kickoff.replace("\n", " | "))

    # ── 3. Espera apertura RTH + margen de propagacion de Yahoo.
    #        CAMBIO (27-ago-2026): 9:30 -> 9:32 CT. Confirmado con el log de
    #        Railway del 27-ago-2026 (9:30:02-9:33:34 CT, servicio GEOMETRY):
    #        "fetch_intraday {ticker}: {e}" NUNCA aparecio en los 8 intentos
    #        -- fetch_intraday() nunca lanzo excepcion, siempre volvio con un
    #        DataFrame vacio tras el filtro RTH. Descarta fallo de API
    #        (hipotesis a), confirma lag de propagacion de la barra de
    #        apertura de MES=F en Yahoo (hipotesis b). Ver
    #        GLITCH_RESEARCH_LOG.md para el diagnostico completo. ──
    while ct_now().hour * 60 + ct_now().minute < 9 * 60 + 32:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura RTH...")
        time.sleep(15)

    # CAMBIO (27-ago-2026): 8 -> 12 reintentos (4min -> 6min de presupuesto
    # total). Logging por intento ahora distingue None (fetch_intraday()
    # lanzo excepcion -- esa excepcion ya se loguea aparte dentro de la
    # funcion) de "DataFrame vacio" (fetch OK, pero el filtro RTH no dejo
    # filas) -- si esto vuelve a fallar, el log ya dice cual de los 2 casos
    # es, sin tener que repetir esta investigacion.
    entry_bars = None
    for attempt in range(12):
        entry_bars = fetch_intraday(CFG.spec.yf_ticker)
        n_rows = len(entry_bars) if entry_bars is not None else 0
        if entry_bars is not None and n_rows >= 1:
            log.info(f"  {CFG.spec.yf_ticker}: {n_rows} filas RTH recibidas en intento {attempt+1}/12")
            break
        estado = "fetch devolvio None (ver linea de excepcion arriba, si la hay)" if entry_bars is None \
            else f"{n_rows} filas (fetch OK, vacio tras filtro RTH)"
        log.info(f"  Esperando datos {CFG.spec.yf_ticker} ({attempt+1}/12) -- {estado}")
        time.sleep(30)

    if entry_bars is None or entry_bars.empty:
        msg = f"GLITCH - GEOMETRY-{PRODUCT_KEY}\nSTATUS: ERROR\nERROR: no entry data available"
        send(msg)
        paper_log.append({"date": today_str, "signal": True, "side": side,
                          "pnl": 0, "note": "no_data_entry"})
        save_log(paper_log)
        return

    entry_price = float(entry_bars.iloc[-1]['close'])
    tp_price, sl_price = CFG.barrier_prices(entry_price, side)
    tp_usd, sl_usd = CFG.dollar_tp_sl()

    log.info(f"Entrada: {direction_str} @ {entry_price:.4f}")
    log.info(f"TP={tp_price:.4f} (+${tp_usd:.0f})  SL={sl_price:.4f} (-${sl_usd:.0f})  NC={CFG.nc}")

    msg = (f"GLITCH DETECTED - GEOMETRY-{PRODUCT_KEY}\n"
           f"{'PAPER LIVE' if DRY_RUN else 'LIVE'}\n"
           f"STATUS: OPEN\n"
           f"{direction_str}: {entry_price:,.4f}\n"
           f"TP/SL: {tp_price:,.4f} - {sl_price:,.4f}\n"
           f"ASSET: {CFG.spec.label} ({ticker})\n"
           f"SIZE: {CFG.nc} Contracts\n"
           f"{datetime.now(CT).strftime('%Y-%m-%d %H:%M CT')}")
    send(msg)

    # ── 4. Monitorea la posicion -- flatten obligatorio de fin de sesion es la
    #        barrera de tiempo VINCULANTE en vivo (ver nota en geometry_pure.py:
    #        max_holding_bars del backtest, ~8.3h, es mas largo que una sesion) ──
    result = None
    exit_price = entry_price

    while True:
        now = ct_now()
        t = now.hour * 60 + now.minute

        if t >= 14 * 60 + 30:
            bars = fetch_intraday(CFG.spec.yf_ticker)
            exit_price = float(bars.iloc[-1]['close']) if bars is not None and len(bars) > 0 else entry_price
            result = "FLATTEN"
            log.info(f"[{now.strftime('%H:%M')} CT] Cierre forzado de sesion @ {exit_price:.4f}")
            break

        bars = fetch_intraday(CFG.spec.yf_ticker)
        if bars is None or bars.empty:
            log.info(f"[{now.strftime('%H:%M')} CT] Sin datos, reintentando...")
            time.sleep(POLL_INTERVAL)
            continue

        price = float(bars.iloc[-1]['close'])
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

    # ── 5. PnL y notificacion ──────────────────────────────────────────────
    pnl = (exit_price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * CFG.nc
    log.info(f"EXIT {result} @ {exit_price:.4f} | PnL={pnl:+.2f}")

    msg = (f"GLITCH CLOSED - GEOMETRY-{PRODUCT_KEY}\n"
           f"{'PAPER LIVE' if DRY_RUN else 'LIVE'} | {result}\n"
           f"{direction_str}: {entry_price:,.4f} → {exit_price:,.4f}\n"
           f"PnL: ${pnl:+,.2f} USD\n"
           f"ASSET: {CFG.spec.label}\n"
           f"{datetime.now(CT).strftime('%Y-%m-%d %H:%M CT')}")
    send(msg)

    paper_log.append({
        "date": today_str, "signal": True, "side": side,
        "direction": direction_str, "entry": entry_price,
        "exit": exit_price, "result": result,
        "pnl": round(pnl, 2), "sl_ticks": CFG.sl_ticks, "tp_ticks": CFG.tp_ticks,
        "nc": CFG.nc, "dry_run": DRY_RUN, "product": PRODUCT_KEY,
    })
    save_log(paper_log)

    total_pnl = sum(e.get('pnl', 0) for e in paper_log)
    progress = _paper_progress(paper_log, today_str)  # recalculado -- incluye el ciclo de hoy

    if progress["pass_rate_empirico"] is not None:
        gap_pp = (progress["pass_rate_empirico"] - THEORETICAL_PASS_RATE) * 100
        pass_rate_line = (f"{progress['pass_rate_empirico']:.1%} empirico vs "
                           f"{THEORETICAL_PASS_RATE:.1%} teorico ({gap_pp:+.1f}pp)")
    else:
        pass_rate_line = "sin ciclos resueltos todavia"

    summary = (f"GLITCH - GEOMETRY-{PRODUCT_KEY} | DAILY SUMMARY\n"
               f"Dia {progress['days_elapsed']} de paper  |  Ciclos: {progress['n_cycles']}\n"
               f"Pass Rate: {pass_rate_line}\n"
               f"PnL Total: ${total_pnl:+,.2f} USD")
    send(summary)
    log.info("Done — saliendo")


if __name__ == "__main__":
    run()
