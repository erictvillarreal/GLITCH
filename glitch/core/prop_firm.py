"""
Glitch — Topstep $50K Combine Rules Engine (2026, verified April 2026)
======================================================================
Single source of truth for every hard rule and soft objective.

VERIFIED RULES (source: tradecovex.com/guides/topstep-combine-rules-2026,
                        proptradingvibes.com/blog/topstep-rules-overview,
                        topstep help center, April 2026):

HARD RULE (account-ender):
  - MLL breach: live equity drops below the trailing floor at EOD.
    Floor updates ONLY at end-of-day close (not intraday).
    Floor never moves down. Locks at starting_balance once it reaches it.

OBJECTIVES (soft — do not close account alone, but block passing):
  - Profit target: $3,000 net for $50K
  - Daily Loss Limit: $1,000 (pauses trading for session, NOT fatal)
  - Consistency: best single day < 50% of cumulative cycle profit
  - Max position size: 5 mini contracts OR 50 micro contracts

COST STRUCTURE:
  - Standard path: $49/month + $149 activation on pass
  - No-Activation-Fee path: higher monthly, no activation

INSTRUMENTS: CME futures only. ES, MES, NQ, MNQ, RTY, M2K, CL, GC, 6E…
HOURS: 5:00 PM CT to 3:10 PM CT next day. Flat by 3:10 PM CT daily.
NO overnight positions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import yaml, os


@dataclass(frozen=True)
class TopstepCombineSpec:
    """
    Immutable specification for one Topstep Combine account size.
    All dollar values are USD.
    """
    # Account identity
    label: str                      # e.g. "50K"
    account_size: float             # 50_000 / 100_000 / 150_000

    # Hard rule
    mll_distance: float             # Distance floor trails below peak EOD balance
                                    # $2,000 / $3,000 / $4,500

    # Objectives
    profit_target: float            # $3,000 / $6,000 / $9,000
    daily_loss_limit: float         # $1,000 / $2,000 / $3,000 (soft — pauses day)
    consistency_cap_pct: float      # 0.50 — best day must be < 50% of cycle profit

    # Position limits (TopstepX ratio: 1 mini = 10 micros)
    max_mini_contracts: int         # 5 / 10 / 15
    max_micro_contracts: int        # 50 / 100 / 150

    # Cost
    monthly_fee: float              # $49 / $99 / $149 (Standard path)
    activation_fee: float           # $149 (Standard path, paid on pass)

    # Session rules
    session_close_ct: str = "15:10"  # Hard flat time, Central Time
    session_open_ct:  str = "17:00"  # Previous calendar day

    # Derived
    @property
    def starting_floor(self) -> float:
        """Initial MLL floor = account_size - mll_distance."""
        return self.account_size - self.mll_distance

    @property
    def floor_lock_level(self) -> float:
        """MLL freezes when floor reaches starting balance."""
        return self.account_size

    @property
    def consistency_max_day_usd(self) -> float:
        """Hard cap: single day profit that triggers consistency violation."""
        return self.profit_target * self.consistency_cap_pct

    @property
    def total_entry_cost(self) -> float:
        return self.monthly_fee + self.activation_fee


# ── Canonical specs (verified April 2026) ─────────────────────────────────

TOPSTEP_50K = TopstepCombineSpec(
    label="50K",
    account_size=50_000,
    mll_distance=2_000,
    profit_target=3_000,
    daily_loss_limit=1_000,
    consistency_cap_pct=0.50,
    max_mini_contracts=5,
    max_micro_contracts=50,
    monthly_fee=49.0,
    activation_fee=149.0,
)

TOPSTEP_100K = TopstepCombineSpec(
    label="100K",
    account_size=100_000,
    mll_distance=3_000,
    profit_target=6_000,
    daily_loss_limit=2_000,
    consistency_cap_pct=0.50,
    max_mini_contracts=10,
    max_micro_contracts=100,
    monthly_fee=99.0,
    activation_fee=149.0,
)

TOPSTEP_150K = TopstepCombineSpec(
    label="150K",
    account_size=150_000,
    mll_distance=4_500,
    profit_target=9_000,
    daily_loss_limit=3_000,
    consistency_cap_pct=0.50,
    max_mini_contracts=15,
    max_micro_contracts=150,
    monthly_fee=149.0,
    activation_fee=149.0,
)

TOPSTEP_SPECS = {
    "50K":  TOPSTEP_50K,
    "100K": TOPSTEP_100K,
    "150K": TOPSTEP_150K,
}

def get_spec(size: str = "50K") -> TopstepCombineSpec:
    if size not in TOPSTEP_SPECS:
        raise ValueError(f"Unknown size '{size}'. Choose from {list(TOPSTEP_SPECS)}")
    return TOPSTEP_SPECS[size]
