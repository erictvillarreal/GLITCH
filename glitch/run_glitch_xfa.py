"""
Glitch — XFA Runner (Cerebro 2)
================================
Momentum intraday para maximizar EV en Express Funded Account.

Estrategia: entrada en barra 2 (30min post-open)
dirección basada en momentum vs open.
TP=12pts, SL=3pts, 5 contratos MES.

Uso:
  python run_glitch_xfa.py --env live --account 12345
  python run_glitch_xfa.py --env demo --account 12345 --dry-run
"""

import sys, os, time, argparse, logging, json
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '.')

from brokers.projectx import ProjectXClient, ProjectXCredentials, OrderSide
from core.safety import (
    BracketMonitor, FlattenFailsafe,
    ConsistencyGuard, pre_flight_check
)

CT  = ZoneInfo("America/Chicago")
MES = 5.0

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers= [
        logging.StreamHandler(),
        logging.FileHandler("glitch_xfa.log"),
    ]
)
log = logging.getLogger("glitch.xfa")

STATE_FILE = ".glitch_xfa_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"daily_pnls": [], "total_payouts": 0,
            "total_payout_amount": 0.0, "winning_days": 0}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

def wait_for_momentum_signal(client, contract_id: str,
                              entry_time_ct, scan_until_ct,
                              dry_run: bool = False):
    """
    Cerebro 2: espera hasta las 10:00 AM CT (barra 2 de 15min),
    determina dirección por momentum vs open.
    Retorna (direction, entry_price).
    """
    if dry_run:
        log.info("[C2] DRY RUN — simulating long signal at 5000.00")
        return 1, 5000.00

    log.info(f"[C2] Waiting for momentum signal at "
             f"{entry_time_ct.strftime('%H:%M')} CT...")

    while True:
        now = datetime.now(CT)

        if now > scan_until_ct:
            log.info("[C2] Scan window expired — no signal")
            return 0, 0.0

        if now < entry_time_ct:
            time.sleep(15)
            continue

        # Entry time reached — get bars and determine direction
        try:
            bars = client.get_bars(contract_id, bar_type=1,
                                    bar_size=1, count=35)
            if not bars or len(bars) < 3:
                time.sleep(10)
                continue

            open_price  = bars[0].get('open', bars[0].get('close', 0))
            entry_price = bars[-1].get('close', 0)

            if entry_price <= 0:
                time.sleep(10)
                continue

            # Momentum: current price vs open
            momentum = entry_price - open_price
            side     = 1 if momentum >= 0 else -1
            direction_str = "LONG" if side == 1 else "SHORT"

            log.info(f"[C2] Signal: {direction_str} "
                     f"| Open={open_price:.2f} "
                     f"| Entry={entry_price:.2f} "
                     f"| Momentum={momentum:+.2f}pts")
            return side, entry_price

        except Exception as e:
            log.warning(f"[C2] Signal error: {e}")
            time.sleep(10)


def check_payout_eligibility(state: dict,
                               account_balance: float,
                               min_balance: float = 55_000) -> tuple[bool, str]:
    """
    Verifica si es elegible para solicitar payout.
    Regla: 5 winning days de $150+ Y balance >= $55,000.
    """
    winning_days = state.get("winning_days", 0)
    if account_balance < min_balance:
        return False, (f"Balance ${account_balance:,.0f} < "
                       f"${min_balance:,.0f} threshold")
    if winning_days < 5:
        return False, f"Only {winning_days}/5 winning days ($150+)"
    return True, (f"ELIGIBLE: {winning_days} winning days, "
                  f"balance ${account_balance:,.0f}")


