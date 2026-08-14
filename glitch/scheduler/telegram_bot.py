"""
Glitch Telegram Bot — Brain 1 + Brain 2 notifications
"""
import requests
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo

CT      = ZoneInfo("America/Chicago")
UTC     = timezone.utc
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

def _now_utc():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

# ── BRAIN 1 — TRADE OPEN ─────────────────────────────
def notify_brain1_open(direction: str, entry: float,
                        tp: float, sl: float,
                        nc: int,
                        combine_pnl: float,
                        combine_goal: float = 3000.0,
                        combine_floor: float = 2000.0,
                        dry_run: bool = True):
    mode = "PAPER LIVE" if dry_run else "LIVE"
    pct  = min(max(combine_pnl, 0) / combine_goal * 100, 100)
    left = max(combine_goal - combine_pnl, 0)
    dd   = combine_floor

    send(f"""GLITCH DETECTED - BRAIN 1
{mode}
STATUS: OPEN
{direction}: {entry:,.2f}
TP/SL: {tp:,.2f} - {sl:,.2f}
ASSET: MES
SIZE: {nc} Contracts
% OF COMBINE: {pct:.1f}%
$ LEFT TO GOAL: ${left:,.0f} USD
MAX TRAILING DD: ${dd:,.0f} USD
{_now_utc()}""")

# ── BRAIN 1 — TRADE CLOSE ────────────────────────────
def notify_brain1_close(direction: str, entry: float,
                         exit_price: float, result: str,
                         pnl: float,
                         combine_pnl: float,
                         combine_goal: float = 3000.0,
                         combine_floor: float = 2000.0,
                         dry_run: bool = True):
    mode  = "PAPER LIVE" if dry_run else "LIVE"
    emoji = "✅" if pnl > 0 else "❌"
    pct   = min(max(combine_pnl, 0) / combine_goal * 100, 100)
    left  = max(combine_goal - combine_pnl, 0)
    bar_w = 15
    done  = int(pct / 100 * bar_w)
    bar   = "█" * done + "░" * (bar_w - done)

    send(f"""{emoji} GLITCH CLOSED - BRAIN 1
{mode} | {result}
{direction}: {entry:,.2f} → {exit_price:,.2f}
PnL: ${pnl:+,.2f} USD
ASSET: MES

COMBINE PROGRESS:
[{bar}] {pct:.1f}%
$ LEFT TO GOAL: ${left:,.0f} USD
MAX TRAILING DD: ${combine_floor:,.0f} USD
{_now_utc()}""")

# ── BRAIN 1 — NO SIGNAL ──────────────────────────────
def notify_brain1_no_signal(reason: str,
                              combine_pnl: float,
                              combine_goal: float = 3000.0):
    pct  = min(max(combine_pnl, 0) / combine_goal * 100, 100)
    left = max(combine_goal - combine_pnl, 0)
    bar_w = 15
    done  = int(pct / 100 * bar_w)
    bar   = "█" * done + "░" * (bar_w - done)

    send(f"""⚪ GLITCH - BRAIN 1 | NO SIGNAL
Reason: {reason}

COMBINE PROGRESS:
[{bar}] {pct:.1f}%
$ LEFT TO GOAL: ${left:,.0f} USD
{_now_utc()}""")

# ── BRAIN 2 — TRADE OPEN ─────────────────────────────
def notify_brain2_open(direction: str, entry: float,
                        tp: float, sl: float,
                        nc: int,
                        xfa_balance: float,
                        payout_pct: float = 0.05,
                        min_buffer: float = 2000.0,
                        winning_days: int = 0,
                        days_to_payout: int = 5,
                        dry_run: bool = True):
    mode          = "PAPER LIVE" if dry_run else "LIVE"
    est_payout    = min(xfa_balance * payout_pct, 5000) * 0.90
    post_buf      = xfa_balance - min(xfa_balance * payout_pct, 5000)
    days_left     = max(days_to_payout - winning_days, 0)

    send(f"""GLITCH DETECTED - BRAIN 2
{mode} - OPEN
{direction}: {entry:,.2f}
TP/SL: {tp:,.2f} - {sl:,.2f}
ASSET: MES
SIZE: {nc} Contracts
ACCUMULATED BALANCE: ${xfa_balance:,.2f} USD
EST. PAYOUT (5% RULE): ${est_payout:,.2f} USD
BUFFER POST-PAYOUT: ${post_buf:,.2f} USD (Floor: ${min_buffer:,.0f} USD)
DAYS TO NEXT PAYOUT (D. PAYOUT): {days_left} Days
{_now_utc()}""")

