"""
Glitch — Cerebro 2 pivote: grid de ZC (Corn), nunca corrido pese a tener
datos en cache (06-sep-2026)
========================================================================
Rama cerebro2-dev. Mismo grid de 16 combos (lookback{1,5} x hold x
direccion) ya aplicado a los otros 6 productos en wf_slow_mr_grid.py --
gap identificado en la auditoria de Tarea 0.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from scripts.wf_slow_mr import resample_daily, run_fold_walk_forward, summarize, DATA_DIR

LOOKBACK_HOLD = [(1, 2), (1, 3), (1, 5), (1, 10), (1, 15), (5, 5), (5, 10), (5, 15)]


def main():
    daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, "zc_5min_2y.parquet")))
    rows = []
    for lookback, hold in LOOKBACK_HOLD:
        for direction in ("fade", "momentum"):
            wf = run_fold_walk_forward(daily, lookback, hold, direction)
            s = summarize(wf, f"ZC/lb{lookback}/hold{hold}/{direction}")
            s.update(product="ZC", lookback=lookback, hold=hold, direction=direction)
            rows.append(s)

    df = pd.DataFrame(rows)
    out_path = os.path.join(DATA_DIR, "cerebro2_zc_grid.csv")
    df.to_csv(out_path, index=False)
    print(f"ZC: {len(df)} filas guardadas en {out_path}. N>200: {df['n_over_200'].sum()}  p<0.05: {df['significant_5pct'].sum()}")
    print(df.sort_values("p_value_one_sided")[
        ["lookback", "hold", "direction", "total_trades", "n_over_200", "mean_ev_pct", "p_value_one_sided"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
