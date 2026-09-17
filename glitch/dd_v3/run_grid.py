"""
DD v3 -- corre el grid completo de politicas de retiro (5 payout_pct x
6 min_cushion = 30 combinaciones -- el usuario menciono "25" pero listo
6 valores de colchon, no 5; se corren los 30 literales de los rangos
dados, no se recorta uno arbitrariamente) y reporta a 1 y 3 años.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from dd_v3.withdrawal_policy_grid import simulate_with_policy, PAYOUT_PCT_GRID, MIN_CUSHION_GRID

N_PATHS = 100_000


def main():
    rows = []
    for pct in PAYOUT_PCT_GRID:
        for cushion in MIN_CUSHION_GRID:
            r = simulate_with_policy(payout_pct=pct, min_cushion=cushion, n_paths=N_PATHS, seed=7)
            for horizon in ("1y", "3y"):
                h = r[horizon]
                rows.append({
                    "payout_pct": pct, "min_cushion": cushion, "horizon": horizon,
                    "median_payout_usd": h["median_payout_usd"],
                    "avg_payout_usd": h["avg_payout_usd"],
                    "p10_payout_usd": h["p10_payout_usd"],
                    "p90_payout_usd": h["p90_payout_usd"],
                    "avg_lifetime_payouts": h["avg_lifetime_payouts"],
                    "median_lifetime_payouts": h["median_lifetime_payouts"],
                    "avg_days_alive": h["avg_days_alive"],
                    "median_days_alive": h["median_days_alive"],
                    "prob_still_alive": h["prob_still_alive"],
                    "prob_never_first_payout": h["prob_never_reached_first_payout"],
                })
            print(f"pct={pct:.0%} cushion=${cushion:5d}  done  "
                  f"(1y median=${r['1y']['median_payout_usd']:,.0f}  3y median=${r['3y']['median_payout_usd']:,.0f}  "
                  f"deferrals={r['n_deferred_total']})")

    df = pd.DataFrame(rows)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "withdrawal_policy_grid_results.csv")
    df.to_csv(out_path, index=False)
    print(f"\nGuardado: {out_path}\n")

    for horizon in ("1y", "3y"):
        sub = df[df.horizon == horizon].sort_values("median_payout_usd", ascending=False)
        print(f"\n{'='*100}\nTOP 5 por MEDIANA de payout total -- horizonte {horizon}\n{'='*100}")
        print(sub[["payout_pct", "min_cushion", "median_payout_usd", "avg_payout_usd",
                    "p10_payout_usd", "p90_payout_usd", "avg_lifetime_payouts", "avg_days_alive",
                    "prob_never_first_payout"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
