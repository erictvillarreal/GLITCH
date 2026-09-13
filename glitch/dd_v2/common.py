"""
DD v2 -- helpers compartidos: construccion de la secuencia real,
cronologica, de UN trade por dia (no el bar-walk denso de
measure_wr_bracket) para G2 (MES) y MGC_XFA (MGC), usando exactamente
la misma logica de entrada que scheduler/geometry_scheduler.py en
produccion (decide_side/trading_day_index) -- mismo patron ya usado en
scripts/g2_calendar_check.py, generalizado a cualquier producto/config.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.combo2d import session_open_bar_positions
from strategies.geometry_pure import SPECS, CANDIDATES, trading_day_index, decide_side
from scripts.camino_b_grid import _label_fixed_ticks

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")
MGC_PATH = os.path.join(DATA_DIR, "mgc_5min_2y_corrected_window.parquet")  # ventana corregida, ver scripts/fetch_mgc_correct_window.py


def build_daily_trades(parquet_path: str, product_key: str, sl_ticks: int, tp_ticks: int,
                        max_holding_bars: int, direction: str = "alternate") -> pd.DataFrame:
    """Un trade por dia de sesion RTH real, cronologico, misma logica de
    entrada que produccion. Devuelve columnas: session_date, side, label
    (1=TP, -1=SL, 0=time-exit)."""
    prices = pd.read_parquet(parquet_path)
    spec = SPECS[product_key]
    open_pos = session_open_bar_positions(prices).sort_index()
    sides = np.array([decide_side(trading_day_index(d), direction) for d in open_pos.index])
    entry_positions = open_pos.values.astype(int)

    sl_pts = sl_ticks * spec.tick_size
    tp_pts = tp_ticks * spec.tick_size

    longs_mask = sides == 1
    longs_idx, shorts_idx = entry_positions[longs_mask], entry_positions[~longs_mask]

    labels_l = _label_fixed_ticks(prices, longs_idx, tp_pts, sl_pts, max_holding_bars, side=1, win_first=False)
    labels_s = _label_fixed_ticks(prices, shorts_idx, tp_pts, sl_pts, max_holding_bars, side=-1, win_first=False)

    df = pd.DataFrame({
        "session_date": list(open_pos.index[longs_mask]) + list(open_pos.index[~longs_mask]),
        "side": np.concatenate([np.ones(longs_mask.sum(), dtype=int), -np.ones((~longs_mask).sum(), dtype=int)]),
        "label": np.concatenate([labels_l, labels_s]),
    })
    df["session_date"] = pd.to_datetime(df["session_date"])
    return df.sort_values("session_date").reset_index(drop=True)


def wr_conditional(df: pd.DataFrame) -> float:
    """TP/(TP+SL), excluyendo time-exits del denominador -- la metrica
    correcta para comparar contra un WR teorico de gambler's ruin (ver
    scripts/validate_mgc_wr_empirical.py para el porque)."""
    w = (df["label"] == 1).sum()
    l = (df["label"] == -1).sum()
    return w / (w + l) if (w + l) > 0 else float("nan")


G2 = CANDIDATES["MES"]
MGC_XFA = CANDIDATES["MGC_XFA_150K"]


if __name__ == "__main__":
    g2_df = build_daily_trades(MES_PATH, "MES", G2.sl_ticks, G2.tp_ticks, G2.max_holding_bars, G2.direction)
    mgc_df = build_daily_trades(MGC_PATH, "MGC", MGC_XFA.sl_ticks, MGC_XFA.tp_ticks, MGC_XFA.max_holding_bars, MGC_XFA.direction)

    print(f"G2 (MES, SL={G2.sl_ticks}/TP={G2.tp_ticks}): {len(g2_df)} trades, "
          f"{g2_df['session_date'].min().date()} -> {g2_df['session_date'].max().date()}")
    print(f"  distribucion label: {g2_df['label'].value_counts().to_dict()}")
    print(f"  WR condicional: {wr_conditional(g2_df):.4f}")
    print()
    print(f"MGC_XFA (MGC, SL={MGC_XFA.sl_ticks}/TP={MGC_XFA.tp_ticks}): {len(mgc_df)} trades, "
          f"{mgc_df['session_date'].min().date()} -> {mgc_df['session_date'].max().date()}")
    print(f"  distribucion label: {mgc_df['label'].value_counts().to_dict()}")
    print(f"  WR condicional: {wr_conditional(mgc_df):.4f}")
