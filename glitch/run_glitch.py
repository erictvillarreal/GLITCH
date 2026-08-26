"""
Glitch — Daily Runner v2 (con safety fixes)
============================================
Cerebro 1: Opening Range Breakout para pasar el Combine

Uso:
  python run_glitch.py --env live --account 12345
  python run_glitch.py --env demo --account 12345 --dry-run
"""

import sys, os, time, argparse, logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '.')

from brokers.projectx import ProjectXClient, ProjectXCredentials, OrderSide
from core.safety import (
    BracketMonitor, FlattenFailsafe,
    ConsistencyGuard, pre_flight_check
)

CT  = ZoneInfo("America/Chicago")
MES = 5.0   # $ per point per contract

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers= [
        logging.StreamHandler(),
        logging.FileHandler("glitch.log"),
    ]
)
log = logging.getLogger("glitch.runner")

# ── State persistence ─────────────────────────────────────────────
STATE_FILE = ".glitch_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"daily_pnls": [], "total_trades": 0}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

# ── ORB signal detection ──────────────────────────────────────────
def wait_for_orb_signal(client, contract_id: str,
                         orb_close_ct, scan_until_ct,
                         dry_run: bool = False):
    """
    Espera el breakout del Opening Range (primeros 5min).
    Retorna (direction, entry_price) o (0, 0.0) si no hay señal.
    direction: +1 long, -1 short, 0 no signal
    """
    if dry_run:
        log.info("[ORB] DRY RUN — simulating long signal at 5000.00")
        return 1, 5000.00

    log.info("[ORB] Waiting for 5min opening range...")

    orb_high = -float('inf')
    orb_low  =  float('inf')
    orb_set  = False

    while True:
        now = datetime.now(CT)

        if now > scan_until_ct:
            log.info("[ORB] Scan window expired — no signal today")
            return 0, 0.0

        try:
            bars = client.get_bars(contract_id, bar_type=1,
                                    bar_size=1, count=10)
            if not bars:
                time.sleep(10)
                continue

            last  = bars[-1]
            price = last.get('close', 0)
            high  = last.get('high', price)
            low   = last.get('low',  price)

            # Build opening range until orb_close
            if not orb_set and now < orb_close_ct:
                orb_high = max(orb_high, high)
                orb_low  = min(orb_low,  low)

            # ORB window closed
            if now >= orb_close_ct and not orb_set:
                orb_set = True
                orb_range = orb_high - orb_low
                log.info(f"[ORB] Range set: H={orb_high:.2f} "
                         f"L={orb_low:.2f} Range={orb_range:.2f}pts")

                # Regime filter: skip if range < 5pts (too tight)
                if orb_range < 5.0:
                    log.info("[ORB] Range too tight — no trade today")
                    return 0, 0.0

            if orb_set:
                if price > orb_high:
                    log.info(f"[ORB] LONG breakout at {price:.2f}")
                    return 1, price
                elif price < orb_low:
                    log.info(f"[ORB] SHORT breakout at {price:.2f}")
                    return -1, price

        except Exception as e:
            log.warning(f"[ORB] Poll error: {e}")

        time.sleep(10)

