"""
Glitch — Re-validacion de la tabla de geometria pura (Camino B) post-fix
===========================================================================
Re-corre las 5 filas SL/TP en ticks fijos, entrada sin señal (alterna
long/short cada barra), sobre MES real, con el fix de barreras ambiguas
YA aplicado en simulation/triple_barrier.py (25-ago-2026: en caso
ambiguo, se asume la PERDIDA).

Metodologia identica a la validacion original: WR empirico = fraccion de
entradas cuyo label resultante es +1.

NOTA: label_triple_barrier() no soporta barreras en ticks fijos
directamente -- su pt_multiplier/sl_multiplier siempre escalan una
volatilidad (ATR o std), nunca un offset constante. _label_fixed_ticks()
de aqui abajo es una copia literal, bar-por-bar, del mismo orden de
resolucion YA CORREGIDO en simulation/triple_barrier.py (SL se chequea
antes que TP) -- no una logica independiente. Si triple_barrier.py
cambia el orden de resolucion otra vez, este archivo debe actualizarse
a mano para seguir reflejando el mismo fix.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")
TICK_SIZE = 0.25
MAX_HOLDING_BARS = 66  # ~sesion completa RTH (8:30-15:00 CT = 78 barras 5min; 66 ~ convencion previa de la sesion)

ROWS = [
    (30, 10),
    (20, 10),
    (10, 10),
    (10, 20),
    (10, 30),
]


def run_row(mes: pd.DataFrame, sl_ticks: int, tp_ticks: int) -> dict:
    n = len(mes)
    sl_pts = sl_ticks * TICK_SIZE
    tp_pts = tp_ticks * TICK_SIZE

    signal_indices = np.arange(0, n - MAX_HOLDING_BARS - 1, 1)
    sides = np.where(np.arange(len(signal_indices)) % 2 == 0, 1, -1)

    longs = signal_indices[sides == 1]
    shorts = signal_indices[sides == -1]

    labels_l = _label_fixed_ticks(mes, longs, tp_pts, sl_pts, MAX_HOLDING_BARS, side=1)
    labels_s = _label_fixed_ticks(mes, shorts, tp_pts, sl_pts, MAX_HOLDING_BARS, side=-1)
    labels = pd.concat([labels_l, labels_s], ignore_index=True)

    n_trades = len(labels)
    wr_long = (labels_l["label"] == 1).mean() if len(labels_l) else float("nan")
    wr_short = (labels_s["label"] == 1).mean() if len(labels_s) else float("nan")
    wr_all = (labels["label"] == 1).mean()

    n_ambig_l = _count_ambiguous(mes, longs, tp_pts, sl_pts, MAX_HOLDING_BARS, side=1)
    n_ambig_s = _count_ambiguous(mes, shorts, tp_pts, sl_pts, MAX_HOLDING_BARS, side=-1)
    pct_bars_ambiguous = (n_ambig_l + n_ambig_s) / n_trades * 100

    return {
        "sl_ticks": sl_ticks, "tp_ticks": tp_ticks,
        "rr": round(tp_ticks / sl_ticks, 3),
        "wr_theoretical": round(sl_ticks / (sl_ticks + tp_ticks), 4),
        "wr_empirical": round(wr_all, 4),
        "bias_emp_minus_theo": round(wr_all - sl_ticks / (sl_ticks + tp_ticks), 4),
        "wr_long": round(wr_long, 4),
        "wr_short": round(wr_short, 4),
        "wr_long_plus_short": round(wr_long + wr_short, 4),
        "pct_bars_ambiguous": round(pct_bars_ambiguous, 2),
        "n_trades": n_trades,
    }


def _count_ambiguous(prices: pd.DataFrame, signal_indices: np.ndarray,
                      tp_pts: float, sl_pts: float, max_holding_bars: int, side: int) -> int:
    """Cuenta barras resolutorias donde TP y SL se tocaron simultaneamente."""
    close = prices["close"].values
    high  = prices["high"].values
    low   = prices["low"].values
    n = len(prices)
    n_ambig = 0

    for entry_i in signal_indices:
        entry_i = int(entry_i)
        if entry_i >= n - 1:
            continue
        entry_price = close[entry_i]
        upper = entry_price + side * tp_pts
        lower = entry_price - side * sl_pts
        exit_i = min(entry_i + max_holding_bars, n - 1)

        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]
            if side == 1:
                win_touch, loss_touch = h >= upper, l <= lower
            else:
                win_touch, loss_touch = l <= upper, h >= lower
            if win_touch or loss_touch:
                if win_touch and loss_touch:
                    n_ambig += 1
                break

    return n_ambig


def _label_fixed_ticks(prices: pd.DataFrame, signal_indices: np.ndarray,
                        tp_pts: float, sl_pts: float, max_holding_bars: int, side: int) -> pd.DataFrame:
    """
    Misma logica de resolucion que label_triple_barrier() (post-fix:
    SL se chequea antes que TP en caso de barra ambigua) pero con
    barreras en TICKS FIJOS en vez de ATR-escaladas.
    """
    close = prices["close"].values
    high  = prices["high"].values
    low   = prices["low"].values
    n = len(prices)
    records = []

    for entry_i in signal_indices:
        entry_i = int(entry_i)
        if entry_i >= n - 1:
            continue
        entry_price = close[entry_i]
        upper = entry_price + side * tp_pts
        lower = entry_price - side * sl_pts
        label = 0
        exit_i = min(entry_i + max_holding_bars, n - 1)

        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]
            if side == 1:
                if l <= lower:
                    label = -1; exit_i = j; break
                if h >= upper:
                    label = 1; exit_i = j; break
            else:
                if h >= lower:
                    label = -1; exit_i = j; break
                if l <= upper:
                    label = 1; exit_i = j; break

        records.append({"entry_idx": entry_i, "label": label})

    return pd.DataFrame(records)


def main():
    mes = pd.read_parquet(MES_PATH)
    print(f"MES: {len(mes):,} barras RTH  {mes.index.min()} -> {mes.index.max()}")
    print(f"max_holding_bars={MAX_HOLDING_BARS}, entrada sin señal alternando long/short cada barra\n")

    results = [run_row(mes, sl, tp) for sl, tp in ROWS]
    df = pd.DataFrame(results)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
