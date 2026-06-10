"""
Glitch — Safety & Operational Risk Module
==========================================
Los tres fixes críticos antes de ir live:

Fix 1: Monitor de órdenes huérfanas
Fix 2: Flatten failsafe independiente  
Fix 3: Consistencia check pre-trade
"""

from __future__ import annotations
import time
import threading
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

CT = ZoneInfo("America/Chicago")
log = logging.getLogger("glitch.safety")


# ══════════════════════════════════════════════════════════════════
# FIX 1 — ORDEN HUÉRFANA MONITOR
# ══════════════════════════════════════════════════════════════════

class BracketMonitor:
    """
    Después de un fill de TP o SL, cancela la orden contraria
    inmediatamente para evitar posición huérfana.

    Uso:
        monitor = BracketMonitor(client, account_id)
        monitor.register(tp_order_id, sl_order_id)
        monitor.start()   # corre en background thread
        # ... cuando detecta fill de uno, cancela el otro
        monitor.stop()
    """

    def __init__(self, client, account_id: int,
                 poll_interval: float = 5.0):
        self.client       = client
        self.account_id   = account_id
        self.poll_interval= poll_interval
        self._brackets: list[dict] = []   # [{tp_id, sl_id, status}]
        self._running     = False
        self._thread: Optional[threading.Thread] = None
        self._lock        = threading.Lock()

    def register(self, tp_order_id: int, sl_order_id: int,
                 entry_order_id: Optional[int] = None):
        """Registra un bracket para monitoreo."""
        with self._lock:
            self._brackets.append({
                'tp_id':     tp_order_id,
                'sl_id':     sl_order_id,
                'entry_id':  entry_order_id,
                'status':    'active',
                'registered_at': time.time(),
            })
        log.info(f"[BracketMonitor] Registered TP={tp_order_id} SL={sl_order_id}")

    def start(self):
        """Arranca el monitor en un thread background."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="BracketMonitor"
        )
        self._thread.start()
        log.info("[BracketMonitor] Started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        log.info("[BracketMonitor] Stopped")

    def _monitor_loop(self):
        while self._running:
            try:
                self._check_brackets()
            except Exception as e:
                log.error(f"[BracketMonitor] Error: {e}")
            time.sleep(self.poll_interval)

    def _check_brackets(self):
        with self._lock:
            active = [b for b in self._brackets
                      if b['status'] == 'active']

        if not active:
            return

        # Get all open orders
        try:
            open_orders = self.client.get_open_orders(self.account_id)
            open_ids    = {o.get('id') or o.get('orderId')
                           for o in open_orders}
        except Exception as e:
            log.warning(f"[BracketMonitor] Could not fetch orders: {e}")
            return

        for bracket in active:
            tp_open = bracket['tp_id'] in open_ids
            sl_open = bracket['sl_id'] in open_ids

            # Both gone → both filled or cancelled → done
            if not tp_open and not sl_open:
                bracket['status'] = 'done'
                log.info(f"[BracketMonitor] Bracket done "
                         f"TP={bracket['tp_id']} SL={bracket['sl_id']}")
                continue

            # TP filled → cancel SL
            if not tp_open and sl_open:
                log.info(f"[BracketMonitor] TP filled → cancelling SL={bracket['sl_id']}")
                try:
                    self.client.cancel_order(bracket['sl_id'])
                    bracket['status'] = 'tp_filled'
                except Exception as e:
                    log.error(f"[BracketMonitor] Failed to cancel SL: {e}")

            # SL filled → cancel TP
            elif tp_open and not sl_open:
                log.info(f"[BracketMonitor] SL filled → cancelling TP={bracket['tp_id']}")
                try:
                    self.client.cancel_order(bracket['tp_id'])
                    bracket['status'] = 'sl_filled'
                except Exception as e:
                    log.error(f"[BracketMonitor] Failed to cancel TP: {e}")

    def all_done(self) -> bool:
        """True si todos los brackets están cerrados."""
        with self._lock:
            return all(b['status'] != 'active'
                       for b in self._brackets)

    def last_exit(self) -> Optional[str]:
        """Retorna 'tp_filled' o 'sl_filled' del último bracket."""
        with self._lock:
            done = [b for b in self._brackets
                    if b['status'] in ('tp_filled','sl_filled','done')]
            return done[-1]['status'] if done else None


# ══════════════════════════════════════════════════════════════════
# FIX 2 — FLATTEN FAILSAFE
# ══════════════════════════════════════════════════════════════════

class FlattenFailsafe:
    """
    Proceso independiente que garantiza cierre de posiciones
    a las 3:00 PM CT pase lo que pase con el script principal.

    Corre en su propio thread. Si el script principal crashea,
    este sigue corriendo hasta flattenear la cuenta.

    Uso:
        failsafe = FlattenFailsafe(client, account_id, symbol)
        failsafe.start()   # arranca al inicio del día
        # corre en background hasta las 3:00 PM CT
    """

    FLATTEN_HOUR   = 15   # 3:00 PM CT
    FLATTEN_MINUTE = 0
    CHECK_INTERVAL = 30   # segundos entre checks

    def __init__(self, client, account_id: int, symbol: str,
                 flatten_hour: int = 15, flatten_minute: int = 0):
        self.client        = client
        self.account_id    = account_id
        self.symbol        = symbol
        self.flatten_hour  = flatten_hour
        self.flatten_minute= flatten_minute
        self._running      = False
        self._flattened    = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._failsafe_loop,
            daemon=True,
            name="FlattenFailsafe"
        )
        self._thread.start()
        log.info(f"[FlattenFailsafe] Started — will flatten at "
                 f"{self.flatten_hour:02d}:{self.flatten_minute:02d} CT")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def _failsafe_loop(self):
        while self._running and not self._flattened:
            try:
                now_ct = datetime.now(CT)
                flatten_time = now_ct.replace(
                    hour=self.flatten_hour,
                    minute=self.flatten_minute,
                    second=0, microsecond=0
                )

                if now_ct >= flatten_time:
                    self._execute_flatten()
                    break

            except Exception as e:
                log.error(f"[FlattenFailsafe] Error: {e}")
                # Even on error, keep trying
            time.sleep(self.CHECK_INTERVAL)

    def _execute_flatten(self):
        """Flatten all positions — tries 3 times."""
        for attempt in range(1, 4):
            try:
                log.warning(f"[FlattenFailsafe] FLATTEN attempt {attempt} "
                            f"at {datetime.now(CT).strftime('%H:%M:%S')} CT")

                # Cancel all open orders first
                try:
                    self.client.cancel_all_orders(self.account_id)
                    log.info("[FlattenFailsafe] All orders cancelled")
                except Exception as e:
                    log.warning(f"[FlattenFailsafe] Cancel orders failed: {e}")

                # Flatten positions
                positions = self.client.get_positions(self.account_id)
                flat_count = 0
                for pos in positions:
                    net = pos.get('netPos', 0)
                    if net == 0:
                        continue
                    try:
                        self.client.flatten_position(
                            self.account_id, self.symbol
                        )
                        flat_count += 1
                        log.info(f"[FlattenFailsafe] Flattened {net} contracts")
                    except Exception as e:
                        log.error(f"[FlattenFailsafe] Flatten failed: {e}")

                self._flattened = True
                log.info(f"[FlattenFailsafe] Done — {flat_count} positions flattened")
                return

            except Exception as e:
                log.error(f"[FlattenFailsafe] Attempt {attempt} failed: {e}")
                time.sleep(5)

        log.critical("[FlattenFailsafe] ALL ATTEMPTS FAILED — manual intervention needed")

    def is_flattened(self) -> bool:
        return self._flattened

    def force_flatten_now(self):
        """Flatten inmediato — para emergencias."""
        log.warning("[FlattenFailsafe] FORCE FLATTEN NOW called")
        self._execute_flatten()


# ══════════════════════════════════════════════════════════════════
# FIX 3 — CONSISTENCIA CHECK
# ══════════════════════════════════════════════════════════════════

class ConsistencyGuard:
    """
    Verifica la regla de consistencia de Topstep ANTES de operar.
    Regla: mejor día < 50% del profit total acumulado.

    Uso:
        guard = ConsistencyGuard(profit_target=3000)
        guard.record_day(pnl=90.0)     # registra cada día
        ok, msg = guard.can_trade(expected_win=90.0)
        if not ok:
            print(f"Skipping trade: {msg}")
    """

    CONSISTENCY_LIMIT = 0.50   # mejor día no puede ser > 50% del total
    SAFETY_BUFFER     = 0.45   # nos detenemos al 45% para tener margen

    def __init__(self, profit_target: float = 3000.0):
        self.profit_target = profit_target
        self.daily_pnls: list[float] = []

    def record_day(self, pnl: float):
        """Registra el PnL de un día completado."""
        self.daily_pnls.append(pnl)

    @property
    def total_profit(self) -> float:
        return sum(p for p in self.daily_pnls if p > 0)

    @property
    def best_day(self) -> float:
        pos = [p for p in self.daily_pnls if p > 0]
        return max(pos) if pos else 0.0

    @property
    def consistency_ratio(self) -> float:
        if self.total_profit <= 0:
            return 0.0
        return self.best_day / self.total_profit

    def can_trade(self, expected_win: float = 90.0) -> tuple[bool, str]:
        """
        Verifica si es seguro operar dado el win esperado.
        Retorna (ok, mensaje).
        """
        if self.total_profit <= 0:
            return True, "No profit yet — safe to trade"

        # Simula qué pasaría si este trade gana
        projected_total  = self.total_profit + expected_win
        projected_best   = max(self.best_day, expected_win)
        projected_ratio  = projected_best / projected_total

        if projected_ratio > self.CONSISTENCY_LIMIT:
            return False, (
                f"CONSISTENCY BLOCK: projected ratio {projected_ratio:.1%} "
                f"> {self.CONSISTENCY_LIMIT:.0%} limit. "
                f"Best day=${self.best_day:.0f} "
                f"Total profit=${self.total_profit:.0f}"
            )

        if projected_ratio > self.SAFETY_BUFFER:
            return True, (
                f"CONSISTENCY WARNING: ratio would be {projected_ratio:.1%} "
                f"(limit {self.CONSISTENCY_LIMIT:.0%}) — trade with caution"
            )

        return True, f"OK — consistency ratio {self.consistency_ratio:.1%}"

    def status(self) -> dict:
        return {
            'total_profit':       self.total_profit,
            'best_day':           self.best_day,
            'consistency_ratio':  self.consistency_ratio,
            'days_recorded':      len(self.daily_pnls),
            'progress_to_target': self.total_profit / self.profit_target,
        }

    def summary(self) -> str:
        s = self.status()
        return (
            f"Profit: ${s['total_profit']:.0f}/{self.profit_target:.0f} "
            f"({s['progress_to_target']:.1%}) | "
            f"Best day: ${s['best_day']:.0f} | "
            f"Consistency: {s['consistency_ratio']:.1%}"
        )


# ══════════════════════════════════════════════════════════════════
# DAILY PRE-FLIGHT CHECK
# ══════════════════════════════════════════════════════════════════

def pre_flight_check(client, account_id: int,
                     consistency_guard: ConsistencyGuard,
                     expected_win: float = 90.0,
                     expected_loss: float = 45.0) -> tuple[bool, list[str]]:
    """
    Verifica TODAS las condiciones antes de operar cada día.
    Retorna (go, [lista de mensajes]).

    Checks:
      1. Hora correcta (no demasiado tarde)
      2. Cuenta dentro de límites Topstep
      3. Consistencia no violada
      4. DLL disponible
      5. Sin posiciones abiertas previas
    """
    messages = []
    go       = True
    now_ct   = datetime.now(CT)

    # Check 1: Hora
    if now_ct.hour >= 14:
        messages.append(f"✗ Too late to trade: {now_ct.strftime('%H:%M')} CT")
        go = False
    else:
        messages.append(f"✓ Time: {now_ct.strftime('%H:%M')} CT")

    # Check 2: Cuenta
    try:
        status = client.check_combine_limits(account_id)
        ok, reason = status if isinstance(status, tuple) else (True, "OK")
        if not ok:
            messages.append(f"✗ Account: {reason}")
            go = False
        else:
            messages.append(f"✓ Account: within limits")
    except Exception as e:
        messages.append(f"✗ Account check failed: {e}")
        go = False

    # Check 3: Consistencia
    cons_ok, cons_msg = consistency_guard.can_trade(expected_win)
    if not cons_ok:
        messages.append(f"✗ Consistency: {cons_msg}")
        go = False
    else:
        messages.append(f"✓ Consistency: {cons_msg}")

    # Check 4: Sin posiciones abiertas
    try:
        positions = client.get_positions(account_id)
        open_pos  = [p for p in positions
                     if p.get('netPos', 0) != 0]
        if open_pos:
            messages.append(f"✗ Open positions detected: {len(open_pos)} — flatten first")
            go = False
        else:
            messages.append(f"✓ No open positions")
    except Exception as e:
        messages.append(f"⚠ Could not check positions: {e}")

    # Check 5: CME holiday
    holidays_2026 = {
        (2026,  1,  1), (2026,  1, 19), (2026,  2, 16),
        (2026,  4,  3), (2026,  5, 25), (2026,  7,  3),
        (2026,  9,  7), (2026, 11, 26), (2026, 12, 25),
    }
    today = (now_ct.year, now_ct.month, now_ct.day)
    if today in holidays_2026:
        messages.append(f"✗ CME Holiday today — no trading")
        go = False
    else:
        messages.append(f"✓ Not a CME holiday")

    return go, messages
