"""
Glitch — Cerebro 2 pivote: extension de hold periods y productos
(04-sep-2026)
========================================================================
Rama cerebro2-dev. Extiende la Direccion 1 (timeframes lentos) mas
alla de lo ya probado (daily hold=3d/5d, weekly hold=5d en MES/MGC) --
agrega holds mas cortos (2d) y mas largos (10d/15d), y los 4 productos
adicionales con datos ya confirmados en data_cache/ (M2K/RTY, MCL/CL,
M6E/6E, ZN). Misma metodologia exacta (triple_barrier + walk-forward
por folds + t-test OOS, fade Y momentum, entradas no solapadas) --
NINGUN cambio de metodologia, solo mas cobertura del mismo diseño ya
validado.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from scripts.wf_slow_mr import resample_daily, run_fold_walk_forward, summarize, DATA_DIR

PRODUCTS = {"MES": "mes", "MGC": "mgc", "M2K": "m2k", "MCL": "mcl", "M6E": "m6e", "ZN": "zn"}
LOOKBACK_HOLD = [
    (1, 2), (1, 3), (1, 5), (1, 10), (1, 15),   # señal diaria, holds 2-15d
    (5, 5), (5, 10), (5, 15),                    # señal semanal, holds 5-15d
]
DIRECTIONS = ("fade", "momentum")


def main():
    rows = []
    daily_cache = {}
    for product, stem in PRODUCTS.items():
        daily_cache[product] = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))

    for product, daily in daily_cache.items():
        for lookback, hold in LOOKBACK_HOLD:
            for direction in DIRECTIONS:
                wf = run_fold_walk_forward(daily, lookback, hold, direction)
                s = summarize(wf, f"{product}/lb{lookback}/hold{hold}/{direction}")
                s["product"] = product
                s["lookback"] = lookback
                s["hold"] = hold
                s["direction"] = direction
                rows.append(s)

    df = pd.DataFrame(rows)
    out_path = os.path.join(DATA_DIR, "cerebro2_slow_mr_grid.csv")
    df.to_csv(out_path, index=False)
    print(f"Guardado: {out_path} ({len(df)} filas)\n")

    print("=" * 100)
    print(f"Total experimentos: {len(df)}  |  N>200: {df['n_over_200'].sum()}  |  p<0.05: {df['significant_5pct'].sum()}")
    print("=" * 100)

    print("\nTop 15 por p-value (menor primero), incluye N y si cruza N>200:")
    top = df.sort_values("p_value_one_sided").head(15)
    print(top[["product", "lookback", "hold", "direction", "total_trades", "n_over_200",
               "mean_ev_pct", "p_value_one_sided", "significant_5pct"]].to_string(index=False))

    print("\nExperimentos con N>200 (potencia real, cualquier p):")
    over200 = df[df["n_over_200"]].sort_values("p_value_one_sided")
    if over200.empty:
        print("  (ninguno)")
    else:
        print(over200[["product", "lookback", "hold", "direction", "total_trades",
                        "mean_ev_pct", "p_value_one_sided", "significant_5pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
