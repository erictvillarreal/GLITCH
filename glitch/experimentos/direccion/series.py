"""Serie diaria ajustada por roll de MES y utilidades de la Parte B (ver PREREGISTRO.md, Enmienda 1)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "preservacion"))
from daydata import DEFAULT_PARQUET, load_days  # noqa: E402

WARMUP = 50


def daily_series(path=DEFAULT_PARQUET):
    d = pd.read_parquet(path).tz_convert("America/Chicago")
    d["date"] = d.index.date
    g = d.groupby("date")
    df = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(), "contract": g.contract.last()})
    prev_c = df.close.shift(); same = df.contract == df.contract.shift()
    chg = np.where(same, df.close - prev_c, df.close - df.open)           # el dia del roll: solo el movimiento dentro del dia
    chg[0] = 0.0
    df["adj_close"] = df.close.iloc[0] + np.cumsum(chg)
    tr = np.maximum(df.high - df.low, np.maximum((df.high - prev_c).abs(), (df.low - prev_c).abs()))
    df["tr"] = np.where(same, tr, df.high - df.low)
    df["roll"] = ~same
    return df


def add_indicators(df):
    """Indicadores con la informacion del dia (cierre de ESE dia); la regla del dia d usa la fila d-1."""
    out = df.copy()
    out["sma20"] = out.adj_close.rolling(20).mean(); out["sma50"] = out.adj_close.rolling(50).mean()
    out["atr14"] = out.tr.rolling(14).mean()
    return out


def eval_index(df, dd):
    """Indices (posicion en df) de los dias evaluables: dia completo en dd y posicion >= WARMUP."""
    pos = {d: i for i, d in enumerate(df.index)}
    return [pos[d] for d in dd.dates if pos[d] >= WARMUP]


def dominant_window(df, idx, width=60):
    """Ventana de `width` dias de evaluacion consecutivos con mayor |delta del cierre ajustado| (solo precio)."""
    best = None
    for s in range(0, len(idx) - width + 1):
        i0, i1 = idx[s], idx[s + width - 1]
        move = df.adj_close.iloc[i1] - df.adj_close.iloc[i0 - 1]
        if best is None or abs(move) > abs(best[0]):
            best = (move, s, s + width - 1, df.index[i0], df.index[i1])
    return best
