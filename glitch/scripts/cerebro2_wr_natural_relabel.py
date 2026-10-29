"""
Glitch — Cerebro 2: re-etiquetado del grid Pass-1 contra WR natural (01-sep-2026)
==================================================================================
Rama cerebro2-dev. NO corre ninguna simulacion nueva -- lee el CSV ya
generado por cerebro2_grid_pass1.py y lo re-etiqueta.

Motivo: en el diseño de cerebro2_grid_pass1.py, WR se barre como
PARAMETRO LIBRE (ExactDayDist.wr, Bernoulli independiente) mientras que
avg_win_usd/avg_loss_usd (de donde sale RR) se derivan de sl_ticks/nc.
Los dos ejes NUNCA se conectaron entre si -- no hay ningun calculo de
gambler's ruin en el pipeline. Esto es exactamente el mismo error de
encuadre que casi se cometio con Camino B al principio de la sesion:
confundir "geometria que no requiere señal" con "cualquier WR que se
le ocurra al barrido".

Formula (misma convencion gambler's ruin ya usada para Camino B, ver
GLITCH_RESEARCH_LOG.md): para un proceso SIN sesgo con barreras de
toque simple a distancia SL (perdida) y TP (ganancia), usando el mismo
numero de contratos en ambos lados (nc identico, mismo tick_value --
confirmado en cerebro2_grid_pass1.py: avg_win_usd = rr * avg_loss_usd
con el mismo nc):

    WR_natural = SL / (SL + TP) = 1 / (1 + RR)      donde RR = TP/SL

Cualquier WR barrido POR ENCIMA de WR_natural para esa fila de RR
requiere edge real de magnitud (WR - WR_natural) en probabilidad, que
en R-multiples equivale a EV_R = WR*(1+RR) - 1 por trade (0 exactamente
en WR_natural).
"""
from __future__ import annotations
import os

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
IN_PATH = os.path.join(DATA_DIR, "cerebro2_grid_pass1.csv")
OUT_PATH = os.path.join(DATA_DIR, "cerebro2_grid_pass1_relabeled.csv")


def main():
    df = pd.read_csv(IN_PATH)

    df["wr_natural"] = 1.0 / (1.0 + df["rr"])
    df["edge_required"] = (df["wr"] - df["wr_natural"]).clip(lower=0.0)
    df["ev_r_per_trade"] = df["wr"] * (1.0 + df["rr"]) - 1.0
    df["needs_real_edge"] = df["edge_required"] > 1e-9
    df.to_csv(OUT_PATH, index=False)

    print("=" * 100)
    print("WR NATURAL POR RR (gambler's ruin, proceso sin sesgo, WR_natural = 1/(1+RR))")
    print("=" * 100)
    for rr in sorted(df["rr"].unique()):
        wr_nat = 1.0 / (1.0 + rr)
        print(f"  RR={rr:.1f}  ->  WR_natural = {wr_nat:.1%}")

    print()
    print("=" * 100)
    print("RE-ETIQUETADO: para cada RR, que valores de WR barridos son geometria pura")
    print("(WR <= WR_natural, sin edge) vs. cuales requieren edge real (WR > WR_natural)")
    print("=" * 100)
    wr_grid = sorted(df["wr"].unique())
    for rr in sorted(df["rr"].unique()):
        wr_nat = 1.0 / (1.0 + rr)
        row_labels = []
        for wr in wr_grid:
            if wr <= wr_nat + 1e-9:
                row_labels.append(f"{wr:.2f}=PURA")
            else:
                edge = wr - wr_nat
                row_labels.append(f"{wr:.2f}=EDGE+{edge:.1%}")
        print(f"\nRR={rr:.1f} (WR_natural={wr_nat:.1%}):")
        print("  " + "  ".join(row_labels))

    print()
    print("=" * 100)
    print("TABLA avg_lifetime_payout_usd (MES, promedio de politicas MLL, promedio de k)")
    print("re-anotada: [P] = geometria pura (WR<=WR_natural), [E+x%] = requiere edge real")
    print("=" * 100)
    for product in sorted(df["product"].unique()):
        sub = df[df["product"] == product]
        pivot_val = sub.groupby(["rr", "wr"])["avg_lifetime_payout_usd"].mean().unstack("wr")
        pivot_edge = sub.groupby(["rr", "wr"])["edge_required"].mean().unstack("wr")
        print(f"\n--- {product} ---")
        header = "rr\\wr  " + "  ".join(f"{c:>14.2f}" for c in pivot_val.columns)
        print(header)
        for rr in pivot_val.index:
            cells = []
            for wr in pivot_val.columns:
                val = pivot_val.loc[rr, wr]
                edge = pivot_edge.loc[rr, wr]
                if pd.isna(val):
                    cells.append(f"{'-':>14s}")
                elif edge <= 1e-9:
                    cells.append(f"{'$'+format(val,',.0f')+'[P]':>14s}")
                else:
                    cells.append(f"{'$'+format(val,',.0f')+f'[E+{edge:.0%}]':>14s}")
            print(f"{rr:<6.1f} " + "  ".join(cells))

    print()
    print("=" * 100)
    print("RESUMEN: cuadrante antes marcado 'prometedor, sin señal' -- costo real en edge")
    print("=" * 100)
    quadrant = df[(df["rr"] >= 1.5) & (df["wr"] >= 0.50)]
    n_total = len(quadrant)
    n_pure = (quadrant["edge_required"] <= 1e-9).sum()
    n_edge = n_total - n_pure
    print(f"Celdas con RR>=1.5 y WR>=0.50: {n_total} filas de simulacion")
    print(f"  -> Geometria pura (sin edge): {n_pure}")
    print(f"  -> Requieren edge real: {n_edge}")
    if n_edge > 0:
        e = quadrant[quadrant["edge_required"] > 1e-9]
        print(f"  -> Edge requerido en ese subconjunto: min={e['edge_required'].min():.1%} "
              f"max={e['edge_required'].max():.1%} promedio={e['edge_required'].mean():.1%}")
        print(f"  -> EV_R (R-multiples) requerido: min={e['ev_r_per_trade'].min():.3f}R "
              f"max={e['ev_r_per_trade'].max():.3f}R promedio={e['ev_r_per_trade'].mean():.3f}R")

    print(f"\nGuardado: {OUT_PATH}")


if __name__ == "__main__":
    main()
