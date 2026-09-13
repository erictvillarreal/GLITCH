"""
Glitch — Cerebro 2 pivote: TODOS los pares posibles entre los 6
productos originales, misma profundidad que MES-M2K (04-sep-2026)
========================================================================
Rama cerebro2-dev. wf_slow_spreads_variants.py solo probo MES-M2K (1 de
15 pares posibles entre MES/MGC/M2K/MCL/M6E/ZN). Aqui se corren los 14
pares restantes con EXACTAMENTE la misma profundidad: 2 construcciones
(ratio de cierres, indice dollar-neutral retA-retB) x lookback{1,5} x
hold{2,3,5,10,15} x direccion = 40 combos por par x 14 pares = 560
combos nuevos (+ 40 de MES-M2K ya existentes = 600 en la tabla
consolidada).
"""
from __future__ import annotations
import os
import sys
import itertools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, CFG, DATA_DIR

PRODUCTS = {"MES": "mes", "MGC": "mgc", "M2K": "m2k", "MCL": "mcl", "M6E": "m6e", "ZN": "zn"}
LOOKBACKS = (1, 5)
HOLDS = (2, 3, 5, 10, 15)
DIRECTIONS = ("fade", "momentum")


def build_spread_ratio(stem_a, stem_b):
    a = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_a}_5min_2y.parquet")))
    b = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_b}_5min_2y.parquet")))
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    s = pd.DataFrame(index=common)
    s["close"] = a["close"] / b["close"]
    s["open"] = s["high"] = s["low"] = s["close"]
    return s


def build_spread_retdiff(stem_a, stem_b):
    a = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_a}_5min_2y.parquet")))
    b = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_b}_5min_2y.parquet")))
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    ret_diff = (a["close"].pct_change() - b["close"].pct_change()).fillna(0)
    index_level = 100 * (1 + ret_diff).cumprod()
    s = pd.DataFrame(index=common)
    s["close"] = index_level
    s["open"] = s["high"] = s["low"] = s["close"]
    return s


def run(daily, lookback, hold, direction):
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=hold, volatility_window=CFG.volatility_window, use_atr=False)
    sig = make_signal_indices(daily, lookback, hold, direction)
    if len(sig) == 0:
        return pd.DataFrame()
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()
    if full.empty:
        return full
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]
    return full


def fold_test(trades, fold_days=126):
    if trades.empty or len(trades) < 10:
        return {"n_trades": len(trades), "p_one_sided": None}
    start, end = trades["entry_date"].min(), trades["entry_date"].max() + pd.Timedelta(days=1)
    bounds = pd.date_range(start, end, freq=f"{fold_days}D")
    if bounds[-1] < end:
        bounds = bounds.append(pd.DatetimeIndex([end]))
    evs = []
    for i in range(len(bounds) - 1):
        f = trades[(trades["entry_date"] >= bounds[i]) & (trades["entry_date"] < bounds[i + 1])]
        if len(f) >= 3:
            evs.append(f["pnl_pct"].mean() * 100)
    if len(evs) < 2:
        return {"n_trades": len(trades), "p_one_sided": None}
    t, p2 = scipy_stats.ttest_1samp(evs, 0)
    p1 = p2 / 2 if t > 0 else 1.0
    return {"n_trades": len(trades), "mean_ev_pct": round(float(sum(evs) / len(evs)), 4), "p_one_sided": round(float(p1), 4)}


def split_half(trades):
    if trades.empty:
        return {"same_sign": None}
    mid = trades["entry_date"].min() + (trades["entry_date"].max() - trades["entry_date"].min()) / 2
    h1, h2 = trades[trades["entry_date"] < mid], trades[trades["entry_date"] >= mid]
    if len(h1) < 3 or len(h2) < 3:
        return {"same_sign": None}
    return {"same_sign": bool((h1["pnl_pct"].mean() > 0) == (h2["pnl_pct"].mean() > 0)),
            "ev1_pct": round(float(h1["pnl_pct"].mean() * 100), 4), "ev2_pct": round(float(h2["pnl_pct"].mean() * 100), 4)}


def main():
    pairs = list(itertools.combinations(sorted(PRODUCTS), 2))
    print(f"Pares a correr: {len(pairs)} -> {pairs}\n")

    rows = []
    for prod_a, prod_b in pairs:
        stem_a, stem_b = PRODUCTS[prod_a], PRODUCTS[prod_b]
        pair_label = f"{prod_a}-{prod_b}"
        ratio_spread = build_spread_ratio(stem_a, stem_b)
        retdiff_spread = build_spread_retdiff(stem_a, stem_b)
        for constr_name, spread in [("ratio_close", ratio_spread), ("retdiff_index", retdiff_spread)]:
            for lookback in LOOKBACKS:
                for hold in HOLDS:
                    for direction in DIRECTIONS:
                        trades = run(spread, lookback, hold, direction)
                        r = fold_test(trades)
                        sh = split_half(trades) if not trades.empty else {"same_sign": None}
                        r.update(pair=pair_label, construction=constr_name, lookback=lookback,
                                  hold=hold, direction=direction, same_sign_halves=sh.get("same_sign"))
                        rows.append(r)

    df = pd.DataFrame(rows)
    out_path = os.path.join(DATA_DIR, "cerebro2_pairs_full_grid.csv")
    df.to_csv(out_path, index=False)
    print(f"Guardado: {out_path} ({len(df)} filas)\n")

    valid = df[df["p_one_sided"].notna()].sort_values("p_one_sided")
    print(f"Total validos: {len(valid)}  |  p<0.05: {(valid['p_one_sided']<0.05).sum()}  |  N>200: {(valid['n_trades']>200).sum()}")
    print("\nTop 20 por p-value:")
    print(valid[["pair", "construction", "lookback", "hold", "direction", "n_trades",
                 "mean_ev_pct", "p_one_sided", "same_sign_halves"]].head(20).to_string(index=False))

    print("\nCombinaciones con N>200 (cualquier p):")
    over200 = valid[valid["n_trades"] > 200].sort_values("p_one_sided")
    print(over200[["pair", "construction", "lookback", "hold", "direction", "n_trades",
                    "mean_ev_pct", "p_one_sided"]].to_string(index=False) if not over200.empty else "  (ninguna)")


if __name__ == "__main__":
    main()
