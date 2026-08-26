"""
Glitch — Topstep Combine Account State Machine
===============================================
Implements the EXACT Topstep 2026 rule mechanics verified from source.

KEY MECHANIC — EOD TRAILING MLL:
  - floor only moves UP at end_of_day() call
  - floor never moves down
  - floor locks at account_size once it reaches it
  - breach check runs at EOD after floor update
  - intraday: only DLL can pause the session (soft, not fatal)

CONSISTENCY RULE:
  - best_day / cumulative_profit < 0.50
  - gates the PASS state — does not blow the account
  - we track it continuously so the optimizer can penalize it

PASS CONDITIONS:
  - cumulative_profit >= profit_target
  - consistency rule satisfied
  - (no minimum day count in 2026 Combine — verified)

BLOWN CONDITIONS (hard, permanent):
  - EOD balance <= MLL floor  →  BLOWN_MLL
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import numpy as np

from core.prop_firm import TopstepCombineSpec, TOPSTEP_50K


class CombineStatus(Enum):
    ACTIVE        = "active"
    PASSED        = "passed"          # Hit profit target + consistency OK
    BLOWN_MLL     = "blown_mll"       # EOD balance hit/below floor (hard, permanent)
    DLL_PAUSED    = "dll_paused"      # Hit daily loss limit (soft — resets next day)
    CONSISTENCY_GATED = "consistency_gated"  # Profit target hit but 50% rule violated


@dataclass
class DayRecord:
    day_number: int
    pnl: float
    eod_balance: float
    mll_floor_after: float
    status_after: str


@dataclass
class TopstepCombineAccount:
    """
    Full state machine for one Topstep Trading Combine attempt.

    Usage pattern:
        acct = TopstepCombineAccount(spec)
        for each_day:
            acct.start_day()
            for each_trade:
                acct.record_trade_pnl(pnl, unrealized_high=peak_intraday)
                if not acct.is_session_active: break
            acct.end_of_day()
            if not acct.is_alive: break
    """
    spec: TopstepCombineSpec = field(default_factory=lambda: TOPSTEP_50K)

    # ── Internal state (post_init) ─────────────────────────────────────────
    balance: float          = field(init=False)
    mll_floor: float        = field(init=False)   # trailing floor, EOD-only
    status: CombineStatus   = field(init=False)
    day_number: int         = field(default=0, init=False)
    day_pnl: float          = field(default=0.0, init=False)
    day_paused: bool        = field(default=False, init=False)  # DLL hit this session
    cumulative_profit: float = field(default=0.0, init=False)
    best_day_profit: float  = field(default=0.0, init=False)
    day_log: List[DayRecord] = field(default_factory=list, init=False)
    months_elapsed: float   = field(default=0.0, init=False)

    def __post_init__(self):
        self.balance   = self.spec.account_size
        self.mll_floor = self.spec.starting_floor
        self.status    = CombineStatus.ACTIVE

    # ── Session control ────────────────────────────────────────────────────

    def start_day(self):
        """Call once at the start of each trading session."""
        self.day_number += 1
        self.day_pnl    = 0.0
        self.day_paused = False

    def record_trade_pnl(self, realized_pnl: float) -> bool:
        """
        Apply a closed trade's realized PnL.
        Returns True if session still active, False if DLL hit.

        Note: intraday MLL checks are NOT done here — Topstep Combine
        uses EOD trailing. Only the DLL can pause intraday.
        """
        if not self.is_session_active:
            return False

        self.balance  += realized_pnl
        self.day_pnl  += realized_pnl

        # DLL check (soft — pauses session, not fatal)
        if self.day_pnl <= -self.spec.daily_loss_limit:
            self.day_paused = True
            self.status = CombineStatus.DLL_PAUSED
            return False

        return True

    def end_of_day(self):
        """
        Call at session close (3:10 PM CT).
        This is the ONLY moment the MLL floor can move.
        Permanent blow check happens here.
        """
        # 1. Update trailing floor (only moves UP)
        new_floor = self.balance - self.spec.mll_distance
        if new_floor > self.mll_floor:
            self.mll_floor = min(new_floor, self.spec.floor_lock_level)

        # 2. Hard blow check: EOD balance below floor
        if self.balance <= self.mll_floor:
            self.status = CombineStatus.BLOWN_MLL
            self._log_day()
            return

        # 3. Update cycle profit tracking (even when gated — keep accumulating)
        if self.day_pnl > 0:
            self.cumulative_profit += self.day_pnl
            self.best_day_profit    = max(self.best_day_profit, self.day_pnl)

        # 4. Reset DLL pause / consistency gate for re-evaluation next day
        if self.status in (CombineStatus.DLL_PAUSED, CombineStatus.CONSISTENCY_GATED):
            self.status = CombineStatus.ACTIVE

        # 5. Pass check
        self._check_pass()
        self._log_day()

    # ── Pass logic ─────────────────────────────────────────────────────────

    def _check_pass(self):
        """Profit target + consistency must both be satisfied."""
        if self.cumulative_profit < self.spec.profit_target:
            return
        # Profit target reached — check consistency
        if self._consistency_violated():
            self.status = CombineStatus.CONSISTENCY_GATED
        else:
            self.status = CombineStatus.PASSED

    def _consistency_violated(self) -> bool:
        if self.cumulative_profit <= 0:
            return False
        return (self.best_day_profit / self.cumulative_profit) >= self.spec.consistency_cap_pct

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        return self.status not in (CombineStatus.BLOWN_MLL,)

    @property
    def is_session_active(self) -> bool:
        # CONSISTENCY_GATED = still trading, just can't PASS yet
        tradeable = self.status in (CombineStatus.ACTIVE, CombineStatus.CONSISTENCY_GATED)
        return tradeable and not self.day_paused

    @property
    def mll_buffer(self) -> float:
        """USD distance between current balance and MLL floor."""
        return self.balance - self.mll_floor

    @property
    def profit_progress(self) -> float:
        """0.0 → 1.0+ progress toward profit target."""
        return self.cumulative_profit / self.spec.profit_target

    @property
    def consistency_ratio(self) -> float:
        """best_day / cumulative_profit. Must stay < 0.50 to pass."""
        if self.cumulative_profit <= 0:
            return 0.0
        return self.best_day_profit / self.cumulative_profit

    @property
    def running_pnl(self) -> float:
        return self.balance - self.spec.account_size

    @property
    def mll_floor_locked(self) -> bool:
        return self.mll_floor >= self.spec.floor_lock_level

    def _log_day(self):
        self.day_log.append(DayRecord(
            day_number=self.day_number,
            pnl=self.day_pnl,
            eod_balance=self.balance,
            mll_floor_after=self.mll_floor,
            status_after=self.status.value,
        ))

    def summary(self) -> dict:
        return {
            "status":            self.status.value,
            "day":               self.day_number,
            "balance":           round(self.balance, 2),
            "mll_floor":         round(self.mll_floor, 2),
            "mll_buffer":        round(self.mll_buffer, 2),
            "mll_locked":        self.mll_floor_locked,
            "cumulative_profit": round(self.cumulative_profit, 2),
            "best_day":          round(self.best_day_profit, 2),
            "consistency_ratio": round(self.consistency_ratio, 3),
            "profit_progress":   round(self.profit_progress * 100, 1),
        }
