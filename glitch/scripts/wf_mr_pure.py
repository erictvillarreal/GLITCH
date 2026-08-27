"""
Glitch — Walk-forward del candidato mean-reversion dia-a-dia PURO (MES)
==========================================================================
Mismo candidato descrito en la sesion original de investigacion (p=0.149
citado): side=-sign(ret_prev), sin MNQ, sin doble confirmacion, operado
directamente en MES. Corre EXACTAMENTE la misma metodologia de
walk-forward (folds secuenciales, t-test OOS) y la MISMA geometria de
barrera (pt=2.5x/sl=1.5x ATR(20), max_holding=60 barras) que
scripts/wf_combo2d.py, para que la unica variable que cambia entre los
dos candidatos sea la señal -- no la geometria ni la metodologia.

Uso:
    python scripts/wf_mr_pure.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from strategies.mr_pure import generate_mr_pure_signal_table

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")

FOLD_DAYS = 63
MIN_TRADES_PER_FOLD = 5
CFG = BarrierConfig(pt_multiplier=2.5, sl_multiplier=1.5, max_holding_bars=60, volatility_window=20, use_atr=True)


def run_fold(mes: pd.DataFrame, sig_table: pd.DataFrame, dates: list) -> dict | None:
    fold_sig = sig_table.loc[sig_table.index.isin(dates)]
    longs  = fold_sig.loc[fold_sig.side == 1, "mes_entry_pos"].values
    shorts = fold_sig.loc[fold_sig.side == -1, "mes_entry_pos"].values

    labels_l = label_triple_barrier(mes, longs, CFG, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(mes, shorts, CFG, side=-1) if len(shorts) else pd.DataFrame()
    labels = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()

    if labels.empty or len(labels) < MIN_TRADES_PER_FOLD:
        return None

    wins = labels[labels["label"] == 1]["pnl_usd"]
    all_pnl = labels["pnl_usd"]

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
    sig_table = generate_mr_pure_signal_table(mes)

    n_signal_days = int((sig_table["side"] != 0).sum())
    print(f"Dias con señal MR-pura: {n_signal_days} de {len(sig_table)} dias evaluados")
    print(f"Longs: {int((sig_table.side == 1).sum())}  Shorts: {int((sig_table.side == -1).sum())}\n")

    all_dates = list(sig_table.index)
    folds = []
    for i in range(0, len(all_dates), FOLD_DAYS):
        fold_dates = all_dates[i:i + FOLD_DAYS]
        if len(fold_dates) < FOLD_DAYS // 2:
            continue
        r = run_fold(mes, sig_table, fold_dates)
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
