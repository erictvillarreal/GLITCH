"""
Glitch — Strategy Grid Search Optimizer
=========================================
Exhaustive parameter sweep over (win_rate × rr × risk_pct) space
to find strategies that maximise P(pass) and system EV.

This is the core tool for:
  - Identifying the optimal risk geometry for each firm
  - Proving the convex payoff thesis quantitatively
  - Generating the strategy heatmaps for institutional reporting

Usage
-----
>>> from simulation.optimizer import GridSearchOptimizer
>>> from core.prop_firm import load_firm
>>> 
>>> firm = load_firm("ftmo_100k")
>>> opt = GridSearchOptimizer(firm, n_paths=5000)
>>> results_df = opt.run()
>>> opt.plot_heatmap(results_df)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from itertools import product
from tqdm import tqdm

from core.prop_firm import PropFirmConfig
from simulation.monte_carlo import MonteCarloSimulator, StrategyParams


@dataclass
class GridConfig:
    win_rates: List[float] = None
    rr_values: List[float] = None
    risk_pcts: List[float] = None
    trades_per_day: float = 3.0

    def __post_init__(self):
        if self.win_rates is None:
            self.win_rates = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
        if self.rr_values is None:
            self.rr_values = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
        if self.risk_pcts is None:
            self.risk_pcts = [0.003, 0.005, 0.008, 0.01]


class GridSearchOptimizer:
    """
    Runs Monte Carlo simulation across a parameter grid.
    Returns a DataFrame with all results, sortable by any metric.
    """

    def __init__(
        self,
        firm: PropFirmConfig,
        grid: Optional[GridConfig] = None,
        n_paths: int = 5_000,
        seed: int = 42,
    ):
        self.firm = firm
        self.grid = grid or GridConfig()
        self.n_paths = n_paths
        self.seed = seed

    def run(self, verbose: bool = True) -> pd.DataFrame:
        """
        Execute grid search. Returns DataFrame with one row per parameter combo.
        """
        combos = list(product(
            self.grid.win_rates,
            self.grid.rr_values,
            self.grid.risk_pcts,
        ))

        rows = []
        iterator = tqdm(combos, desc="Grid search") if verbose else combos

        for wr, rr, risk in iterator:
            # Skip zero or negative EV only if strictly necessary
            # (we want to show even negative-EV strategies can pass via convexity)
            strategy = StrategyParams(
                win_rate=wr,
                rr=rr,
                risk_per_trade_pct=risk,
                trades_per_day=self.grid.trades_per_day,
                strategy_name=f"WR{wr:.0%}_RR{rr}_R{risk:.1%}",
            )

            sim = MonteCarloSimulator(
                self.firm, strategy,
                n_paths=self.n_paths,
                seed=self.seed,
            )
            result = sim.run()

            # Compute challenge phase pass rates individually
            challenge_rates = []
            for pr in result.phase_results:
                if "funded" not in pr.phase_name.lower():
                    challenge_rates.append(pr.pass_rate)

            rows.append({
                "win_rate": wr,
                "rr": rr,
                "risk_pct": risk,
                "ev_per_trade_pct": strategy.expected_value_per_trade_pct * 100,
                "system_pass_rate": result.system_pass_rate,
                "system_ev_usd": result.system_ev_per_attempt,
                "avg_payout": result.avg_payout_given_pass,
                "phase1_pass_rate": challenge_rates[0] if len(challenge_rates) > 0 else None,
                "phase2_pass_rate": challenge_rates[1] if len(challenge_rates) > 1 else None,
                "attempts_to_fund": 1 / result.system_pass_rate if result.system_pass_rate > 0 else np.inf,
            })

        df = pd.DataFrame(rows)
        df = df.sort_values("system_ev_usd", ascending=False).reset_index(drop=True)
        return df

    def top_n(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """Return top N strategies sorted by system EV."""
        return df.head(n)

    def pareto_front(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return strategies on the Pareto front of (pass_rate, ev_usd).
        These are strategies where no other strategy dominates on both metrics.
        """
        dominated = []
        for i, row_i in df.iterrows():
            for j, row_j in df.iterrows():
                if i == j:
                    continue
                if (row_j["system_pass_rate"] >= row_i["system_pass_rate"] and
                        row_j["system_ev_usd"] >= row_i["system_ev_usd"] and
                        (row_j["system_pass_rate"] > row_i["system_pass_rate"] or
                         row_j["system_ev_usd"] > row_i["system_ev_usd"])):
                    dominated.append(i)
                    break
        return df.drop(index=dominated).reset_index(drop=True)

    def sensitivity_analysis(
        self,
        base_strategy: StrategyParams,
        param: str,
        values: List[float],
        n_paths: int = 10_000,
    ) -> pd.DataFrame:
        """
        Test sensitivity of system EV to a single parameter change.
        Returns DataFrame with one row per value.
        """
        rows = []
        for v in values:
            s = StrategyParams(
                win_rate=base_strategy.win_rate if param != "win_rate" else v,
                rr=base_strategy.rr if param != "rr" else v,
                risk_per_trade_pct=base_strategy.risk_per_trade_pct if param != "risk_pct" else v,
                trades_per_day=base_strategy.trades_per_day,
            )
            sim = MonteCarloSimulator(self.firm, s, n_paths=n_paths, seed=self.seed)
            r = sim.run()
            rows.append({param: v, "system_ev_usd": r.system_ev_per_attempt,
                         "system_pass_rate": r.system_pass_rate})
        return pd.DataFrame(rows)
