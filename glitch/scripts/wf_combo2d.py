"""
Glitch — Walk-forward de combo_2d (mean-reversion dia-a-dia, MES+MNQ)
========================================================================
Corre walk-forward OOS sobre la señal combo_2d real (misma logica que
scheduler/combo2d_scheduler.py), geometria de produccion pt=2.5x/sl=1.5x
ATR(20), ejecutada en MNQ, max_holding=60 barras (9:30->14:30 CT).

combo_2d es una regla fija (no se "entrena" — no tiene parametros que
ajustar por ventana), asi que el walk-forward aqui particiona la muestra
en folds secuenciales de ~63 dias de trading para el t-test de
significancia OOS, sin usar la ventana de train para fittear nada
(coherente con la metodologia ya usada en el resto del repo:
"nunca reportar muestra completa sin walk-forward").

Uso:
    python scripts/wf_combo2d.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from strategies.combo2d import generate_combo2d_signal_table

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")
MNQ_PATH = os.path.join(DATA_DIR, "mnq_5min_2y.parquet")

FOLD_DAYS = 63
MIN_TRADES_PER_FOLD = 5
CFG = BarrierConfig(pt_multiplier=2.5, sl_multiplier=1.5, max_holding_bars=60, volatility_window=20, use_atr=True)


def run_fold(mnq: pd.DataFrame, sig_table: pd.DataFrame, dates: list) -> dict | None:
    fold_sig = sig_table.loc[sig_table.index.isin(dates)]
    longs  = fold_sig.loc[fold_sig.side == 1, "mnq_entry_pos"].values
    shorts = fold_sig.loc[fold_sig.side == -1, "mnq_entry_pos"].values

    labels_l = label_triple_barrier(mnq, longs, CFG, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(mnq, shorts, CFG, side=-1) if len(shorts) else pd.DataFrame()
    labels = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()

    if labels.empty or len(labels) < MIN_TRADES_PER_FOLD:
        return None

    wins   = labels[labels["label"] ==  1]["pnl_usd"]
    losses = labels[labels["label"] == -1]["pnl_usd"].abs()
    all_pnl = labels["pnl_usd"]  # pnl_pct * entry_price, "por unidad" (puntos de indice)

    n_trades = len(labels)
    win_rate = len(wins) / n_trades
    ev = float(all_pnl.mean())

    return {
        "n_trades": n_trades,
        "win_rate": round(win_rate, 4),
        "ev_per_trade_pts": round(ev, 4),
    }


def main():
    mes = pd.read_parquet(MES_PATH)
    mnq = pd.read_parquet(MNQ_PATH)
    sig_table = generate_combo2d_signal_table(mes, mnq)

    all_dates = list(sig_table.index)
    folds = []
    for i in range(0, len(all_dates), FOLD_DAYS):
        fold_dates = all_dates[i:i + FOLD_DAYS]
        if len(fold_dates) < FOLD_DAYS // 2:
            continue
        r = run_fold(mnq, sig_table, fold_dates)
        if r is not None:
            r["fold"] = len(folds)
            r["start"] = str(fold_dates[0])
            r["end"] = str(fold_dates[-1])
            folds.append(r)

    wf = pd.DataFrame(folds)
    print(wf.to_string(index=False))

    if len(wf) < 2:
        print("\nMuy pocos folds validos para t-test.")
        return

    evs = wf["ev_per_trade_pts"].values
    t_stat, p_two = scipy_stats.ttest_1samp(evs, 0)
    p_one = p_two / 2 if t_stat > 0 else 1.0

    print(f"\nFolds: {len(wf)}")
    print(f"Total trades: {int(wf['n_trades'].sum())}")
    print(f"Mean EV/trade (pts): {evs.mean():.4f}")
    print(f"Mean win rate: {wf['win_rate'].mean():.4f}")
    print(f"t_stat: {t_stat:.4f}")
    print(f"p_value_one_sided: {p_one:.4f}")


if __name__ == "__main__":
    main()
