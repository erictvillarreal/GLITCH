"""
Glitch Telegram Bot — Notificaciones en tiempo real
"""
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")

TOKEN   = "8996694212:AAHdGlnbM-0ACf6HvUS67f74tWaNowuUtsY"
CHAT_ID = "5154940894"
BASE    = f"https://api.telegram.org/bot{TOKEN}"

def send(msg: str):
    try:
        requests.post(f"{BASE}/sendMessage", json={
            "chat_id":    CHAT_ID,
            "text":       msg,
            "parse_mode": "HTML",
        }, timeout=10)
    except Exception as e:
        print(f"[Telegram] Error: {e}")

def notify_start(dry_run: bool):
    mode = "🟡 PAPER MODE" if dry_run else "🟢 LIVE MODE"
    send(f"""⚡ <b>GLITCH SCHEDULER ARRANCÓ</b>
{mode}
Estrategia: S10 ORB Fade
{datetime.now(CT).strftime('%a %d %b %Y  %H:%M CT')}""")

def notify_regime_skip(prev_range: float, median: float):
    send(f"""⚪ <b>REGIME FILTER — SIN TRADE HOY</b>
Rango ayer: {prev_range:.1f}pts
Mediana 20d: {median:.1f}pts
Mercado choppy — esperando mañana""")

def notify_orb(orb_high: float, orb_low: float,
               orb_range: float, tp_pts: float, sl_pts: float):
    send(f"""📐 <b>ORB FIJADO — {datetime.now(CT).strftime('%H:%M CT')}</b>
High:  {orb_high:.2f}
Low:   {orb_low:.2f}
Range: {orb_range:.2f} pts
TP: {tp_pts:.1f}pts | SL: {sl_pts:.1f}pts
Esperando breakout para fade...🎯""")

def notify_signal(direction: int, entry: float,
                  tp: float, sl: float,
                  tp_pts: float, sl_pts: float,
                  nc: int = 3, mes_point: float = 5.0):
    side = "▼ FADE SHORT" if direction == -1 else "▲ FADE LONG"
    profit = tp_pts * nc * mes_point
    loss   = sl_pts * nc * mes_point
    send(f"""🎯 <b>SEÑAL DETECTADA — {datetime.now(CT).strftime('%H:%M CT')}</b>
{side}
Entry: {entry:.2f}
TP:    {tp:.2f}  (+{tp_pts:.1f}pts = +${profit:.0f})
SL:    {sl:.2f}  (-{sl_pts:.1f}pts = -${loss:.0f})
RR: {tp_pts/sl_pts:.1f}:1""")

def notify_exit(reason: str, exit_price: float, pnl: float,
                entry: float, direction: int):
    icon  = "✅" if reason == "TP" else "❌" if reason == "SL" else "⏹"
    emoji = "🟢" if pnl > 0 else "🔴"
    send(f"""{icon} <b>EXIT {reason} — {datetime.now(CT).strftime('%H:%M CT')}</b>
{emoji} PnL: {"+" if pnl>=0 else ""}${pnl:.2f}
Entry: {entry:.2f} → Exit: {exit_price:.2f}""")

def notify_summary(paper_log: list):
    trades = [t for t in paper_log if t.get('signal')]
    if not trades: return
    wins      = [t for t in trades if t.get('pnl',0) > 0]
    losses    = [t for t in trades if t.get('pnl',0) < 0]
    total_pnl = sum(t.get('pnl',0) for t in trades)
    wr        = len(wins)/len(trades) if trades else 0
    ev_day    = total_pnl/len(paper_log) if paper_log else 0

    bar_w = 20
    done  = int(min(total_pnl/3000,1)*bar_w) if total_pnl>0 else 0
    bar   = '█'*done + '░'*(bar_w-done)
    pct   = min(total_pnl/3000*100,100) if total_pnl>0 else 0

    send(f"""📊 <b>RESUMEN ACUMULADO</b>
Días: {len(paper_log)} | Trades: {len(trades)}
WR: {wr:.1%} ({len(wins)}W/{len(losses)}L)
PnL total: {"+" if total_pnl>=0 else ""}${total_pnl:.2f}
EV/día: {"+" if ev_day>=0 else ""}${ev_day:.2f}

Combine: [{bar}] {pct:.1f}%
${total_pnl:.0f} / $3,000""")

def notify_no_signal(reason: str = "no_breakout"):
    msgs = {
        "no_breakout":    "⚪ Sin breakout hoy — precio se mantuvo dentro del ORB",
        "range_too_tight":"⚪ ORB range muy pequeño — sin trade",
        "regime_filter":  "⚪ Régimen filter — mercado choppy",
        "out_of_window":  "⚪ Fuera de ventana de operación",
    }
    send(msgs.get(reason, f"⚪ Sin señal: {reason}"))
