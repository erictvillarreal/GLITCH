"""
Glitch — Topstep Combine Monte Carlo Simulator
================================================
Vectorised simulation of N independent Combine attempts under a
given daily-return distribution.

SIMULATION MODEL
----------------
We simulate at the DAY level (not trade level) because:
  1. The MLL is EOD-based — what matters is the closing balance each day
  2. The consistency rule is per-day
  3. It's 100x faster than tick-level simulation

Each day's P&L is drawn from a distribution parameterized by:
  - win_rate     : P(day is profitable)
  - avg_win_usd  : mean winning day P&L
  - avg_loss_usd : mean losing day magnitude
  - win_std_usd  : std dev of winning days
  - loss_std_usd : std dev of losing days

These parameters are either:
  (a) assumed (for grid search / theoretical analysis)
  (b) estimated from backtest data (for real strategy validation)

TRIPLE-BARRIER LABELING (for strategy validation):
  Each trade/day gets a label based on which barrier is hit first:
    +1  : upper barrier (take profit)
    -1  : lower barrier (stop loss)
     0  : time barrier (max holding period)
  This is the de Prado (2018) method for financial ML labeling.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import numpy as np
from scipy import stats

from core.prop_firm import TopstepCombineSpec, TOPSTEP_50K, get_spec


# ── Strategy distribution parameters ──────────────────────────────────────

@dataclass
class DailyReturnDist:
    """
    Statistical distribution of daily P&L for a strategy.
    All USD values relative to a given account size.

    Can be constructed from:
      - Assumed parameters (theoretical analysis)
      - Backtest trade log (empirical)
    """
    win_rate: float           # P(day net positive), e.g. 0.60
    avg_win:  float           # Mean winning day, USD, e.g. 250
    avg_loss: float           # Mean losing day (positive number), e.g. 180
    win_std:  float = 0.0     # Std dev of winning days
    loss_std: float = 0.0     # Std dev of losing days
    name: str = "strategy"

    @classmethod
    def from_trade_log(cls, daily_pnls: np.ndarray, name: str = "backtest") -> "DailyReturnDist":
        """Fit distribution parameters from a backtest daily P&L series."""
        wins  = daily_pnls[daily_pnls > 0]
        losses = -daily_pnls[daily_pnls < 0]   # positive magnitudes
        n = len(daily_pnls)
        return cls(
            win_rate = len(wins) / n if n > 0 else 0.0,
            avg_win  = float(wins.mean())   if len(wins) > 0 else 0.0,
            avg_loss = float(losses.mean()) if len(losses) > 0 else 0.0,
            win_std  = float(wins.std())    if len(wins) > 1 else 0.0,
            loss_std = float(losses.std())  if len(losses) > 1 else 0.0,
            name=name,
        )

    @property
    def expected_daily_pnl(self) -> float:
        return self.win_rate * self.avg_win - (1 - self.win_rate) * self.avg_loss

    @property
    def daily_std(self) -> float:
        ev = self.expected_daily_pnl
        var = (self.win_rate * (self.avg_win - ev)**2 +
               (1 - self.win_rate) * (-self.avg_loss - ev)**2)
        return float(np.sqrt(var))

    @property
    def edge_ratio(self) -> float:
        """avg_win / avg_loss — the daily RR."""
        return self.avg_win / self.avg_loss if self.avg_loss > 0 else float("inf")

    def describe(self) -> str:
        return (f"[{self.name}] WR={self.win_rate:.0%}  "
                f"avg_win=${self.avg_win:.0f}  avg_loss=${self.avg_loss:.0f}  "
                f"RR={self.edge_ratio:.2f}  EV/day=${self.expected_daily_pnl:+.1f}")

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Draw n daily PnL values from this distribution."""
        is_win = rng.random(n) < self.win_rate
        if self.win_std > 0:
            wins = rng.normal(self.avg_win, self.win_std, n).clip(0)
        else:
            wins = np.full(n, self.avg_win)
        if self.loss_std > 0:
            losses = -rng.normal(self.avg_loss, self.loss_std, n).clip(0)
        else:
            losses = np.full(n, -self.avg_loss)
        return np.where(is_win, wins, losses)


# ── Simulation results ─────────────────────────────────────────────────────

