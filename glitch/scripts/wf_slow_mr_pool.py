"""
Glitch — Cerebro 2 pivote: pool MES+MGC para los configs con direccion
consistente (04-sep-2026)
========================================================================
Rama cerebro2-dev. Sigue de scripts/wf_slow_mr.py (12 experimentos
individuales, ninguno N>200, ninguno p<0.05). Decision del usuario:
Camino 3 -- verificar consistencia de direccion ANTES de poolear (si
las direcciones son opuestas entre productos, poolear enmascararia
cualquier señal real, no la fortaleceria), y solo poolear donde SI son
consistentes.

Verificacion de consistencia (hecha antes de este script, con los
datos ya generados por wf_slow_mr.py): de 6 combinaciones
(config x direccion), 4 tienen el MISMO signo de EV en MES y MGC:
  - daily hold=3d / momentum   (MES +0.11%, MGC +0.02%)
  - daily hold=5d / fade       (MES +0.06%, MGC +0.17%)
  - daily hold=5d / momentum   (MES -0.05%, MGC -0.15%)
  - weekly hold=5d / fade      (MES +0.31%, MGC +0.14%)
2 tienen signos OPUESTOS -- NO se poolean, se reportan como hallazgo:
  - daily hold=3d / fade       (MES -0.15%, MGC +0.13%)
  - weekly hold=5d / momentum  (MES -0.40%, MGC +0.14%)

Pool: concatena los trades de MES y MGC (cada uno generado
independientemente con su propia señal/geometria) ORDENADOS POR FECHA
REAL de entrada -- no mezclados al azar -- y los agrupa en folds
cronologicos por calendario (no por indice de barra, que difiere en 1
entre los dos productos). Reproducibilidad: ademas del walk-forward
completo, se corre el mismo test partiendo la muestra en primera
mitad / segunda mitad temporal, exigido explicitamente antes de
confiar en cualquier numero que salga significativo.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, DATA_DIR, CFG, FOLD_DAYS

CONSISTENT_CONFIGS = [
    ("daily hold=3d / momentum", 1, 3, "momentum"),
    ("daily hold=5d / fade", 1, 5, "fade"),
    ("daily hold=5d / momentum", 1, 5, "momentum"),
    ("weekly hold=5d / fade", 5, 5, "fade"),
]


def labeled_trades_with_dates(product: str, stem: str, lookback: int, hold: int, direction: str) -> pd.DataFrame:
    daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=hold, volatility_window=CFG.volatility_window, use_atr=True)
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
    full["product"] = product
    return full


def fold_stats(trades: pd.DataFrame, fold_start: pd.Timestamp, fold_end: pd.Timestamp) -> dict | None:
    fold = trades[(trades["entry_date"] >= fold_start) & (trades["entry_date"] < fold_end)]
    if len(fold) < 3:
        return None
    wins = fold[fold["label"] == 1]["pnl_pct"]
    losses = fold[fold["label"] == -1]["pnl_pct"].abs()
    time_exits = fold[fold["label"] == 0]
    return {
        "fold_start": fold_start.date(), "fold_end": fold_end.date(),
        "n_trades": len(fold), "n_mes": int((fold["product"] == "MES").sum()), "n_mgc": int((fold["product"] == "MGC").sum()),
        "n_tp": len(wins), "n_sl": len(losses), "n_time_exit": len(time_exits),
        "ev_per_trade_pct": round(float(fold["pnl_pct"].mean() * 100), 4),
    }


def walk_forward_pooled(trades: pd.DataFrame, fold_days: int = FOLD_DAYS) -> pd.DataFrame:
    start = trades["entry_date"].min()
    end = trades["entry_date"].max() + pd.Timedelta(days=1)
    bounds = pd.date_range(start, end, freq=f"{fold_days}D")
    if bounds[-1] < end:
        bounds = bounds.append(pd.DatetimeIndex([end]))
    rows = []
    for i in range(len(bounds) - 1):
        r = fold_stats(trades, bounds[i], bounds[i + 1])
        if r is not None:
            rows.append(r)
    return pd.DataFrame(rows)


def significance(wf_df: pd.DataFrame) -> dict:
    if wf_df.empty or len(wf_df) < 2:
        return {"n_folds": len(wf_df), "p_value_one_sided": None}
    evs = wf_df["ev_per_trade_pct"].values
    t_stat, p_two = scipy_stats.ttest_1samp(evs, 0)
    p_one = p_two / 2 if t_stat > 0 else 1.0
    total = int(wf_df["n_trades"].sum())
    return {
        "n_folds": len(wf_df), "total_trades": total,
        "n_tp": int(wf_df["n_tp"].sum()), "n_sl": int(wf_df["n_sl"].sum()), "n_time_exit": int(wf_df["n_time_exit"].sum()),
        "mean_ev_pct": round(float(evs.mean()), 4),
        "t_statistic": round(float(t_stat), 3),
        "p_value_one_sided": round(float(p_one), 4),
        "significant_5pct": bool(p_one < 0.05),
        "n_over_200": bool(total > 200),
    }


def main():
    for label, lookback, hold, direction in CONSISTENT_CONFIGS:
        print(f"\n{'='*95}\nPOOL MES+MGC -- {label}\n{'='*95}")
        mes_trades = labeled_trades_with_dates("MES", "mes", lookback, hold, direction)
        mgc_trades = labeled_trades_with_dates("MGC", "mgc", lookback, hold, direction)
        pooled = pd.concat([mes_trades, mgc_trades], ignore_index=True).sort_values("entry_date").reset_index(drop=True)

        wf = walk_forward_pooled(pooled)
        print(wf.to_string(index=False))
        summary = significance(wf)
        print("FULL SAMPLE:", summary)

        # Reproducibilidad obligatoria: primera mitad vs segunda mitad temporal
        mid = pooled["entry_date"].min() + (pooled["entry_date"].max() - pooled["entry_date"].min()) / 2
        first_half = pooled[pooled["entry_date"] < mid]
        second_half = pooled[pooled["entry_date"] >= mid]
        wf_1 = walk_forward_pooled(first_half, fold_days=FOLD_DAYS // 2)
        wf_2 = walk_forward_pooled(second_half, fold_days=FOLD_DAYS // 2)
        print("PRIMERA MITAD:", significance(wf_1))
        print("SEGUNDA MITAD:", significance(wf_2))


if __name__ == "__main__":
    main()
