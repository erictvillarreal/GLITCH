"""
Glitch — Strategy Grid Search for Topstep 50K
===============================================
Sweeps (win_rate × avg_win × avg_loss) space.
Returns a DataFrame ranked by system EV.

The optimizer answers: "which daily P&L distribution
gives the highest probability of passing the Topstep 50K
while staying below the consistency ceiling?"
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from itertools import product
from typing import List, Optional
from tqdm import tqdm

from core.prop_firm import TopstepCombineSpec, TOPSTEP_50K
from simulation.monte_carlo import TopstepMonteCarloSimulator, DailyReturnDist, SimResult


def run_grid_search(
    spec: TopstepCombineSpec = TOPSTEP_50K,
    win_rates:  List[float] = None,
    avg_wins:   List[float] = None,
    avg_losses: List[float] = None,
    n_paths: int = 10_000,
    max_days: int = 120,
    seed: int = 42,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Full grid search over strategy parameter space.

    Default grid is calibrated for Topstep 50K:
      - win_rates:  30% to 75% (realistic range for futures day strategies)
      - avg_wins:   $100–$600/day  (1–6 MES contracts, 4–24 ticks ES)
      - avg_losses: $80–$400/day
    """
    if win_rates is None:
        win_rates = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    if avg_wins is None:
        avg_wins = [100, 150, 200, 250, 300, 400, 500]
    if avg_losses is None:
        avg_losses = [80, 120, 160, 200, 250, 300]

    combos = list(product(win_rates, avg_wins, avg_losses))
    rows = []
    it = tqdm(combos, desc="Grid search") if verbose else combos

    for wr, aw, al in it:
        dist = DailyReturnDist(win_rate=wr, avg_win=aw, avg_loss=al,
                               name=f"WR{wr:.0%}_W{aw}_L{al}")
        sim = TopstepMonteCarloSimulator(dist, spec, n_paths=n_paths,
                                         max_days=max_days, seed=seed)
        r = sim.run()
        ci_lo, ci_hi = r.wilson_ci()
        rows.append({
            "win_rate":       wr,
            "avg_win":        aw,
            "avg_loss":       al,
            "rr":             round(aw / al, 3),
            "ev_per_day":     round(dist.expected_daily_pnl, 2),
            "pass_rate":      round(r.pass_rate, 4),
            "ci_lo":          round(ci_lo, 4),
            "ci_hi":          round(ci_hi, 4),
            "blow_rate":      round(r.blow_rate, 4),
            "cons_gate_rate": round(r.consistency_gate_rate, 4),
            "avg_pass_days":  round(r.avg_pass_days or 0, 1),
            "system_ev":      round(r.system_ev, 1),
        })

    df = pd.DataFrame(rows).sort_values("system_ev", ascending=False).reset_index(drop=True)
    return df


def minimum_sample_size(target_pass_rate: float, margin: float = 0.03,
                        alpha: float = 0.05) -> int:
    """
    Minimum n_paths for a Wilson CI half-width ≤ margin at the target pass rate.
    Standard formula: n = z² * p*(1-p) / margin²
    """
    from scipy.stats import norm
    z = norm.ppf(1 - alpha / 2)
    p = target_pass_rate
    return int(np.ceil(z**2 * p * (1 - p) / margin**2))
