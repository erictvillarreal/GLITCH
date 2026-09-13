"""
Glitch — Cerebro 2 pivote: variantes de construccion del spread MES-M2K
(04-sep-2026)
========================================================================
Rama cerebro2-dev. wf_slow_spreads.py probo MES-M2K con una sola
construccion (ratio de cierres) y solo 3 configs (daily hold=3d/5d,
weekly hold=5d), dando weekly hold=5d/fade como el mas cercano
(p=0.062, no significativo). Aqui se prueban 2 construcciones
independientes del spread x lookback{1,5} x hold{2,3,5,10,15} x
direccion = 40 combinaciones, para ver si el resultado sobrevive a mas
cobertura y si distintas formas de construir el spread coinciden.

Construccion A (ratio_close): close_A / close_B -- misma que
wf_slow_spreads.py.
Construccion B (retdiff_index): indice sintetico dollar/beta-neutral,
acumulando (retorno_A - retorno_B) dia a dia -- mas estandar para un
par trade real (neutraliza diferencias de nivel de precio entre
productos). Ambas usan solo cierre (open=high=low=close), use_atr=False
(mismo criterio que wf_slow_spreads.py -- sin datos intradia
sincronizados para reconstruir un rango real del spread).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, CFG, DATA_DIR

STEM_A, STEM_B = "mes", "m2k"
LOOKBACKS = (1, 5)
HOLDS = (2, 3, 5, 10, 15)
DIRECTIONS = ("fade", "momentum")


def build_spread_ratio(stem_a: str, stem_b: str) -> pd.DataFrame:
    a = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_a}_5min_2y.parquet")))
    b = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_b}_5min_2y.parquet")))
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    s = pd.DataFrame(index=common)
    s["close"] = a["close"] / b["close"]
    s["open"] = s["high"] = s["low"] = s["close"]
    return s


def build_spread_retdiff(stem_a: str, stem_b: str) -> pd.DataFrame:
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


def run(daily: pd.DataFrame, lookback: int, hold: int, direction: str) -> pd.DataFrame:
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


def fold_test(trades: pd.DataFrame, fold_days: int = 126) -> dict:
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


def split_half(trades: pd.DataFrame) -> dict:
    mid = trades["entry_date"].min() + (trades["entry_date"].max() - trades["entry_date"].min()) / 2
    h1, h2 = trades[trades["entry_date"] < mid], trades[trades["entry_date"] >= mid]
    return {
        "n1": len(h1), "ev1_pct": round(float(h1["pnl_pct"].mean() * 100), 4),
        "n2": len(h2), "ev2_pct": round(float(h2["pnl_pct"].mean() * 100), 4),
        "same_sign": bool((h1["pnl_pct"].mean() > 0) == (h2["pnl_pct"].mean() > 0)),
    }


def main():
    ratio_spread = build_spread_ratio(STEM_A, STEM_B)
    retdiff_spread = build_spread_retdiff(STEM_A, STEM_B)

    rows = []
    for constr_name, spread in [("ratio_close", ratio_spread), ("retdiff_index", retdiff_spread)]:
        for lookback in LOOKBACKS:
            for hold in HOLDS:
                for direction in DIRECTIONS:
                    trades = run(spread, lookback, hold, direction)
                    r = fold_test(trades)
                    r.update(construction=constr_name, lookback=lookback, hold=hold, direction=direction)
                    rows.append(r)

    df = pd.DataFrame(rows)
    valid = df[df["p_one_sided"].notna()].sort_values("p_one_sided")
    print(valid[["construction", "lookback", "hold", "direction", "n_trades", "mean_ev_pct", "p_one_sided"]].head(15).to_string(index=False))
    print(f"\nTotal validos: {len(valid)}  |  p<0.05: {(valid['p_one_sided']<0.05).sum()}  |  N>200: {(valid['n_trades']>200).sum()}")

    print("\n--- Detalle del mejor resultado (ambas construcciones), con split de mitades ---")
    for constr_name, spread in [("ratio_close", ratio_spread), ("retdiff_index", retdiff_spread)]:
        trades = run(spread, 1, 5, "momentum")
        trades = trades.sort_values("entry_date")
        print(f"{constr_name} / daily hold=5d / momentum: {fold_test(trades)}  split={split_half(trades)}")
        trades["dow"] = trades["entry_date"].dt.day_name()
        g = trades.groupby("dow")["pnl_pct"].mean() * 100
        print(f"  por dia de semana: {g.reindex(['Monday','Tuesday','Wednesday','Thursday','Friday']).round(4).to_dict()}")


if __name__ == "__main__":
    main()