# ── Main daily runner ─────────────────────────────────────────────
def run_trading_day(
    credentials: ProjectXCredentials,
    account_id:  int,
    dry_run:     bool = False,
    n_contracts: int  = 3,
    tp_pts:      float = 6.0,
    sl_pts:      float = 3.0,
    symbol:      str   = "CON.F.US.EP.M26",
):
    now    = datetime.now(CT)
    state  = load_state()
    client = ProjectXClient(credentials)

    log.info("=" * 55)
    log.info(f"GLITCH — {now.strftime('%Y-%m-%d %A')}")
    log.info(f"Env: {'DRY RUN' if dry_run else 'LIVE'}  "
             f"Account: {account_id}")
    log.info("=" * 55)

    # ── Times ─────────────────────────────────────────
    orb_open   = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    orb_close  = now.replace(hour=9,  minute=35, second=0, microsecond=0)
    scan_until = now.replace(hour=14, minute=30, second=0, microsecond=0)
    flatten_at = now.replace(hour=15, minute=0,  second=0, microsecond=0)

    # ── Safety: ConsistencyGuard ───────────────────────
    guard = ConsistencyGuard(profit_target=3000.0)
    for pnl in state.get("daily_pnls", []):
        guard.record_day(pnl)
    log.info(f"[Consistency] {guard.summary()}")

    # ── Safety: FlattenFailsafe ────────────────────────
    if not dry_run:
        failsafe = FlattenFailsafe(
            client, account_id, symbol,
            flatten_hour=15, flatten_minute=0
        )
        failsafe.start()
        log.info("[Failsafe] Flatten failsafe armed at 3:00 PM CT")

    # ── Authenticate ──────────────────────────────────
    try:
        client.authenticate()
    except Exception as e:
        log.error(f"Auth failed: {e}")
        return {"status": "auth_failed", "error": str(e)}

    # ── Pre-flight check ───────────────────────────────
    go, checks = pre_flight_check(
        client, account_id, guard,
        expected_win  = tp_pts * n_contracts * MES,
        expected_loss = sl_pts * n_contracts * MES,
    )
    for msg in checks:
        log.info(f"[PreFlight] {msg}")

    if not go:
        log.warning("[PreFlight] ABORT — pre-flight failed")
        if not dry_run:
            failsafe.stop()
        return {"status": "preflight_failed", "checks": checks}

    # ── Find contract ──────────────────────────────────
    try:
        contract = client.find_mes_contract()
        contract_id = contract['id']
        log.info(f"[Contract] {contract.get('name')} id={contract_id}")
    except Exception as e:
        log.error(f"Contract lookup failed: {e}")
        if not dry_run:
            failsafe.stop()
        return {"status": "contract_failed"}

    # ── Wait for ORB signal ───────────────────────────
    direction, entry_price = wait_for_orb_signal(
        client, contract_id,
        orb_close, scan_until,
        dry_run=dry_run
    )

    if direction == 0:
        log.info("[ORB] No signal — done for today")
        if not dry_run:
            failsafe.stop()
        state["daily_pnls"].append(0.0)
        save_state(state)
        return {"status": "no_signal"}

    # ── Calculate bracket prices ──────────────────────
    def round_tick(p): return round(round(p / 0.25) * 0.25, 2)
    action   = "Buy" if direction == 1 else "Sell"
    tp_price = round_tick(entry_price + direction * tp_pts)
    sl_price = round_tick(entry_price - direction * sl_pts)

    log.info(f"[Order] {action} {n_contracts}x {contract.get('name')} "
             f"| Entry≈{entry_price:.2f} TP={tp_price:.2f} SL={sl_price:.2f}")

    if dry_run:
        log.info("[DRY RUN] Would place bracket — not executing")
        if not dry_run:
            failsafe.stop()
        return {"status": "dry_run_ok",
                "direction": direction,
                "tp": tp_price, "sl": sl_price}

    # ── Place bracket orders ──────────────────────────
    try:
        entry_side = OrderSide.ASK if direction == 1 else OrderSide.BID
        exit_side  = OrderSide.BID if direction == 1 else OrderSide.ASK

        # Market entry
        entry_id = client.place_market_order(
            account_id, contract_id, entry_side, n_contracts
        )
        log.info(f"[Order] Entry placed: orderId={entry_id}")
        time.sleep(2)   # wait for fill

        # TP limit
        tp_id = client.place_limit_order(
            account_id, contract_id, exit_side,
            n_contracts, tp_price
        )

        # SL stop
        sl_id = client.place_stop_order(
            account_id, contract_id, exit_side,
            n_contracts, sl_price
        )
        log.info(f"[Order] TP={tp_id} SL={sl_id} placed")

    except Exception as e:
        log.error(f"[Order] Failed: {e}")
        log.warning("[Order] Attempting emergency flatten...")
        try:
            client.flatten_position(account_id,
                                     contract.get('name',''))
        except:
            pass
        failsafe.stop()
        return {"status": "order_failed", "error": str(e)}

    # ── Fix 1: BracketMonitor ─────────────────────────
    monitor = BracketMonitor(client, account_id, poll_interval=5)
    monitor.register(tp_id, sl_id, entry_id)
    monitor.start()
    log.info("[Monitor] BracketMonitor running — watching for fills")

    # ── Wait for exit ─────────────────────────────────
    while True:
        now = datetime.now(CT)

        # Flatten time reached
        if now >= flatten_at:
            log.warning("[Runner] Flatten time — closing position")
            try:
                client.cancel_order(tp_id)
                client.cancel_order(sl_id)
                client.flatten_position(account_id, contract.get('name',''))
            except Exception as e:
                log.error(f"[Runner] Flatten failed: {e}")
            exit_reason = "flatten"
            break

        # Bracket filled
        if monitor.all_done():
            exit_reason = monitor.last_exit() or "done"
            log.info(f"[Runner] Position closed: {exit_reason}")
            break

        time.sleep(15)

    monitor.stop()

    # ── Record daily PnL ──────────────────────────────
    if exit_reason == "tp_filled":
        daily_pnl = tp_pts * n_contracts * MES
    elif exit_reason == "sl_filled":
        daily_pnl = -sl_pts * n_contracts * MES
    else:
        daily_pnl = 0.0  # flatten — unknown, use 0

    log.info(f"[EOD] Exit: {exit_reason}  PnL: ${daily_pnl:+.2f}")

    # ── Fix 3: Record for consistency ─────────────────
    guard.record_day(daily_pnl)
    state["daily_pnls"].append(daily_pnl)
    state["total_trades"] = state.get("total_trades", 0) + 1
    save_state(state)
    log.info(f"[Consistency] {guard.summary()}")

    # ── EOD account status ────────────────────────────
    try:
        status = client.check_combine_limits(account_id)
        log.info(f"[Account] {status}")
    except:
        pass

    if not dry_run:
        failsafe.stop()

    return {
        "status":     "ok",
        "exit":       exit_reason,
        "daily_pnl":  daily_pnl,
        "consistency": guard.summary(),
    }


# ── CLI ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glitch Daily Runner")
    parser.add_argument("--account", type=int, required=True)
    parser.add_argument("--env",     default="demo",
                        choices=["demo","live"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--contracts", type=int, default=3)
    parser.add_argument("--tp",  type=float, default=6.0)
    parser.add_argument("--sl",  type=float, default=3.0)
    args = parser.parse_args()

    try:
        creds = ProjectXCredentials.from_file(".projectx_creds.json")
    except FileNotFoundError:
        print("Missing .projectx_creds.json")
        print('Create it: {"user_name": "email", "api_key": "key"}')
        sys.exit(1)

    result = run_trading_day(
        credentials = creds,
        account_id  = args.account,
        dry_run     = args.dry_run,
        n_contracts = args.contracts,
        tp_pts      = args.tp,
        sl_pts      = args.sl,
    )
    log.info(f"Day complete: {result}")
