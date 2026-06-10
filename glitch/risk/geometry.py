"""
Glitch — Risk Geometry Module
================================
Position sizing, Kelly criterion, drawdown analytics, and
risk budget management.

The central insight: in prop firm trading, the "edge" isn't just
the strategy's EV — it's the geometric structure of the position
sizing relative to the firm's constraint boundaries.

Usage
-----
>>> from risk.geometry import RiskGeometry
>>> rg = RiskGeometry(account_size=100_000, max_daily_loss_pct=0.05, max_total_loss_pct=0.10)
>>> rg.kelly_position_size(win_rate=0.55, rr=1.5)
>>> rg.max_position_for_drawdown_budget(remaining_budget_pct=0.06, rr=1.5)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class RiskGeometry:
    """
    Computes optimal position sizing given account constraints and strategy params.
    
    Key principle: never risk more than what keeps us alive to see the next trade.
    The optimal risk per trade is the MINIMUM of:
      1. Kelly criterion (maximise geometric growth)
      2. Daily loss budget fraction
      3. Total drawdown budget fraction
    """
    account_size: float
    max_daily_loss_pct: float
    max_total_loss_pct: float
    safety_factor: float = 0.5  # Fraction of Kelly to use (half-Kelly is standard)

    @property
    def max_daily_loss(self) -> float:
        return self.account_size * self.max_daily_loss_pct

    @property
    def max_total_loss(self) -> float:
        return self.account_size * self.max_total_loss_pct

    # ------------------------------------------------------------------
    # Kelly Criterion
    # ------------------------------------------------------------------

    def kelly_fraction(self, win_rate: float, rr: float) -> float:
        """
        Full Kelly fraction of account to risk per trade.
        f* = (p * (RR+1) - 1) / RR
        
        Returns 0 if the strategy has negative EV (Kelly says don't trade).
        """
        f = (win_rate * (rr + 1) - 1) / rr
        return max(0.0, f)

    def half_kelly_fraction(self, win_rate: float, rr: float) -> float:
        """Half-Kelly: more conservative, preferred in practice."""
        return self.kelly_fraction(win_rate, rr) * self.safety_factor

    def kelly_position_size(self, win_rate: float, rr: float, use_half: bool = True) -> float:
        """Dollar amount to risk per trade under Kelly."""
        f = self.half_kelly_fraction(win_rate, rr) if use_half else self.kelly_fraction(win_rate, rr)
        return self.account_size * f

    # ------------------------------------------------------------------
    # Constraint-aware sizing
    # ------------------------------------------------------------------

    def max_risk_given_daily_budget(
        self,
        trades_remaining_today: int,
        daily_pnl_so_far: float = 0.0,
    ) -> float:
        """
        Max risk per trade given remaining daily loss budget.
        Distributes the remaining budget evenly across expected remaining trades.
        """
        remaining_budget = self.max_daily_loss + daily_pnl_so_far  # daily_pnl negative if losing
        remaining_budget = max(0.0, remaining_budget)
        if trades_remaining_today <= 0:
            return 0.0
        return remaining_budget / trades_remaining_today

    def max_risk_given_total_budget(
        self,
        current_equity: float,
        trades_remaining_session: int = 10,
    ) -> float:
        """
        Max risk per trade given remaining total drawdown budget.
        """
        drawdown_used = self.account_size - current_equity
        remaining = self.max_total_loss - drawdown_used
        remaining = max(0.0, remaining)
        if trades_remaining_session <= 0:
            return 0.0
        return remaining / trades_remaining_session

    def optimal_risk_per_trade(
        self,
        win_rate: float,
        rr: float,
        current_equity: float,
        daily_pnl: float = 0.0,
        trades_today_remaining: int = 3,
        trades_session_remaining: int = 10,
        use_kelly: bool = True,
    ) -> float:
        """
        Conservative optimal: minimum of Kelly, daily budget, total budget.
        This is the amount to RISK (not the position notional).
        """
        constraints = []

        if use_kelly:
            kelly_risk = self.kelly_position_size(win_rate, rr)
            constraints.append(kelly_risk)

        daily_budget_risk = self.max_risk_given_daily_budget(
            trades_today_remaining, daily_pnl
        )
        total_budget_risk = self.max_risk_given_total_budget(
            current_equity, trades_session_remaining
        )
        constraints.extend([daily_budget_risk, total_budget_risk])

        # Filter out zeros (shouldn't trade if any budget is 0)
        valid = [c for c in constraints if c > 0]
        if not valid:
            return 0.0
        return min(valid)

    # ------------------------------------------------------------------
    # Drawdown analytics
    # ------------------------------------------------------------------

    def max_consecutive_losses_before_breach(
        self,
        risk_per_trade_pct: float,
        use_daily: bool = True,
    ) -> int:
        """
        How many consecutive losses can we absorb before breaching a limit?
        """
        if use_daily:
            limit = self.max_daily_loss
        else:
            limit = self.max_total_loss
        risk_per_trade = self.account_size * risk_per_trade_pct
        if risk_per_trade <= 0:
            return float("inf")
        return int(limit // risk_per_trade)

    def ruin_probability_analytic(
        self,
        win_rate: float,
        rr: float,
        risk_per_trade_pct: float,
        target_pct: float,
        ruin_pct: float,
    ) -> float:
        """
        Gambler's ruin approximation for probability of hitting ruin
        before target.  Assumes fixed-fractional betting.
        
        R = ((q/p)^(target/risk) - 1) / ((q/p)^((target+ruin)/risk) - 1)
        
        Where p = probability-weighted gain per unit, q = loss per unit.
        """
        p = win_rate * rr  # Expected win in risk units
        q = 1 - win_rate   # Expected loss in risk units

        if abs(p - q) < 1e-10:
            # Symmetric random walk
            return ruin_pct / (target_pct + ruin_pct)

        ratio = q / p
        n_target = int(target_pct / risk_per_trade_pct)
        n_ruin = int(ruin_pct / risk_per_trade_pct)

        try:
            num = ratio**n_target - 1
            den = ratio**(n_target + n_ruin) - 1
            return num / den if den != 0 else 0.5
        except (OverflowError, ZeroDivisionError):
            return 0.0 if p > q else 1.0

    # ------------------------------------------------------------------
    # Expected value calculations
    # ------------------------------------------------------------------

    def ev_per_trade_usd(self, win_rate: float, rr: float, risk_usd: float) -> float:
        return win_rate * (risk_usd * rr) - (1 - win_rate) * risk_usd

    def expected_trades_to_target(
        self,
        win_rate: float,
        rr: float,
        risk_per_trade_pct: float,
        target_pct: float,
    ) -> float:
        """Expected number of trades to reach profit target (EV-based estimate)."""
        ev_pct = win_rate * rr * risk_per_trade_pct - (1 - win_rate) * risk_per_trade_pct
        if ev_pct <= 0:
            return float("inf")
        return target_pct / ev_pct

    def variance_per_trade(
        self, win_rate: float, rr: float, risk_per_trade_pct: float
    ) -> float:
        """Variance of PnL per trade as fraction of account^2."""
        ev = self.ev_per_trade_usd(win_rate, rr, self.account_size * risk_per_trade_pct)
        avg_win = self.account_size * risk_per_trade_pct * rr
        avg_loss = self.account_size * risk_per_trade_pct
        return win_rate * (avg_win - ev)**2 + (1 - win_rate) * (-avg_loss - ev)**2

    def sharpe_ratio_estimate(
        self,
        win_rate: float,
        rr: float,
        risk_per_trade_pct: float,
        trades_per_day: float = 3.0,
        trading_days: float = 252,
    ) -> float:
        """
        Annualised Sharpe ratio estimate from trade distribution parameters.
        """
        ev = self.ev_per_trade_usd(win_rate, rr, self.account_size * risk_per_trade_pct)
        var = self.variance_per_trade(win_rate, rr, risk_per_trade_pct)
        std = np.sqrt(var)
        if std == 0:
            return float("inf") if ev > 0 else 0.0
        trades_per_year = trades_per_day * trading_days
        annual_ev = ev * trades_per_year
        annual_std = std * np.sqrt(trades_per_year)
        return annual_ev / annual_std


@dataclass
class ConvexPayoffAnalysis:
    """
    Analyses the option-like convex payoff structure of a prop firm attempt.
    
    Maps the challenge to a call option:
    - Premium paid = challenge_fee + activation_fee
    - Strike = required profit target  
    - Upside = funded account payout potential
    """
    challenge_fee: float
    activation_fee: float
    account_size: float
    profit_target_pct: float
    profit_split_pct: float
    funded_avg_return_pct: float = 0.05  # Expected monthly return when funded

    @property
    def total_premium(self) -> float:
        return self.challenge_fee + self.activation_fee

    @property
    def max_upside_monthly(self) -> float:
        """Max monthly payout from funded account."""
        return self.account_size * self.funded_avg_return_pct * self.profit_split_pct

    def breakeven_pass_rate(self, expected_months_funded: float = 6.0) -> float:
        """
        Minimum pass rate for positive EV.
        P(pass) > premium / (expected_payout_per_funded_account)
        """
        expected_payout = self.max_upside_monthly * expected_months_funded
        if expected_payout <= 0:
            return 1.0
        return self.total_premium / expected_payout

    def net_ev(self, pass_rate: float, expected_months_funded: float = 6.0) -> float:
        """Net expected value per attempt."""
        expected_payout = self.max_upside_monthly * expected_months_funded
        return pass_rate * expected_payout - self.total_premium

    def option_leverage(self, pass_rate: float, expected_months_funded: float = 6.0) -> float:
        """
        Ratio of expected payout to premium — measures the convexity.
        Higher is better; >1 means positive EV even accounting for pass rate.
        """
        return (pass_rate * self.max_upside_monthly * expected_months_funded) / max(self.total_premium, 1)
