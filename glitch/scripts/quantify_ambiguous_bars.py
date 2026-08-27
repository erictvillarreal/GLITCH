"""
Glitch — Quantify Ambiguous Bars
==================================
Mide que fraccion de los "wins" reportados por label_triple_barrier()
vienen de barras donde TP y SL fueron tocados en la MISMA barra (5min) —
la barra es demasiado ancha para distinguir cual golpeo primero, y el
codigo actual (simulation/triple_barrier.py) siempre resuelve a favor del
"gano" tanto para LONG como para SHORT. Eso infla el win rate.

Corre dos casos:
  A) SL=10/TP=10 ticks fijos, entrada alternando long/short SIN señal
     (el caso que disparo la alarma original: WR_long+WR_short=1.262).
  B) Geometria real de produccion: pt=2.5x ATR / sl=1.5x ATR (20 barras),
     sobre la señal real combo_2d (mean-reversion dia-a-dia, doble
     confirmacion MES+MNQ), ejecutada en MNQ, max_holding=60 barras
     (9:30->14:30 CT, igual que el scheduler en vivo).

NO modifica simulation/triple_barrier.py — solo lo instrumenta desde afuera
para contar barras ambiguas ademas de correr el labeling normal.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from simulation.triple_barrier import BarrierConfig, label_triple_barrier, compute_atr
from strategies.combo2d import generate_combo2d_signal_table

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")
MNQ_PATH = os.path.join(DATA_DIR, "mnq_5min_2y.parquet")


def count_ambiguous_wins(prices: pd.DataFrame, signal_indices: np.ndarray,
                          cfg: BarrierConfig, side: int) -> dict:
    """
    Re-implementa el walk de barras de label_triple_barrier() pero, en vez de
    romper en el primer touch, chequea si AMBAS barreras se tocaron en la
    misma barra resolutoria. Devuelve conteos agregados.
    """
    close = prices["close"].values
    high  = prices["high"].values
    low   = prices["low"].values

    if cfg.use_atr:
        vol = compute_atr(high, low, close, cfg.volatility_window)
    else:
        vol = pd.Series(close).pct_change().rolling(cfg.volatility_window).std().values
        vol = np.abs(vol * close)
        vol = np.nan_to_num(vol, nan=close * 0.001)

    n = len(prices)
    n_entries = 0
    n_wins_reported = 0     # label==1 bajo la logica actual (buggy: win-primero)
    n_wins_ambiguous = 0    # de esos wins, cuantos tenian TAMBIEN el SL tocado en la misma barra
    n_losses_reported = 0
    n_time_barrier = 0

    for entry_i in signal_indices:
        entry_i = int(entry_i)
        if entry_i >= n - 1:
            continue
        n_entries += 1
        entry_price = close[entry_i]
        v = vol[entry_i]
        upper = entry_price + side * cfg.pt_multiplier * v
        lower = entry_price - side * cfg.sl_multiplier * v
        exit_i = min(entry_i + cfg.max_holding_bars, n - 1)

        resolved = False
        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]
            if side == 1:
                win_touch  = h >= upper
                loss_touch = l <= lower
            else:
                win_touch  = l <= upper
                loss_touch = h >= lower

            if win_touch or loss_touch:
                resolved = True
                if win_touch:
                    n_wins_reported += 1
                    if loss_touch:
                        n_wins_ambiguous += 1
                else:
                    n_losses_reported += 1
                break
        if not resolved:
            n_time_barrier += 1

    return {
        "n_entries": n_entries,
        "n_wins_reported": n_wins_reported,
        "n_wins_ambiguous": n_wins_ambiguous,
        "pct_wins_ambiguous": (n_wins_ambiguous / n_wins_reported * 100) if n_wins_reported else 0.0,
        "n_losses_reported": n_losses_reported,
        "n_time_barrier": n_time_barrier,
    }


def fixed_tick_upper_lower_case(mes_prices: pd.DataFrame, tp_ticks: float = 10, sl_ticks: float = 10,
                                 tick_size: float = 0.25, max_holding_bars: int = 20) -> dict:
    """
    Caso A: SL=TP=10 ticks FIJOS (no ATR), entrada alternando long/short en
    cada barra, sin señal — replica el test aislado que disparo la alarma.
    """
    close = mes_prices["close"].values
    high  = mes_prices["high"].values
    low   = mes_prices["low"].values
    n = len(mes_prices)

    tp_pts = tp_ticks * tick_size
    sl_pts = sl_ticks * tick_size

    signal_indices = np.arange(0, n - max_holding_bars - 1, 1)

    agg = {"n_entries": 0, "n_wins_reported": 0, "n_wins_ambiguous": 0,
           "n_losses_reported": 0, "n_time_barrier": 0}

    for k, entry_i in enumerate(signal_indices):
        side = 1 if k % 2 == 0 else -1
        entry_i = int(entry_i)
        entry_price = close[entry_i]
        upper = entry_price + side * tp_pts
        lower = entry_price - side * sl_pts
        exit_i = min(entry_i + max_holding_bars, n - 1)

        agg["n_entries"] += 1
        resolved = False
        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]
            if side == 1:
                win_touch  = h >= upper
                loss_touch = l <= lower
            else:
                win_touch  = l <= upper
                loss_touch = h >= lower
            if win_touch or loss_touch:
                resolved = True
                if win_touch:
                    agg["n_wins_reported"] += 1
                    if loss_touch:
                        agg["n_wins_ambiguous"] += 1
                else:
                    agg["n_losses_reported"] += 1
                break
        if not resolved:
            agg["n_time_barrier"] += 1

    agg["pct_wins_ambiguous"] = (agg["n_wins_ambiguous"] / agg["n_wins_reported"] * 100) if agg["n_wins_reported"] else 0.0
    return agg


def main():
    print("Cargando datos...")
    mes = pd.read_parquet(MES_PATH)
    mnq = pd.read_parquet(MNQ_PATH)
    print(f"  MES: {len(mes):,} barras RTH  {mes.index.min()} -> {mes.index.max()}")
    print(f"  MNQ: {len(mnq):,} barras RTH  {mnq.index.min()} -> {mnq.index.max()}")

    print("\n" + "=" * 70)
    print("CASO A — SL=10/TP=10 ticks fijos, sin señal, alterna long/short (MES)")
    print("=" * 70)
    case_a = fixed_tick_upper_lower_case(mes, tp_ticks=10, sl_ticks=10, max_holding_bars=20)
    for k, v in case_a.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("CASO B — Geometria real de produccion: pt=2.5x/sl=1.5x ATR(20), combo_2d, MNQ")
    print("=" * 70)
    sig_table = generate_combo2d_signal_table(mes, mnq)
    n_signal_days = int((sig_table["side"] != 0).sum())
    print(f"  Dias con señal combo_2d: {n_signal_days} de {len(sig_table)} dias evaluados")

    longs  = sig_table.loc[sig_table.side == 1, "mnq_entry_pos"].values
    shorts = sig_table.loc[sig_table.side == -1, "mnq_entry_pos"].values
    print(f"  Longs: {len(longs)}  Shorts: {len(shorts)}")

    cfg = BarrierConfig(pt_multiplier=2.5, sl_multiplier=1.5, max_holding_bars=60, volatility_window=20, use_atr=True)

    res_long  = count_ambiguous_wins(mnq, longs, cfg, side=1)
    res_short = count_ambiguous_wins(mnq, shorts, cfg, side=-1)

    combined = {k: res_long[k] + res_short[k] for k in
                ["n_entries", "n_wins_reported", "n_wins_ambiguous", "n_losses_reported", "n_time_barrier"]}
    combined["pct_wins_ambiguous"] = (combined["n_wins_ambiguous"] / combined["n_wins_reported"] * 100) if combined["n_wins_reported"] else 0.0

    print("\n  -- LONG --")
    for k, v in res_long.items():
        print(f"    {k}: {v}")
    print("  -- SHORT --")
    for k, v in res_short.items():
        print(f"    {k}: {v}")
    print("  -- COMBINADO --")
    for k, v in combined.items():
        print(f"    {k}: {v}")

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Caso A (SL=10/TP=10 fijo, sin señal):  {case_a['pct_wins_ambiguous']:.1f}% de los wins son barras ambiguas  ({case_a['n_wins_ambiguous']}/{case_a['n_wins_reported']})")
    print(f"Caso B (geometria real combo_2d):       {combined['pct_wins_ambiguous']:.1f}% de los wins son barras ambiguas  ({combined['n_wins_ambiguous']}/{combined['n_wins_reported']})")


if __name__ == "__main__":
    main()
