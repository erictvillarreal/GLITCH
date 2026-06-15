import os, sys, time, json, logging
from datetime import datetime, date
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scheduler.telegram_bot import (
    notify_start, notify_orb, notify_signal, notify_exit,
    notify_summary, notify_no_signal, notify_regime_skip, send
)

CT = ZoneInfo("America/Chicago")
logging.basicConfig(stream=__import__("sys").stdout, 
    level=logging.INFO,
    format="%(asctime)s CT [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("glitch")

MES_POINT     = 5.0
NC            = 3
LOG_FILE      = "paper_trade_log.json"
STATE_FILE    = ".scheduler_state.json"
POLL_INTERVAL = 60
SLEEP_INTERVAL= 300

def load_log():
    try:
        with open(LOG_FILE) as f: return json.load(f)
    except: return []

def save_log(l):
    with open(LOG_FILE,"w") as f: json.dump(l,f,indent=2,default=str)

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except:
        return {"orb_high":None,"orb_low":None,"orb_built":False,
                "trade_placed":False,"direction":0,"entry":0,
                "tp":0,"sl":0,"tp_pts":0,"sl_pts":0,"date":None}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f,indent=2,default=str)

def reset_state():
    save_state({"orb_high":None,"orb_low":None,"orb_built":False,
                "trade_placed":False,"direction":0,"entry":0,
                "tp":0,"sl":0,"tp_pts":0,"sl_pts":0,
                "date":str(date.today())})

def ct_now(): return datetime.now(CT)

