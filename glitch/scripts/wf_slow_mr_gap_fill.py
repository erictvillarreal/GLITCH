"""
Glitch — Cerebro 2 pivote: cierre de gaps identificados en la auditoria
de Tarea 0 (06-sep-2026)
========================================================================
Rama cerebro2-dev. Tres piezas pendientes tras la auditoria honesta de
que tan agotada estaba la busqueda de edge:
  1. Refinamiento (dia de semana, filtro volumen/rango) para los
     candidatos individuales MCL daily-2d/fade y M6E daily-3d/fade,
     que nunca recibieron el mismo tratamiento que el flagship
     MES+MGC weekly/fade.
  2. Dia de semana + split de mitades para el 2do hallazgo del spread
     MES-M2K (daily hold=10d/fade), tratado superficialmente antes.
  3. Barrido de geometria de barrera (pt/sl multiplier) para los 2
     candidatos mas fuertes -- nunca se habia variado esto en TODA la
     busqueda (siempre 2.5/1.5, heredado de Cerebro 1 sin revision).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, DATA_DIR
from scripts.wf_slow_mr_refinements import resample_daily_with_volrange
from scripts.wf_slow_spreads_variants import build_spread_ratio, build_spread_retdiff, run, fold_test, split_half

GEOMETRIES = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (3.0, 1.0), (1.0, 1.5),
              (1.5, 1.5), (2.5, 1.5), (3.0, 1.5), (1.0, 2.0), (2.0, 2.0)]


def trades_single(stem, lookback, hold, direction):
    daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
    cfg = BarrierConfig(pt_multiplier=2.5, sl_multiplier=1.5, max_holding_bars=hold, volatility_window=20, use_atr=True)
    sig = make_signal_indices(daily, lookback, hold, direction)
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True)
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]
    full["dow"] = full["entry_date"].dt.day_name()
    return full


def refine_single_candidate(label, stem, lookback, hold, direction):
    print(f"\n{'='*90}\n{label}\n{'='*90}")
    t = trades_single(stem, lookback, hold, direction)
    print(f"Baseline: {fold_test(t)}")
    g = t.groupby("dow")["pnl_pct"].agg(["count", "mean"])
    g["mean_pct"] = g["mean"] * 100
    print("Por dia de semana:")
    print(g[["count", "mean_pct"]].reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]).to_string())

    sh = split_half(t)
    print(f"Split mitades: {sh}")

    daily_vr = resample_daily_with_volrange(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
    vol_med = daily_vr["volume"].rolling(20, min_periods=5).median()
    range_med = daily_vr["range"].rolling(20, min_periods=5).median()
    t["vol_high"] = daily_vr["volume"].values[t["entry_idx"].astype(int)] > vol_med.values[t["entry_idx"].astype(int)]
    t["range_high"] = daily_vr["range"].values[t["entry_idx"].astype(int)] > range_med.values[t["entry_idx"].astype(int)]
    print(f"Filtro volumen alto: {fold_test(t[t['vol_high']])}   bajo: {fold_test(t[~t['vol_high']])}")
    print(f"Filtro rango alto:   {fold_test(t[t['range_high']])}   bajo: {fold_test(t[~t['range_high']])}")


def spread_second_finding():
    print(f"\n{'='*90}\nMES-M2K daily hold=10d/fade (2do hallazgo del spread)\n{'='*90}")
    for constr_name, builder in [("ratio_close", build_spread_ratio), ("retdiff_index", build_spread_retdiff)]:
        spread = builder("mes", "m2k")
        trades = run(spread, 1, 10, "fade").sort_values("entry_date")
        print(f"{constr_name}: {fold_test(trades)}  split={split_half(trades)}")
        trades["dow"] = trades["entry_date"].dt.day_name()
        g = (trades.groupby("dow")["pnl_pct"].mean() * 100).reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        print(f"  por dia semana: {g.round(4).to_dict()}")


def barrier_sweep():
    print(f"\n{'='*90}\nBarrido de geometria de barrera -- MES-M2K daily hold=5d/momentum (use_atr=False)\n{'='*90}")
    spread = build_spread_ratio("mes", "m2k")
    for pt, sl in GEOMETRIES:
        cfg = BarrierConfig(pt_multiplier=pt, sl_multiplier=sl, max_holding_bars=5, volatility_window=20, use_atr=False)
        sig = make_signal_indices(spread, 1, 5, "momentum")
        entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
        longs, shorts = entries[sides == 1], entries[sides == -1]
        labels_l = label_triple_barrier(spread, longs, cfg, side=1) if len(longs) else pd.DataFrame()
        labels_s = label_triple_barrier(spread, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
        full = pd.concat([labels_l, labels_s], ignore_index=True)
        full["entry_date"] = spread.index[full["entry_idx"].astype(int)]
        print(f"  pt={pt} sl={sl} (RR={pt/sl:.2f}): {fold_test(full)}")

    print(f"\n{'='*90}\nBarrido de geometria de barrera -- MES+MGC weekly hold=5d/fade pooled (use_atr=True)\n{'='*90}")
    for pt, sl in GEOMETRIES:
        cfg = BarrierConfig(pt_multiplier=pt, sl_multiplier=sl, max_holding_bars=5, volatility_window=20, use_atr=True)
        all_trades = []
        for stem in ("mes", "mgc"):
            daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
            sig = make_signal_indices(daily, 5, 5, "fade")
            entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
            longs, shorts = entries[sides == 1], entries[sides == -1]
            labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
            labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
            full = pd.concat([labels_l, labels_s], ignore_index=True)
            full["entry_date"] = daily.index[full["entry_idx"].astype(int)]
            all_trades.append(full)
        pooled = pd.concat(all_trades, ignore_index=True).sort_values("entry_date")
        print(f"  pt={pt} sl={sl} (RR={pt/sl:.2f}): {fold_test(pooled)}")


if __name__ == "__main__":
    refine_single_candidate("MCL daily hold=2d/fade", "mcl", 1, 2, "fade")
    refine_single_candidate("M6E daily hold=3d/fade", "m6e", 1, 3, "fade")
    spread_second_finding()
    barrier_sweep()
