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
import json
import logging
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scheduler.telegram_bot import send
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index
from execution.contracts import get_front_month, check_expiry_alerts

CT = ZoneInfo("America/Chicago")
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO,
    format="%(asctime)s CT [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("geometry")

# ── Config ────────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

PRODUCT_KEY = os.getenv("GLITCH_PRODUCT", "MES")
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

LOG_FILE = f"geometry_{PRODUCT_KEY.lower()}_log.json"
POLL_INTERVAL = 60  # segundos entre polls

_front_month_cache: dict[str, tuple[str, str]] = {}


# ── Helpers ───────────────────────────────────────────────────────────────
def ct_now(): return datetime.now(CT)


def load_log():
    try:
        with open(LOG_FILE) as f: return json.load(f)
    except Exception: return []


def save_log(l):
    with open(LOG_FILE, "w") as f:
        json.dump(l, f, indent=2, default=str)


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

    # ── 3. Espera apertura RTH (9:30 CT, misma convencion del resto del repo) ──
    while ct_now().hour * 60 + ct_now().minute < 9 * 60 + 30:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura RTH...")
        time.sleep(15)

    entry_bars = None
    for attempt in range(8):
        entry_bars = fetch_intraday(CFG.spec.yf_ticker)
        if entry_bars is not None and len(entry_bars) >= 1:
            break
        log.info(f"  Esperando datos {CFG.spec.yf_ticker} ({attempt+1}/8)...")
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
    wins  = sum(1 for e in paper_log if e.get('result') == 'TP')
    total = sum(1 for e in paper_log if e.get('result') in ('TP', 'SL', 'FLATTEN'))
    wr    = wins / total if total > 0 else 0

    summary = (f"GLITCH - GEOMETRY-{PRODUCT_KEY} | DAILY SUMMARY\n"
               f"Trades: {total}\n"
               f"Win Rate: {wr:.1%}\n"
               f"PnL Total: ${total_pnl:+,.2f} USD")
    send(summary)
    log.info("Done — saliendo")


if __name__ == "__main__":
    run()
