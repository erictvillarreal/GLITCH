"""
Glitch Paper Trader v4 — S10: ORB Fade (Counter-trend)
========================================================
Estrategia: fade el breakout del ORB
  - Si precio rompe ORB HIGH → entra SHORT (fade)
  - Si precio rompe ORB LOW  → entra LONG  (fade)
  - TP = 50% del rango del ORB
  - SL = 40% del rango del ORB

Lógica real de trader:
  9:10 → descarga contexto, régimen filter
  9:30-9:35 → construye ORB en tiempo real
  9:35+ → espera breakout, entra CONTRA la dirección
  Sin señal → no opera
  3:00 PM → flatten automático
"""

import sys, os, time, json, argparse
from datetime import datetime, date
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import numpy as np

sys.path.insert(0, '.')
CT        = ZoneInfo("America/Chicago")
MES_POINT = 5.0
NC        = 3
LOG_FILE  = "paper_trade_log.json"

def load_log():
    try:
        with open(LOG_FILE) as f: return json.load(f)
    except: return []

def save_log(log):
    with open(LOG_FILE,"w") as f:
        json.dump(log, f, indent=2, default=str)

def get_bars(days=5):
    try:
        d = yf.Ticker("MES=F").history(
            period="8d", interval="1m", prepost=True)
        if d.empty: return pd.DataFrame()
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        d['datetime'] = pd.to_datetime(d[tcol], utc=True)
        d['ct']       = d['datetime'].dt.tz_convert(CT)
        d['ct_time']  = d['ct'].dt.hour*60 + d['ct'].dt.minute
        d['date']     = d['ct'].dt.date
        return d.sort_values('datetime').reset_index(drop=True)
    except Exception as e:
        print(f"[Data] Error: {e}")
        return pd.DataFrame()

def get_todays_rth(df):
    today = date.today()
    return df[
        (df['date'] == today) &
        (df['ct_time'] >= 9*60+30) &
        (df['ct_time'] <= 15*60+9)
    ].copy().reset_index(drop=True)

def get_regime(df):
    today  = date.today()
    past   = df[
        (df['date'] < today) &
        (df['ct_time'] >= 9*60+30) &
        (df['ct_time'] <= 15*60+9)
    ].copy()
    if past.empty: return 0, 0, True
    daily_ranges = past.groupby('date').apply(
        lambda x: x['high'].max() - x['low'].min())
    if len(daily_ranges) < 2: return 0, 0, True
    prev_range   = daily_ranges.iloc[-1]
    median_range = daily_ranges.median()
    return prev_range, median_range, prev_range >= median_range

def print_summary(log):
    if not log: return
    trades    = [t for t in log if t.get('signal')]
    no_sig    = [t for t in log if not t.get('signal')]
    wins      = [t for t in trades if t.get('pnl',0) > 0]
    losses    = [t for t in trades if t.get('pnl',0) < 0]
    total_pnl = sum(t.get('pnl',0) for t in trades)
    wr        = len(wins)/len(trades) if trades else 0

    print(f"\n{'═'*58}")
    print(f"  PAPER TRADING SUMMARY — {len(log)} días")
    print(f"  Estrategia: S10 ORB Fade (counter-trend)")
    print(f"{'═'*58}")
    print(f"  Días totales:  {len(log)}")
    print(f"  Trades:        {len(trades)}")
    print(f"  Sin señal:     {len(no_sig)}")
    print(f"  Win rate:      {wr:.1%}  ({len(wins)}W/{len(losses)}L)")
    print(f"  Total PnL:     {'+'if total_pnl>=0 else ''}${total_pnl:.2f}")

    if trades:
        avg_w = np.mean([t['pnl'] for t in wins])   if wins   else 0
        avg_l = np.mean([t['pnl'] for t in losses]) if losses else 0
        ev    = wr*avg_w - (1-wr)*abs(avg_l)
        print(f"  Avg win:       +${avg_w:.2f}")
        print(f"  Avg loss:       ${avg_l:.2f}")
        print(f"  EV/trade:      {'+'if ev>=0 else ''}${ev:.2f}")
        ev_day = total_pnl/len(log)
        print(f"  EV/día:        {'+'if ev_day>=0 else ''}${ev_day:.2f}")

    print(f"\n  {'Fecha':>12} {'Dir':>6} {'ORB rng':>8} "
          f"{'Entry':>8} {'Exit':>8} {'Razón':>8} {'PnL':>8}")
    print(f"  {'─'*60}")
    for t in log[-14:]:
        if t.get('signal'):
            pnl = t.get('pnl',0)
            rng = t.get('orb_range',0)
            print(f"  {str(t['date']):>12} "
                  f"{t.get('direction','?'):>6} "
                  f"{rng:>8.1f} "
                  f"{t.get('entry',0):>8.2f} "
                  f"{t.get('exit',0):>8.2f} "
                  f"{t.get('exit_reason','?'):>8} "
                  f"{'+'if pnl>0 else ''}${pnl:>6.2f}")
        else:
            print(f"  {str(t['date']):>12} "
                  f"{'─':>6} {'─':>8} {'─':>8} {'─':>8} "
                  f"{t.get('note','─'):>8} {'$0.00':>8}")

    if trades and total_pnl > 0:
        bar_w = 30
        done  = int(min(total_pnl/3000,1)*bar_w)
        bar   = '█'*done + '░'*(bar_w-done)
        pct   = min(total_pnl/3000*100,100)
        print(f"\n  Combine: ${total_pnl:.0f}/$3,000  [{bar}] {pct:.1f}%")
        if len(trades)>0 and ev_day>0:
            days_left = max(0,(3000-total_pnl)/ev_day)
            print(f"  Est. días restantes: ~{days_left:.0f}")
    print(f"{'═'*58}\n")

