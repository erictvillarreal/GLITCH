"""
Glitch Telegram Bot — Notificaciones estilo profesional
"""
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CT    = ZoneInfo("America/Chicago")
UTC   = timezone.utc
TOKEN = "8996694212:AAHdGlnbM-0ACf6HvUS67f74tWaNowuUtsY"
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

def _now_utc():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

def _direction_str(direction: int) -> str:
    return "LONG" if direction == 1 else "SHORT"

# ── TRADE OPEN ────────────────────────────────────────
def notify_signal(direction: int, entry: float,
                  tp: float, sl: float,
                  tp_pts: float, sl_pts: float,
                  nc: int = 3, mes_point: float = 5.0,
                  dry_run: bool = True,
                  orb_range: float = 0,
                  equity: float = 50000):

    mode = "PAPER" if dry_run else "LIVE"
    ev   = tp_pts * nc * mes_point
    # p_up = probabilidad implícita basada en WR backtest
    p_up = 0.762  # S10 WR
    stake= sl_pts * nc * mes_point

    send(f"""S10 TRADE [{mode}]
Symbol: MES (Micro E-mini S&P500)
Direction: {_direction_str(direction)}
Entry: ${entry:,.2f}
TP: ${tp:,.2f}  ({'+' if direction==1 else '-'}{tp_pts:.1f}pts)
SL: ${sl:,.2f}  ({'-' if direction==1 else '+'}{sl_pts:.1f}pts)
EV: ${ev:.2f}
p_win: {p_up:.3f}
Stake: ${stake:.2f}
ORB Range: {orb_range:.1f}pts
Equity: ${equity:,.2f}
{_now_utc()}""")

# ── TRADE CLOSE ───────────────────────────────────────
def notify_exit(reason: str, exit_price: float, pnl: float,
                entry: float, direction: int,
                dry_run: bool = True,
                equity: float = 50000):

    mode   = "PAPER" if dry_run else "LIVE"
    result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"
    sign   = "+" if pnl >= 0 else ""

    send(f"""S10 CLOSE [{result}] [{mode}]
Symbol: MES (Micro E-mini S&P500)
Direction: {_direction_str(direction)}
Entry: ${entry:,.2f}
Exit via: {reason} (${exit_price:,.2f})
PnL real: ${sign}{pnl:.2f}
Equity: ${equity:,.2f}
{_now_utc()}""")

# ── ORB BUILT ─────────────────────────────────────────
def notify_orb(orb_high: float, orb_low: float,
               orb_range: float, tp_pts: float, sl_pts: float):
    send(f"""📐 S10 ORB FIJADO
High:  ${orb_high:,.2f}
Low:   ${orb_low:,.2f}
Range: {orb_range:.2f}pts
TP params: {tp_pts:.1f}pts | SL params: {sl_pts:.1f}pts
Esperando breakout para fade...
{_now_utc()}""")

# ── REGIME SKIP ───────────────────────────────────────
def notify_regime_skip(prev_range: float, median: float):
    send(f"""⚪ S10 NO TRADE — Regime Filter
Rango ayer: {prev_range:.1f}pts
Mediana 20d: {median:.1f}pts
Mercado choppy — sin operación hoy
{_now_utc()}""")

# ── NO SIGNAL ─────────────────────────────────────────
def notify_no_signal(reason: str = "no_breakout"):
    msgs = {
        "no_breakout":    "precio dentro del ORB todo el día",
        "range_too_tight":"ORB range < 4pts",
        "regime_filter":  "régimen choppy",
        "out_of_window":  "fuera de ventana",
    }
    send(f"""⚪ S10 NO TRADE
Razón: {msgs.get(reason, reason)}
{_now_utc()}""")

# ── DAILY SUMMARY ─────────────────────────────────────
def notify_summary(paper_log: list, equity: float = 50000):
    trades    = [t for t in paper_log if t.get('signal')]
    if not trades: return
    wins      = [t for t in trades if t.get('pnl',0) > 0]
    losses    = [t for t in trades if t.get('pnl',0) < 0]
    total_pnl = sum(t.get('pnl',0) for t in trades)
    wr        = len(wins)/len(trades) if trades else 0
    ev_day    = total_pnl/len(paper_log) if paper_log else 0
    sign      = "+" if total_pnl >= 0 else ""

    bar_w = 15
    done  = int(min(max(total_pnl,0)/3000,1)*bar_w)
    bar   = '█'*done + '░'*(bar_w-done)
    pct   = min(max(total_pnl,0)/3000*100,100)

    send(f"""📊 S10 RESUMEN ACUMULADO
Días: {len(paper_log)} | Trades: {len(trades)}
WR: {wr:.1%}  ({len(wins)}W / {len(losses)}L)
PnL total: ${sign}{total_pnl:.2f}
EV/día: ${"+" if ev_day>=0 else ""}{ev_day:.2f}
Equity: ${equity:,.2f}

Combine: [{bar}] {pct:.1f}%
${max(total_pnl,0):.0f} / $3,000
{_now_utc()}""")

# ── STARTUP ───────────────────────────────────────────
def notify_start(dry_run: bool):
    mode = "PAPER" if dry_run else "LIVE"
    send(f"""⚡ GLITCH SCHEDULER [{mode}]
Strategy: S10 ORB Fade (counter-trend)
Symbol: MES Micro E-mini S&P500
WR backtest: 76.2% | Pass rate: 100%
Railway: activo 24/7
{_now_utc()}""")