# ── BRAIN 2 — TRADE CLOSE ────────────────────────────
def notify_brain2_close(direction: str, entry: float,
                         exit_price: float, result: str,
                         pnl: float,
                         xfa_balance: float,
                         payout_pct: float = 0.05,
                         min_buffer: float = 2000.0,
                         winning_days: int = 0,
                         days_to_payout: int = 5,
                         dry_run: bool = True):
    mode       = "PAPER LIVE" if dry_run else "LIVE"
    emoji      = "✅" if pnl > 0 else "❌"
    est_payout = min(xfa_balance * payout_pct, 5000) * 0.90
    post_buf   = xfa_balance - min(xfa_balance * payout_pct, 5000)
    days_left  = max(days_to_payout - winning_days, 0)

    send(f"""{emoji} GLITCH CLOSED - BRAIN 2
{mode} | {result}
{direction}: {entry:,.2f} → {exit_price:,.2f}
PnL: ${pnl:+,.2f} USD
ASSET: MES

XFA STATUS:
ACCUMULATED BALANCE: ${xfa_balance:,.2f} USD
EST. PAYOUT (5% RULE): ${est_payout:,.2f} USD
BUFFER POST-PAYOUT: ${post_buf:,.2f} USD (Floor: ${min_buffer:,.0f} USD)
DAYS TO NEXT PAYOUT (D. PAYOUT): {days_left} Days
{_now_utc()}""")

# ── BRAIN 2 — NO SIGNAL ──────────────────────────────
def notify_brain2_no_signal(reason: str,
                              xfa_balance: float,
                              winning_days: int = 0,
                              days_to_payout: int = 5):
    days_left = max(days_to_payout - winning_days, 0)
    send(f"""⚪ GLITCH - BRAIN 2 | NO SIGNAL
Reason: {reason}
ACCUMULATED BALANCE: ${xfa_balance:,.2f} USD
DAYS TO NEXT PAYOUT: {days_left} Days
{_now_utc()}""")

# ── PAYOUT ALERT ─────────────────────────────────────
def notify_payout_eligible(xfa_balance: float,
                            payout_pct: float = 0.05,
                            min_buffer: float = 2000.0):
    gross      = min(xfa_balance * payout_pct, 5000)
    take       = gross * 0.90
    post_buf   = xfa_balance - gross
    eligible   = post_buf >= min_buffer

    send(f"""💰 GLITCH - BRAIN 2 | PAYOUT ELIGIBLE
ACCUMULATED BALANCE: ${xfa_balance:,.2f} USD
EST. PAYOUT (5% RULE): ${take:,.2f} USD
BUFFER POST-PAYOUT: ${post_buf:,.2f} USD
Floor: ${min_buffer:,.0f} USD
ACTION: {"✅ REQUEST PAYOUT" if eligible else "⏳ HOLD — buffer too low"}
{_now_utc()}""")

# ── LEGACY — mantener compatibilidad con glitch_scheduler.py viejo ──
def notify_start(dry_run: bool = True):
    mode = "PAPER" if dry_run else "LIVE"
    send(f"⚡ GLITCH [{mode}] Starting...\n{_now_utc()}")

def notify_orb(orb_high, orb_low, orb_range, tp_pts, sl_pts):
    pass  # deprecated

def notify_regime_skip(prev_range, median):
    notify_brain1_no_signal(f"Regime choppy ({prev_range:.1f}pts < {median:.1f}pts median)", 0)

def notify_no_signal(reason="no_breakout"):
    notify_brain1_no_signal(reason, 0)

def notify_summary(paper_log, equity=50000):
    pass  # deprecated — usar notify_brain1_close

def notify_daily_summary(paper_log):
    pass  # deprecated