def is_trading_day():
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {(2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
                (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)}
    return (now.year,now.month,now.day) not in holidays

def market_phase():
    now = ct_now()
    t   = now.hour*60 + now.minute
    if not is_trading_day():       return "out_of_window"
    if t < 9*60+30:                return "out_of_window"
    if t < 9*60+35:                return "building_orb"
    if t < 14*60+30:               return "scanning"
    if t < 15*60+0:                return "closing"
    return "out_of_window"

def fetch_bars():
    try:
        d = yf.Ticker("MES=F").history(period="5d",interval="1m",prepost=True)
        if d.empty: return pd.DataFrame()
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        d['datetime'] = pd.to_datetime(d[tcol],utc=True)
        d['ct']       = d['datetime'].dt.tz_convert(CT)
        d['ct_time']  = d['ct'].dt.hour*60 + d['ct'].dt.minute
        d['date']     = d['ct'].dt.date
        today = date.today()
        return d[(d['date']==today)&(d['ct_time']>=9*60+30)&
                 (d['ct_time']<=15*60+9)&
                 (d['ct'].dt.dayofweek<5)].copy().reset_index(drop=True)
    except Exception as e:
        log.error(f"fetch_bars: {e}"); return pd.DataFrame()

def get_prev_ranges():
    try:
        d = yf.Ticker("MES=F").history(period="30d",interval="1d",prepost=False)
        if d.empty or len(d)<3: return [],0,0
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        ranges = (d['high']-d['low']).values[-21:]
        return ranges, float(ranges[-2]), float(np.median(ranges[:-1]))
    except: return [],0,0

def check_signal(bars, orb_high, orb_low):
    if bars.empty: return 0,0
    price = bars.iloc[-1]['close']
    if price > orb_high+0.50: return -1, price
    if price < orb_low -0.50: return  1, price
    return 0,0

def check_exit(bars, state):
    if bars.empty: return None,None
    last = bars.iloc[-1]
    d,tp,sl = state['direction'],state['tp'],state['sl']
    if d==1:
        if last['low']  <= sl: return 'SL',sl
        if last['high'] >= tp: return 'TP',tp
    elif d==-1:
        if last['high'] >= sl: return 'SL',sl
        if last['low']  <= tp: return 'TP',tp
    return None,None

def already_logged_today(paper_log, today_str):
    return any(str(t.get('date',''))==today_str for t in paper_log)

def record_trade(paper_log, state, reason, exit_price, pnl, today_str):
    paper_log.append({
        "date":today_str,"signal":True,
        "direction":"LONG" if state['direction']==1 else "SHORT",
        "entry":state['entry'],"exit":exit_price,
        "tp":state['tp'],"sl":state['sl'],
        "exit_reason":reason,"pnl":pnl,
        "orb_high":state['orb_high'],"orb_low":state['orb_low'],
    })
    save_log(paper_log)

def sleep_until_tomorrow():
    """Duerme hasta las 9:25 AM CT del siguiente dia habil."""
    now = ct_now()
    # Calcula dias hasta el lunes si es viernes/sabado/domingo
    days_ahead = 1
    next_day = now.weekday() + 1  # dia de mañana
    if next_day == 5:    # mañana es sabado → esperar hasta lunes
        days_ahead = 3
    elif next_day == 6:  # mañana es domingo → esperar hasta lunes
        days_ahead = 2
    elif next_day == 7:  # hoy es domingo → esperar hasta lunes
        days_ahead = 1

    # Calcula segundos hasta las 9:25 AM CT del proximo dia habil
    from datetime import timedelta
    target = (now + timedelta(days=days_ahead)).replace(
        hour=9, minute=25, second=0, microsecond=0)
    secs = max(int((target - now).total_seconds()), 300)
    hrs  = secs // 3600
    mins = (secs % 3600) // 60
    log.info(f"Done for today — sleeping {hrs}h {mins}m until {target.strftime('%a %d %b %H:%M CT')}")
    time.sleep(secs)

def run():
    dry_run = os.getenv("DRY_RUN","true").lower()=="true"
    log.info("="*55)
    log.info("GLITCH SCHEDULER — Railway")
    log.info(f"Strategy: S10 ORB Fade | DRY_RUN={dry_run}")
    log.info("="*55)
    notify_start(dry_run)

    state     = load_state()
    paper_log = load_log()
    today_str = str(date.today())

    if state.get("date") != today_str:
        reset_state(); state = load_state()

    while True:
        now       = ct_now()
        phase     = market_phase()
        today_str = str(date.today())

        # Reset día nuevo
        if state.get("date") != today_str:
            log.info(f"New day: {today_str}")
            reset_state(); state = load_state()
            paper_log = load_log()

        log.info(f"[{now.strftime('%H:%M:%S')} CT] phase={phase}")

        # ── OUT OF WINDOW ──────────────────────────────
        if phase == "out_of_window":
            if state.get("trade_placed"):
                bars = fetch_bars()
                lp   = bars.iloc[-1]['close'] if not bars.empty else state['entry']
                pnl  = state['direction']*(lp-state['entry'])*MES_POINT*NC
                record_trade(paper_log,state,"FLATTEN",lp,pnl,today_str)
                notify_exit("FLATTEN",lp,pnl,state['entry'],state['direction'])
                notify_summary(paper_log)
                reset_state(); state=load_state()

            if now.hour>=15 and not already_logged_today(paper_log,today_str):
                paper_log.append({"date":today_str,"signal":False,
                                  "pnl":0,"note":"out_of_window"})
                save_log(paper_log)

            if now.hour >= 10:
                sleep_until_tomorrow()
            else:
                time.sleep(60)
            continue

        # ── BUILDING ORB (9:30-9:35) ───────────────────
        if phase == "building_orb":
            bars = fetch_bars()
            if not bars.empty:
                state['orb_high'] = float(bars['high'].max())
                state['orb_low']  = float(bars['low'].min())
                price = bars.iloc[-1]['close']
                log.info(f"  ORB building: H={state['orb_high']:.2f} "
                         f"L={state['orb_low']:.2f} "
                         f"Range={state['orb_high']-state['orb_low']:.2f} "
                         f"Price={price:.2f}")
                save_state(state)
            time.sleep(POLL_INTERVAL)
            continue

        # ── SCANNING / CLOSING ─────────────────────────
        if phase in ("scanning","closing"):

            # Finaliza ORB si no está built
            now_check = ct_now()
            if not state.get("orb_built") and now_check.hour >= 10:
                log.info("  Late start — skipping today")
                paper_log.append({"date":today_str,"signal":False,"pnl":0,"note":"late_start"})
                save_log(paper_log)
                save_log(paper_log)
                sleep_until_tomorrow()
                continue
            if not state.get("orb_built"):
                bars = fetch_bars()
                if not bars.empty:
                    orb_bars = bars[bars['ct_time']<9*60+35]
                    if not orb_bars.empty:
                        state['orb_high'] = float(orb_bars['high'].max())
                        state['orb_low']  = float(orb_bars['low'].min())

                orb_range = (state['orb_high'] or 0)-(state['orb_low'] or 0)

                if orb_range < 1.0:
                    log.info(f"  Range {orb_range:.2f}pts — Yahoo delay, retrying 60s")
                    time.sleep(60)
                    continue
                if orb_range < 4.0:
                    log.info(f"  Range {orb_range:.2f}pts too tight")
                    notify_no_signal("range_too_tight")
                    paper_log.append({"date":today_str,"signal":False,
                                      "pnl":0,"note":"range_too_tight"})
                    save_log(paper_log)
                    sleep_until_tomorrow(); break

                _,prev,med = get_prev_ranges()
                if prev > 0 and prev < med:
                    log.info(f"  Regime skip: {prev:.1f}<{med:.1f}")
                    notify_regime_skip(prev,med)
                    paper_log.append({"date":today_str,"signal":False,
                                      "pnl":0,"note":"regime_filter"})
                    save_log(paper_log)
                    sleep_until_tomorrow(); break

                tp_pts = max(orb_range*0.50,4)
                sl_pts = max(orb_range*0.40,3)
                state['orb_built']=True
                state['tp_pts']=tp_pts
                state['sl_pts']=sl_pts
                save_state(state)

                # Notifica ORB
                notify_orb(state['orb_high'],state['orb_low'],
                           orb_range,tp_pts,sl_pts)
                log.info(f"  ORB set: H={state['orb_high']:.2f} "
                         f"L={state['orb_low']:.2f} "
                         f"TP={tp_pts:.1f} SL={sl_pts:.1f}")

            # Flatten en closing
            if phase=="closing" and state.get("trade_placed"):
                bars = fetch_bars()
                lp   = bars.iloc[-1]['close'] if not bars.empty else state['entry']
                pnl  = state['direction']*(lp-state['entry'])*MES_POINT*NC
                log.info(f"  FLATTEN at {lp:.2f} PnL=${pnl:+.2f}")
                record_trade(paper_log,state,"FLATTEN",lp,pnl,today_str)
                notify_exit("FLATTEN",lp,pnl,state['entry'],state['direction'])
                notify_summary(paper_log)
                reset_state(); state=load_state()
                sleep_until_tomorrow(); break

            if already_logged_today(paper_log,today_str):
                # Send daily summary at 15:00 CT if not sent yet
                now_s = ct_now()
                if now_s.hour == 15 and now_s.minute == 0:
                    notify_daily_summary(paper_log)
                time.sleep(POLL_INTERVAL); continue

            # Descarga y chequea
            bars = fetch_bars()
            if bars.empty:
                time.sleep(30); continue

            price = bars.iloc[-1]['close']

            if not state.get("trade_placed"):
                direction,entry = check_signal(bars,
                                               state['orb_high'],
                                               state['orb_low'])
                if direction!=0:
                    tp_pts = state['tp_pts']
                    sl_pts = state['sl_pts']
                    tp_p   = round(entry+direction*tp_pts,2)
                    sl_p   = round(entry-direction*sl_pts,2)
                    state.update({
                        'trade_placed':True,'direction':direction,
                        'entry':entry,'tp':tp_p,'sl':sl_p
                    })
                    save_state(state)
                    notify_signal(direction,entry,tp_p,sl_p,
                                  tp_pts,sl_pts,NC,MES_POINT)
                    log.info(f"  SIGNAL: {'SHORT' if direction==-1 else 'LONG'} "
                             f"entry={entry:.2f} TP={tp_p:.2f} SL={sl_p:.2f}")
                else:
                    log.info(f"  Price={price:.2f} "
                             f"ORB[{state['orb_low']:.2f}─{state['orb_high']:.2f}] "
                             f"waiting...")
            else:
                exit_reason,exit_price = check_exit(bars,state)
                unr = state['direction']*(price-state['entry'])*MES_POINT*NC
                log.info(f"  IN POSITION price={price:.2f} "
                         f"unreal={unr:+.2f} "
                         f"TP={state['tp']:.2f} SL={state['sl']:.2f}")
                if exit_reason:
                    pnl = state['direction']*(exit_price-state['entry'])*MES_POINT*NC
                    log.info(f"  EXIT {exit_reason} {exit_price:.2f} PnL=${pnl:+.2f}")
                    record_trade(paper_log,state,exit_reason,exit_price,pnl,today_str)
                    notify_exit(exit_reason,exit_price,pnl,
                                state['entry'],state['direction'])
                    notify_summary(paper_log)
                    reset_state(); state=load_state()
                    sleep_until_tomorrow(); break

            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
