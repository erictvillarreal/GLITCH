"""
Glitch Scheduler — Railway deployment
======================================
Corre 24/7. Solo opera dentro de la ventana de mercado.
Descarga velas cada 15min. Ejecuta S10 ORB Fade automáticamente.

Variables de entorno necesarias en Railway:
  TOPSTEP_USERNAME=tu@email.com
  TOPSTEP_API_KEY=tu-api-key
  ACCOUNT_ID=12345
  DRY_RUN=true  (cambiar a false cuando estés listo)
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

CT = ZoneInfo("America/Chicago")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S CT",
)
log = logging.getLogger("glitch")

# ── Config ─────────────────────────────────────────────
MES_POINT  = 5.0
NC         = 3
LOG_FILE   = "paper_trade_log.json"
STATE_FILE = ".scheduler_state.json"

# Trading window CT
MARKET_OPEN   = (9, 30)   # 9:30 AM CT
ORB_CLOSE     = (9, 35)   # 9:35 AM CT — ORB window closes
SCAN_UNTIL    = (14, 30)  # 2:30 PM CT — stop looking for signals
FLATTEN_AT    = (15, 0)   # 3:00 PM CT — flatten everything

POLL_INTERVAL = 60        # seconds between checks when market open
SLEEP_INTERVAL= 300       # seconds between checks when market closed

# ── State ──────────────────────────────────────────────
def load_log():
    try:
        with open(LOG_FILE) as f: return json.load(f)
    except: return []

def save_log(log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2, default=str)

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except:
        return {
            "orb_high": None, "orb_low": None,
            "orb_built": False, "trade_placed": False,
            "direction": 0, "entry": 0,
            "tp": 0, "sl": 0, "tp_pts": 0, "sl_pts": 0,
            "date": None,
        }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

def reset_state():
    save_state({
        "orb_high": None, "orb_low": None,
        "orb_built": False, "trade_placed": False,
        "direction": 0, "entry": 0,
        "tp": 0, "sl": 0, "tp_pts": 0, "sl_pts": 0,
        "date": str(date.today()),
    })

# ── Time helpers ───────────────────────────────────────
def ct_now():
    return datetime.now(CT)

def ct_time(h, m):
    now = ct_now()
    return now.replace(hour=h, minute=m, second=0, microsecond=0)

def in_window(h, m, start, end):
    t = h*60 + m
    return start[0]*60+start[1] <= t <= end[0]*60+end[1]

def is_trading_day():
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),
        (2026,12,25),
    }
    return (now.year, now.month, now.day) not in holidays

def market_phase():
    """
    Returns current market phase:
      out_of_window, building_orb, scanning, in_position, closed
    """
    now = ct_now()
    h, m = now.hour, now.minute
    t = h*60 + m

    if not is_trading_day():
        return "out_of_window"
    if t < 9*60+30:
        return "out_of_window"
    if t < 9*60+35:
        return "building_orb"
    if t < 14*60+30:
        return "scanning"
    if t < 15*60+0:
        return "closing"
    return "out_of_window"

# ── Data ───────────────────────────────────────────────
def fetch_bars():
    """Descarga barras de 1min de MES. Retorna RTH de hoy."""
    try:
        d = yf.Ticker("MES=F").history(
            period="5d", interval="1m", prepost=True)
        if d.empty: return pd.DataFrame()
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        d['datetime'] = pd.to_datetime(d[tcol], utc=True)
        d['ct']       = d['datetime'].dt.tz_convert(CT)
        d['ct_time']  = d['ct'].dt.hour*60 + d['ct'].dt.minute
        d['date']     = d['ct'].dt.date
        today = date.today()
        rth   = d[
            (d['date'] == today) &
            (d['ct_time'] >= 9*60+30) &
            (d['ct_time'] <= 15*60+9) &
            (d['ct'].dt.dayofweek < 5)
        ].copy().reset_index(drop=True)
        return rth
    except Exception as e:
        log.error(f"fetch_bars error: {e}")
        return pd.DataFrame()

def get_prev_ranges(n=20):
    """Calcula rangos de días anteriores para régimen filter."""
    try:
        d = yf.Ticker("MES=F").history(
            period="30d", interval="1d", prepost=False)
        if d.empty or len(d) < 3: return [], 0, 0
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        ranges = (d['high'] - d['low']).values[-n:]
        prev   = float(ranges[-2]) if len(ranges) >= 2 else 0
        med    = float(np.median(ranges[:-1]))
        return ranges, prev, med
    except Exception as e:
        log.error(f"get_prev_ranges error: {e}")
        return [], 0, 0

# ── Strategy S10: ORB Fade ─────────────────────────────
def check_signal(bars, orb_high, orb_low):
    """
    S10: Fade el breakout del ORB.
    Retorna (direction, entry_price) o (0, 0)
    """
    if bars.empty: return 0, 0
    last  = bars.iloc[-1]
    price = last['close']
    if price > orb_high + 0.50:
        return -1, price   # SHORT — fade el breakout arriba
    if price < orb_low - 0.50:
        return 1, price    # LONG — fade el breakdown abajo
    return 0, 0

def check_exit(bars, state):
    """
    Monitorea TP/SL bar-by-bar.
    Retorna (exit_reason, exit_price) o (None, None)
    """
    if bars.empty: return None, None
    last = bars.iloc[-1]
    high = last['high']
    low  = last['low']
    d    = state['direction']
    tp   = state['tp']
    sl   = state['sl']

    if d == 1:
        if low  <= sl: return 'SL', sl
        if high >= tp: return 'TP', tp
    elif d == -1:
        if high >= sl: return 'SL', sl
        if low  <= tp: return 'TP', tp
    return None, None

# ── Main loop ──────────────────────────────────────────
def run():
    log.info("="*55)
    log.info("GLITCH SCHEDULER — Railway")
    log.info("Strategy: S10 ORB Fade (counter-trend)")
    log.info(f"DRY RUN: {os.getenv('DRY_RUN','true')}")
    log.info("="*55)

    dry_run    = os.getenv("DRY_RUN", "true").lower() == "true"
    today_str  = str(date.today())
    state      = load_state()
    paper_log  = load_log()

    # Reset state si es día nuevo
    if state.get("date") != today_str:
        log.info(f"New day: {today_str} — resetting state")
        reset_state()
        state = load_state()

    while True:
        now   = ct_now()
        phase = market_phase()
        today_str = str(date.today())

        # Reset diario
        if state.get("date") != today_str:
            log.info(f"New day: {today_str}")
            reset_state()
            state = load_state()

        log.info(f"[{now.strftime('%H:%M:%S')} CT] Phase={phase}")

        # ── OUT OF WINDOW ─────────────────────────────
        if phase == "out_of_window":
            # Check si hay trade abierto que flatten
            if state.get("trade_placed"):
                log.warning("Trade open outside window — recording FLATTEN")
                pnl = 0
                _record_trade(paper_log, state, "FLATTEN",
                              state['entry'], pnl, today_str)
                reset_state()
                state = load_state()

            # Log y duerme
            already_logged = any(
                str(t.get('date','')) == today_str
                for t in paper_log
            )
            if not already_logged and now.hour >= 15:
                paper_log_entry = {
                    "date": today_str,
                    "signal": False,
                    "pnl": 0,
                    "note": "out_of_window",
                }
                paper_log.append(paper_log_entry)
                save_log(paper_log)

            log.info(f"  Sleeping {SLEEP_INTERVAL}s...")
            time.sleep(SLEEP_INTERVAL)
            continue

        # ── BUILDING ORB (9:30-9:35) ──────────────────
        if phase == "building_orb":
            bars = fetch_bars()
            if not bars.empty:
                state['orb_high'] = float(bars['high'].max())
                state['orb_low']  = float(bars['low'].min())
                price = bars.iloc[-1]['close']
                log.info(f"  Building ORB: H={state['orb_high']:.2f} "
                         f"L={state['orb_low']:.2f} "
                         f"Range={state['orb_high']-state['orb_low']:.2f}pts "
                         f"Price={price:.2f}")
                save_state(state)
            time.sleep(POLL_INTERVAL)
            continue

        # ── SCANNING (9:35-14:30) ─────────────────────
        if phase in ("scanning", "closing"):

            # Finaliza ORB si no está built
            if not state.get("orb_built"):
                bars = fetch_bars()
                if not bars.empty:
                    orb_bars = bars[bars['ct_time'] < 9*60+35]
                    if not orb_bars.empty:
                        state['orb_high'] = float(orb_bars['high'].max())
                        state['orb_low']  = float(orb_bars['low'].min())
                orb_range = (state['orb_high'] or 0) - (state['orb_low'] or 0)

                if orb_range < 4.0:
                    log.info(f"  ORB range {orb_range:.2f}pts too tight — skip")
                    _record_no_trade(paper_log, today_str, "range_too_tight")
                    save_log(paper_log)
                    _sleep_until_tomorrow()
                    continue

                # Régimen filter
                _, prev_range, med_range = get_prev_ranges()
                if prev_range < med_range:
                    log.info(f"  Regime filter: {prev_range:.1f} < {med_range:.1f} — skip")
                    _record_no_trade(paper_log, today_str, "regime_filter")
                    save_log(paper_log)
                    _sleep_until_tomorrow()
                    continue

                tp_pts = max(orb_range*0.50, 4)
                sl_pts = max(orb_range*0.40, 3)
                state['orb_built'] = True
                state['tp_pts']    = tp_pts
                state['sl_pts']    = sl_pts
                log.info(f"  ORB ready: H={state['orb_high']:.2f} "
                         f"L={state['orb_low']:.2f} "
                         f"Range={orb_range:.2f} "
                         f"TP={tp_pts:.1f} SL={sl_pts:.1f}")
                save_state(state)

            # Ya operamos hoy?
            already_traded = any(
                str(t.get('date','')) == today_str and t.get('signal')
                for t in paper_log
            )

            # Flatten en closing
            if phase == "closing" and state.get("trade_placed"):
                bars = fetch_bars()
                last_price = bars.iloc[-1]['close'] if not bars.empty \
                             else state['entry']
                pnl = state['direction']*(last_price-state['entry'])*MES_POINT*NC
                log.info(f"  CLOSING TIME — flatten at {last_price:.2f} PnL=${pnl:+.2f}")
                _record_trade(paper_log, state, "FLATTEN",
                              last_price, pnl, today_str)
                save_log(paper_log)
                reset_state()
                state = load_state()
                _sleep_until_tomorrow()
                continue

            if already_traded or not state.get("orb_built"):
                time.sleep(POLL_INTERVAL)
                continue

            # Descarga barras y chequea
            bars = fetch_bars()
            if bars.empty:
                log.warning("  No bars — retry")
                time.sleep(30)
                continue

            price = bars.iloc[-1]['close']

            if not state.get("trade_placed"):
                # Busca señal
                direction, entry = check_signal(
                    bars,
                    state['orb_high'],
                    state['orb_low']
                )
                if direction != 0:
                    tp_pts = state['tp_pts']
                    sl_pts = state['sl_pts']
                    tp_p = round(entry + direction*tp_pts, 2)
                    sl_p = round(entry - direction*sl_pts, 2)

                    log.info(f"  SIGNAL: "
                             f"{'FADE SHORT ▼' if direction==-1 else 'FADE LONG ▲'}")
                    log.info(f"  Entry={entry:.2f} "
                             f"TP={tp_p:.2f} SL={sl_p:.2f}")
                    log.info(f"  TP={tp_pts:.1f}pts "
                             f"(+${tp_pts*NC*MES_POINT:.0f}) "
                             f"SL={sl_pts:.1f}pts "
                             f"(-${sl_pts*NC*MES_POINT:.0f})")

                    state['trade_placed'] = True
                    state['direction']    = direction
                    state['entry']        = entry
                    state['tp']           = tp_p
                    state['sl']           = sl_p
                    save_state(state)

                    if not dry_run:
                        # TODO: ejecutar orden real via ProjectX
                        log.info("  [LIVE] Order would execute here")
                    else:
                        log.info("  [DRY RUN] Signal logged, no order sent")
                else:
                    unr = price - state['orb_high'] if price > state['orb_high'] \
                          else state['orb_low'] - price if price < state['orb_low'] \
                          else 0
                    log.info(f"  Price={price:.2f}  "
                             f"ORB [{state['orb_low']:.2f}─{state['orb_high']:.2f}]  "
                             f"Waiting...")

            else:
                # Monitorea posición
                exit_reason, exit_price = check_exit(bars, state)
                unrealized = state['direction']*(price-state['entry'])*MES_POINT*NC
                log.info(f"  IN POSITION  Price={price:.2f}  "
                         f"Unreal={unrealized:+.2f}  "
                         f"TP={state['tp']:.2f} SL={state['sl']:.2f}")

                if exit_reason:
                    pnl = state['direction']*(exit_price-state['entry'])*MES_POINT*NC
                    log.info(f"  EXIT {exit_reason}: {exit_price:.2f}  "
                             f"PnL=${pnl:+.2f}")
                    _record_trade(paper_log, state, exit_reason,
                                  exit_price, pnl, today_str)
                    save_log(paper_log)
                    reset_state()
                    state = load_state()
                    _print_summary(paper_log)
                    _sleep_until_tomorrow()
                    continue

            time.sleep(POLL_INTERVAL)

def _record_trade(paper_log, state, reason, exit_price, pnl, today_str):
    paper_log.append({
        "date":        today_str,
        "signal":      True,
        "direction":   "LONG" if state['direction']==1 else "SHORT",
        "entry":       state['entry'],
        "exit":        exit_price,
        "tp":          state['tp'],
        "sl":          state['sl'],
        "exit_reason": reason,
        "pnl":         pnl,
        "orb_high":    state['orb_high'],
        "orb_low":     state['orb_low'],
    })
    save_log(paper_log)

def _record_no_trade(paper_log, today_str, note):
    if not any(str(t.get('date',''))==today_str for t in paper_log):
        paper_log.append({
            "date": today_str, "signal": False,
            "pnl": 0, "note": note,
        })

def _print_summary(paper_log):
    trades = [t for t in paper_log if t.get('signal')]
    if not trades: return
    wins  = [t for t in trades if t.get('pnl',0)>0]
    wr    = len(wins)/len(trades)
    total = sum(t.get('pnl',0) for t in trades)
    log.info(f"  SUMMARY: {len(trades)} trades  "
             f"WR={wr:.1%}  Total=${total:+.2f}")

def _sleep_until_tomorrow():
    now  = ct_now()
    mins_to_close = max(0, (15*60) - (now.hour*60+now.minute))
    sleep_s = mins_to_close*60 + 8*3600  # hasta las 8am CT mañana
    log.info(f"  Done for today — sleeping {sleep_s//3600:.0f}h")
    time.sleep(max(sleep_s, 300))

if __name__ == "__main__":
    run()