def run_paper_day():
    today  = date.today()
    now_ct = datetime.now(CT)
    log    = load_log()

    if any(str(t.get('date',''))==str(today) for t in log):
        print("[Paper] Ya registrado hoy.")
        print_summary(log)
        return

    print(f"\n{'='*58}")
    print(f"  GLITCH PAPER TRADER v4 — S10: ORB FADE")
    print(f"  {now_ct.strftime('%A %d %b %Y  %H:%M CT')}")
    print(f"  Counter-trend: fade el breakout del ORB")
    print(f"{'='*58}\n")

    # Tiempos
    orb_open   = now_ct.replace(hour=9,  minute=30, second=0, microsecond=0)
    orb_close  = now_ct.replace(hour=9,  minute=35, second=0, microsecond=0)
    scan_until = now_ct.replace(hour=14, minute=30, second=0, microsecond=0)
    flatten_at = now_ct.replace(hour=15, minute=0,  second=0, microsecond=0)

    # Descarga contexto
    print(f"[{now_ct.strftime('%H:%M')}] Descargando contexto...")
    all_bars = get_bars(days=10)
    if all_bars.empty:
        print("[Error] Sin datos.")
        return

    # Régimen filter
    prev_range, median_range, should_trade = get_regime(all_bars)
    print(f"[Régimen] Rango ayer: {prev_range:.1f}pts  "
          f"Mediana: {median_range:.1f}pts  "
          f"→ {'GO ✓' if should_trade else 'SKIP ✗'}")

    if not should_trade:
        log.append({"date":str(today),"signal":False,
                    "pnl":0,"note":"regime_filter"})
        save_log(log)
        print_summary(log)
        return

    # Esperar 9:30
    if now_ct < orb_open:
        wait_s = int((orb_open-now_ct).total_seconds())
        print(f"[{now_ct.strftime('%H:%M')}] "
              f"Esperando apertura en {wait_s//60}m {wait_s%60}s...")
        while datetime.now(CT) < orb_open:
            time.sleep(15)
        print("[9:30] Mercado abierto — observando ORB...")

    # Construir ORB 9:30-9:35
    orb_high = -np.inf
    orb_low  =  np.inf
    orb_set  = False

    while not orb_set:
        now_ct = datetime.now(CT)
        if now_ct >= orb_close:
            orb_set = True
            break
        today_bars = get_todays_rth(get_bars(days=1))
        if not today_bars.empty:
            orb_high = today_bars['high'].max()
            orb_low  = today_bars['low'].min()
            price    = today_bars.iloc[-1]['close']
            print(f"\r[{now_ct.strftime('%H:%M:%S')}] "
                  f"MES={price:.2f}  "
                  f"ORB H={orb_high:.2f} L={orb_low:.2f}  "
                  f"Range={orb_high-orb_low:.2f}pts",
                  end='', flush=True)
        time.sleep(15)

    print()
    orb_range = orb_high - orb_low

    if orb_range < 4.0:
        print(f"[ORB] Range {orb_range:.2f}pts muy pequeño — sin trade")
        log.append({"date":str(today),"signal":False,
                    "pnl":0,"note":"range_too_tight"})
        save_log(log)
        print_summary(log)
        return

    # TP y SL basados en el ORB range
    tp_pts = max(orb_range*0.50, 4)
    sl_pts = max(orb_range*0.40, 3)

    print(f"\n[9:35] ORB FIJADO: H={orb_high:.2f} L={orb_low:.2f} "
          f"Range={orb_range:.2f}pts")
    print(f"[9:35] Parámetros: TP={tp_pts:.1f}pts SL={sl_pts:.1f}pts")
    print(f"[9:35] Esperando breakout para FADE...\n")

    # Esperar breakout y entrar CONTRA
    trade_placed = False
    direction    = 0
    entry_price  = 0
    tp_price     = 0
    sl_price     = 0
    exit_reason  = ""
    exit_price   = 0
    daily_pnl    = 0

    while True:
        now_ct = datetime.now(CT)

        if now_ct >= flatten_at and trade_placed:
            exit_price  = entry_price
            exit_reason = "FLATTEN"
            daily_pnl   = 0
            print(f"\n[3:00] Flatten")
            break

        if now_ct >= scan_until and not trade_placed:
            print(f"\n[{now_ct.strftime('%H:%M')}] Sin señal hoy")
            log.append({"date":str(today),"signal":False,
                        "pnl":0,"note":"no_breakout"})
            save_log(log)
            print_summary(log)
            return

        today_bars = get_todays_rth(get_bars(days=1))
        if today_bars.empty:
            time.sleep(30)
            continue

        last  = today_bars.iloc[-1]
        price = last['close']
        high  = last['high']
        low   = last['low']

        if not trade_placed:
            # FADE: breakout arriba → SHORT, breakout abajo → LONG
            if price > orb_high + 0.50:
                direction    = -1   # SHORT — fade el breakout
                entry_price  = price
                tp_price     = round(price - tp_pts, 2)
                sl_price     = round(price + sl_pts, 2)
                trade_placed = True
                print(f"\n{'─'*55}")
                print(f"  🔄 FADE SHORT ▼  (precio rompió arriba)")
                print(f"  Entry:  {entry_price:.2f}")
                print(f"  TP:     {tp_price:.2f}  "
                      f"(-{tp_pts:.1f}pts = "
                      f"+${tp_pts*NC*MES_POINT:.0f})")
                print(f"  SL:     {sl_price:.2f}  "
                      f"(+{sl_pts:.1f}pts = "
                      f"-${sl_pts*NC*MES_POINT:.0f})")
                print(f"{'─'*55}\n")

            elif price < orb_low - 0.50:
                direction    = 1    # LONG — fade el breakdown
                entry_price  = price
                tp_price     = round(price + tp_pts, 2)
                sl_price     = round(price - sl_pts, 2)
                trade_placed = True
                print(f"\n{'─'*55}")
                print(f"  🔄 FADE LONG ▲  (precio rompió abajo)")
                print(f"  Entry:  {entry_price:.2f}")
                print(f"  TP:     {tp_price:.2f}  "
                      f"(+{tp_pts:.1f}pts = "
                      f"+${tp_pts*NC*MES_POINT:.0f})")
                print(f"  SL:     {sl_price:.2f}  "
                      f"(-{sl_pts:.1f}pts = "
                      f"-${sl_pts*NC*MES_POINT:.0f})")
                print(f"{'─'*55}\n")
            else:
                print(f"\r[{now_ct.strftime('%H:%M:%S')}] "
                      f"MES={price:.2f}  "
                      f"ORB [{orb_low:.2f}─{orb_high:.2f}]  "
                      f"Esperando breakout para fade...",
                      end='', flush=True)

        else:
            unrealized = direction*(price-entry_price)*MES_POINT*NC
            print(f"\r[{now_ct.strftime('%H:%M:%S')}] "
                  f"MES={price:.2f}  "
                  f"Unreal: {'+'if unrealized>=0 else ''}"
                  f"${unrealized:.2f}  "
                  f"TP={tp_price:.2f} SL={sl_price:.2f}",
                  end='', flush=True)

            if direction == 1:
                if high >= tp_price: exit_price=tp_price; exit_reason='TP'
                elif low <= sl_price: exit_price=sl_price; exit_reason='SL'
            else:
                if low  <= tp_price: exit_price=tp_price; exit_reason='TP'
                elif high >= sl_price: exit_price=sl_price; exit_reason='SL'

            if exit_reason:
                daily_pnl = direction*(exit_price-entry_price)*MES_POINT*NC
                icon = "✅" if exit_reason=="TP" else "❌"
                print(f"\n\n  {icon} EXIT {exit_reason}: "
                      f"{exit_price:.2f}  "
                      f"PnL: {'+'if daily_pnl>0 else ''}"
                      f"${daily_pnl:.2f}")
                break

        time.sleep(30)

    if trade_placed:
        log.append({
            "date":        str(today),
            "signal":      True,
            "direction":   "LONG" if direction==1 else "SHORT",
            "entry":       entry_price,
            "exit":        exit_price,
            "tp":          tp_price,
            "sl":          sl_price,
            "exit_reason": exit_reason or "open",
            "pnl":         daily_pnl,
            "orb_range":   orb_range,
            "tp_pts":      tp_pts,
            "sl_pts":      sl_pts,
        })
        save_log(log)
    print_summary(log)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    if args.review:
        log = load_log()
        print_summary(log) if log else print("Sin datos aún.")
    else:
        run_paper_day()
