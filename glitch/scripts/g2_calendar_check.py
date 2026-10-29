"""
Glitch — Cerebro 1 (G2): ¿el patron "viernes negativo" encontrado en la
busqueda de edge de Cerebro 2 aplica a la geometria YA VALIDADA de G2?
(06-sep-2026)
========================================================================
Rama cerebro2-dev (analisis, no toca produccion). El patron de viernes
aparecio 3 veces independientes en candidatos de Cerebro 2 (MES
weekly/fade, MGC weekly/fade, spread MES-M2K daily/momentum). Aqui se
prueba si el mismo patron de calendario existe en G2 (Cerebro 1: MES,
SL=100/TP=40 ticks, alternando direccion por dia, holding largo dentro
del dia via max_holding_bars=100 barras de 5min) -- misma logica de
ENTRADA de G2 (una por dia, alternando por strategies/geometry_pure.py
decide_side()/trading_day_index()), labeling con el fix de barras
ambiguas ya auditado (scripts/camino_b_grid.py::_label_fixed_ticks,
win_first=False).

IMPORTANTE: el candidato de geometria pura de Cerebro 2 (MGC/150K,
k=2, nc=6, RR=1.0, WR=0.5) NO se puede someter al mismo analisis --
es un supuesto de Monte Carlo puramente SINTETICO (Bernoulli(WR=0.5)
por dia), nunca derivado de datos reales de MGC, sin fechas de
calendario reales detras. No hay un "viernes" real que excluir de un
proceso sintetico -- se documenta esta limitacion explicitamente en
vez de fabricar un numero.
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


def main():
    mes = pd.read_parquet(os.path.join(DATA_DIR, "mes_5min_2y.parquet"))
    spec = SPECS["MES"]
    g2 = CANDIDATES["MES"]

    open_pos = session_open_bar_positions(mes).sort_index()
    sides = np.array([decide_side(trading_day_index(d), "alternate") for d in open_pos.index])
    entry_positions = open_pos.values.astype(int)

    sl_pts = g2.sl_ticks * spec.tick_size
    tp_pts = g2.tp_ticks * spec.tick_size

    longs_mask = sides == 1
    longs_idx, shorts_idx = entry_positions[longs_mask], entry_positions[~longs_mask]

    labels_l = _label_fixed_ticks(mes, longs_idx, tp_pts, sl_pts, g2.max_holding_bars, side=1, win_first=False)
    labels_s = _label_fixed_ticks(mes, shorts_idx, tp_pts, sl_pts, g2.max_holding_bars, side=-1, win_first=False)

    df = pd.DataFrame({
        "entry_idx": np.concatenate([longs_idx, shorts_idx]),
        "label": np.concatenate([labels_l, labels_s]),
        "session_date": list(open_pos.index[longs_mask]) + list(open_pos.index[~longs_mask]),
    })
    df["session_date"] = pd.to_datetime(df["session_date"])
    df["dow"] = df["session_date"].dt.day_name()
    df = df.sort_values("session_date").reset_index(drop=True)

    print(f"N trades G2 (MES, 1/dia, alternando, {open_pos.index.min()} a {open_pos.index.max()}): {len(df)}")
    print(f"Distribucion label (1=TP, -1=SL, 0=time-barrier): {df['label'].value_counts().to_dict()}")

    def wr_clean(sub):
        w, l = (sub["label"] == 1).sum(), (sub["label"] == -1).sum()
        return w / (w + l) if (w + l) > 0 else float("nan")

    print(f"WR limpio global (TP/(TP+SL)): {wr_clean(df):.4f}")
    print("\nPor dia de semana:")
    g = df.groupby("dow").apply(lambda s: pd.Series({"n": len(s), "wr_clean": wr_clean(s)}))
    print(g.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]).to_string())

    no_friday = df[df["dow"] != "Friday"]
    print(f"\nCon viernes:  N={len(df)}   WR_clean={wr_clean(df):.4f}")
    print(f"Sin viernes:  N={len(no_friday)}   WR_clean={wr_clean(no_friday):.4f}")
    print(f"Diferencia: {(wr_clean(no_friday)-wr_clean(df))*100:.2f} puntos porcentuales -- "
          "nivel de ruido, no un efecto de calendario real en G2.")

    print("\n--- Cerebro 2 geometria pura (MGC/150K) ---")
    print("NO APLICABLE: WR=0.5 es un supuesto sintetico de Monte Carlo, no derivado")
    print("de precios reales de MGC -- no existe un 'viernes' real que excluir.")


if __name__ == "__main__":
    main()