@dataclass
class SimResult:
    spec: TopstepCombineSpec
    dist: DailyReturnDist
    n_paths: int

    n_passed:     int = 0
    n_blown:      int = 0
    n_cons_gated: int = 0   # Hit profit but stuck on consistency
    n_alive:      int = 0   # Still running at max_days

    pass_days:    Optional[np.ndarray] = None   # Days to pass (passed paths only)
    final_balances: Optional[np.ndarray] = None

    @property
    def pass_rate(self) -> float:
        return self.n_passed / self.n_paths

    @property
    def blow_rate(self) -> float:
        return self.n_blown / self.n_paths

    @property
    def consistency_gate_rate(self) -> float:
        return self.n_cons_gated / self.n_paths

    def wilson_ci(self, alpha: float = 0.05) -> Tuple[float, float]:
        n, k = self.n_paths, self.n_passed
        z = stats.norm.ppf(1 - alpha / 2)
        p = k / n
        d = 1 + z**2 / n
        c = (p + z**2 / (2*n)) / d
        h = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
        return max(0.0, c - h), min(1.0, c + h)

    @property
    def avg_pass_days(self) -> Optional[float]:
        if self.pass_days is not None and len(self.pass_days) > 0:
            return float(np.mean(self.pass_days))
        return None

    @property
    def system_ev(self) -> float:
        """
        Net EV per attempt in USD.
        Simplified: we count months as ceiling(avg_pass_days / 21).
        """
        if self.pass_rate == 0:
            return -self.spec.monthly_fee
        avg_days = self.avg_pass_days or 15
        months = max(1, int(np.ceil(avg_days / 21)))
        cost = self.spec.monthly_fee * months + self.spec.activation_fee
        # Rough payout estimate: XFA earns roughly 2× profit target at 90%
        est_payout = self.spec.profit_target * 2 * 0.90
        return self.pass_rate * est_payout - cost

    def print_summary(self):
        ci_lo, ci_hi = self.wilson_ci()
        lines = [
            "=" * 58,
            f"  GLITCH Monte Carlo — Topstep {self.spec.label} Combine",
            f"  Strategy : {self.dist.describe()}",
            f"  Paths    : {self.n_paths:,}",
            "-" * 58,
            f"  PASS rate    : {self.pass_rate:.1%}  (95% CI: {ci_lo:.1%}–{ci_hi:.1%})",
            f"  BLOW rate    : {self.blow_rate:.1%}",
            f"  Cons. gated  : {self.consistency_gate_rate:.1%}",
            f"  Avg days/pass: {self.avg_pass_days:.1f}" if self.avg_pass_days else "  Avg days/pass: n/a",
            f"  System EV    : ${self.system_ev:+,.0f} per attempt",
            f"  Monthly cost : ${self.spec.monthly_fee:.0f} + ${self.spec.activation_fee:.0f} activation",
            "=" * 58,
        ]
        print("\n".join(lines))


# ── Core simulator ─────────────────────────────────────────────────────────

class TopstepMonteCarloSimulator:
    """
    Vectorised EOD-level simulation of Topstep Combine attempts.

    The MLL floor updates ONLY at end_of_day.
    Consistency ratio is tracked per path.
    All arrays are (n_paths,) shaped — no Python loops over paths.
    """

    def __init__(
        self,
        dist: DailyReturnDist,
        spec: TopstepCombineSpec = TOPSTEP_50K,
        n_paths: int = 20_000,
        max_days: int = 120,         # ~6 months of trading days
        seed: Optional[int] = 42,
    ):
        self.dist     = dist
        self.spec     = spec
        self.n_paths  = n_paths
        self.max_days = max_days
        self.rng      = np.random.default_rng(seed)

    def run(self) -> SimResult:
        s = self.spec
        N = self.n_paths

        # State vectors
        balance    = np.full(N, s.account_size, dtype=np.float64)
        mll_floor  = np.full(N, s.starting_floor, dtype=np.float64)
        cum_profit = np.zeros(N, dtype=np.float64)
        best_day   = np.zeros(N, dtype=np.float64)
        alive      = np.ones(N, dtype=bool)
        passed     = np.zeros(N, dtype=bool)
        blown      = np.zeros(N, dtype=bool)
        cons_gated = np.zeros(N, dtype=bool)
        pass_day   = np.full(N, -1, dtype=np.int32)

        for day in range(1, self.max_days + 1):
            if not alive.any():
                break

            # Sample daily PnL for all alive paths
            day_pnl = np.where(alive, self.dist.sample(N, self.rng), 0.0)

            # DLL check: if day_pnl < -DLL, clip to -DLL (paused session)
            # This is a soft cap — balance still takes the loss, but limited
            day_pnl = np.where(
                alive & (day_pnl < -s.daily_loss_limit),
                -s.daily_loss_limit,
                day_pnl
            )

            # Update balance
            balance += day_pnl

            # ── EOD floor update (ONLY positive EOD profits ratchet the floor) ──
            new_floor = balance - s.mll_distance
            # Floor only moves UP, and only when new_floor > current floor
            ratchet = alive & (new_floor > mll_floor)
            mll_floor = np.where(ratchet, np.minimum(new_floor, s.floor_lock_level), mll_floor)

            # ── Hard blow check ──
            just_blown = alive & (balance <= mll_floor)
            blown |= just_blown
            alive &= ~just_blown

            # ── Cumulative profit + best day (only profitable days count) ──
            profitable = alive & (day_pnl > 0)
            cum_profit = np.where(profitable, cum_profit + day_pnl, cum_profit)
            best_day   = np.where(profitable & (day_pnl > best_day), day_pnl, best_day)

            # ── Pass check ──
            target_hit = alive & (cum_profit >= s.profit_target)
            # Consistency: best_day < 50% of cum_profit
            cons_ok    = best_day < (s.consistency_cap_pct * cum_profit)
            just_passed = target_hit & cons_ok
            just_gated  = target_hit & ~cons_ok & ~passed

            passed     |= just_passed
            cons_gated |= just_gated & ~passed
            pass_day    = np.where(just_passed & (pass_day < 0), day, pass_day)
            alive      &= ~just_passed  # passed paths stop simulating

        result = SimResult(
            spec=self.spec,
            dist=self.dist,
            n_paths=N,
            n_passed=int(passed.sum()),
            n_blown=int(blown.sum()),
            n_cons_gated=int(cons_gated.sum() - passed.sum() * 0),  # only still-gated
            n_alive=int(alive.sum()),
            pass_days=pass_day[pass_day > 0],
            final_balances=balance,
        )
        # Correct cons_gated count: paths gated but never passed
        result.n_cons_gated = int((cons_gated & ~passed).sum())
        return result