def run_xfa_day(
    credentials: ProjectXCredentials,
    account_id:  int,
    dry_run:     bool  = False,
    n_contracts: int   = 5,
    tp_pts:      float = 12.0,
    sl_pts:      float = 3.0,
    symbol:      str   = "CON.F.US.EP.M26",
    min_payout_balance: float = 55_000.0,
):
    now    = datetime.now(CT)
    state  = load_state()
    client = ProjectXClient(credentials)

    log.info("=" * 55)
    log.info(f"GLITCH XFA — {now.strftime('%Y-%m-%d %A')}")
    log.info(f"Winning days: {state.get('winning_days',0)}/5  "
             f"Total payouts: ${state.get('total_payout_amount',0):,.0f}")
    log.info("=" * 55)

    # ── Times ──────────────────────────────────────────
    # Entry at 10:00 AM CT (30min post-open = bar 2 of 15min)
    entry_time = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    scan_until = now.replace(hour=14, minute=30, second=0, microsecond=0)
    flatten_at = now.replace(hour=15, minute=0,  second=0, microsecond=0)

    # ── Consistency guard (XFA uses 40% consistency rule) ──
    guard = ConsistencyGuard(profit_target=999_999)
    guard.CONSISTENCY_LIMIT = 0.40
    guard.SAFETY_BUFFER     = 0.35
    for pnl in state.get("daily_pnls", []):
        guard.record_day(pnl)
    log.info(f"[Consistency] {guard.summary()}")

    # ── Flatten failsafe ───────────────────────────────
    if not dry_run:
        failsafe = FlattenFailsafe(client, account_id, symbol)
        failsafe.start()

    # ── Auth ───────────────────────────────────────────
    try:
        client.authenticate()
    except Exception as e:
        log.error(f"Auth failed: {e}")
        return {"status": "auth_failed"}

    # ── Pre-flight ─────────────────────────────────────
    go, checks = pre_flight_check(
        client, account_id, guard,
        expected_win  = tp_pts * n_contracts * MES,
        expected_loss = sl_pts * n_contracts * MES,
    )
    for msg in checks:
        log.info(f"[PreFlight] {msg}")

    if not go:
        log.warning("[PreFlight] ABORT")
        if not dry_run: failsafe.stop()
        return {"status": "preflight_failed"}

    # ── Contract ───────────────────────────────────────
    try:
        contract    = client.find_mes_contract()
        contract_id = contract['id']
        log.info(f"[Contract] {contract.get('name')} id={contract_id}")
    except Exception as e:
        log.error(f"Contract failed: {e}")
        if not dry_run: failsafe.stop()
        return {"status": "contract_failed"}

    # ── Payout eligibility check ───────────────────────
    try:
        bal_info = client.get_account_balance(account_id)
        balance  = bal_info.get('totalEquity',
                   bal_info.get('balance', 0))
        pay_ok, pay_msg = check_payout_eligibility(state, balance,
                                                    min_payout_balance)
        if pay_ok:
            log.info(f"[Payout] *** ELIGIBLE *** {pay_msg}")
            log.info("[Payout] Request payout at topstep.com/dashboard")
        else:
            log.info(f"[Payout] Not yet: {pay_msg}")
    except Exception as e:
        log.warning(f"[Payout] Balance check failed: {e}")
        balance = 50_000

    # ── Wait for momentum signal ───────────────────────
    direction, entry_price = wait_for_momentum_signal(
        client, contract_id,
        entry_time, scan_until,
        dry_run=dry_run
    )

    if direction == 0:
        log.info("[C2] No signal today")
        if not dry_run: failsafe.stop()
        state["daily_pnls"].append(0.0)
        save_state(state)
        return {"status": "no_signal"}

    # ── Bracket prices ─────────────────────────────────
    def round_tick(p): return round(round(p/0.25)*0.25, 2)
    action   = "Buy"  if direction == 1 else "Sell"
    tp_price = round_tick(entry_price + direction * tp_pts)
    sl_price = round_tick(entry_price - direction * sl_pts)

    log.info(f"[Order] {action} {n_contracts}x MES "
             f"| TP={tp_price:.2f} SL={sl_price:.2f}")

    if dry_run:
        log.info("[DRY RUN] Would execute bracket")
        return {"status": "dry_run_ok",
                "direction": direction,
                "tp": tp_price, "sl": sl_price}

    # ── Execute bracket ────────────────────────────────
    try:
        entry_side = OrderSide.ASK if direction == 1 else OrderSide.BID
        exit_side  = OrderSide.BID if direction == 1 else OrderSide.ASK

        entry_id = client.place_market_order(
            account_id, contract_id, entry_side, n_contracts)
        log.info(f"[Order] Entry: orderId={entry_id}")
        time.sleep(2)

        tp_id = client.place_limit_order(
            account_id, contract_id, exit_side, n_contracts, tp_price)
        sl_id = client.place_stop_order(
            account_id, contract_id, exit_side, n_contracts, sl_price)
        log.info(f"[Order] TP={tp_id} SL={sl_id}")

    except Exception as e:
        log.error(f"[Order] Failed: {e}")
        try:
            client.flatten_position(account_id, contract.get('name',''))
        except: pass
        failsafe.stop()
        return {"status": "order_failed"}

    # ── Monitor bracket ────────────────────────────────
    monitor = BracketMonitor(client, account_id, poll_interval=5)
    monitor.register(tp_id, sl_id, entry_id)
    monitor.start()

    while True:
        now = datetime.now(CT)
        if now >= flatten_at:
            log.warning("[Runner] Flatten time reached")
            try:
                client.cancel_order(tp_id)
                client.cancel_order(sl_id)
                client.flatten_position(account_id, contract.get('name',''))
            except: pass
            exit_reason = "flatten"
            break
        if monitor.all_done():
            exit_reason = monitor.last_exit() or "done"
            log.info(f"[Runner] Closed: {exit_reason}")
            break
        time.sleep(15)

    monitor.stop()

    # ── Record PnL ─────────────────────────────────────
    if exit_reason == "tp_filled":
        daily_pnl = tp_pts * n_contracts * MES
    elif exit_reason == "sl_filled":
        daily_pnl = -sl_pts * n_contracts * MES
    else:
        daily_pnl = 0.0

    log.info(f"[EOD] Exit={exit_reason}  PnL=${daily_pnl:+.2f}")

    guard.record_day(daily_pnl)
    state["daily_pnls"].append(daily_pnl)

    # Track winning days ($150+)
    if daily_pnl >= 150:
        state["winning_days"] = state.get("winning_days", 0) + 1
        log.info(f"[EOD] Winning day! "
                 f"Total: {state['winning_days']}/5")

    save_state(state)
    log.info(f"[Consistency] {guard.summary()}")

    if not dry_run:
        failsafe.stop()

    return {
        "status":       "ok",
        "exit":         exit_reason,
        "daily_pnl":    daily_pnl,
        "winning_days": state["winning_days"],
        "consistency":  guard.summary(),
    }


# ── CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glitch XFA Runner")
    parser.add_argument("--account",   type=int, required=True)
    parser.add_argument("--env",       default="demo",
                        choices=["demo","live"])
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--contracts", type=int,   default=5)
    parser.add_argument("--tp",        type=float, default=12.0)
    parser.add_argument("--sl",        type=float, default=3.0)
    args = parser.parse_args()

    try:
        creds = ProjectXCredentials.from_file(".projectx_creds.json")
    except FileNotFoundError:
        print("Missing .projectx_creds.json")
        print('Create: {"user_name": "email", "api_key": "key"}')
        sys.exit(1)

    result = run_xfa_day(
        credentials = creds,
        account_id  = args.account,
        dry_run     = args.dry_run,
        n_contracts = args.contracts,
        tp_pts      = args.tp,
        sl_pts      = args.sl,
    )
    log.info(f"Day complete: {result}")
