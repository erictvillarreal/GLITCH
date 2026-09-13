"""
Glitch — Cerebro 2: primer pase barato del grid (MES + M6E) (01-sep-2026)
============================================================================
Rama cerebro2-dev. Diseño desde cero, NO heredado de G2/Cerebro 1 -- ver
GLITCH_RESEARCH_LOG.md para la discusion completa. Este script:

1. Deriva nc a partir de k (perdidas consecutivas que la cuenta debe
   sobrevivir) para cada (producto, SL_ticks candidato), filtrando
   ANTES de simular cualquier combinacion donde nc redondee a 0 o
   exceda el limite real de Topstep -- reporta cuantas combinaciones
   sobreviven vs. se descartan, como parte del diseño, no como
   sorpresa.
2. Para las combinaciones que sobreviven Y cumplen avg_win_usd >= $150
   (umbral de dia ganador de la XFA), corre el grid k x RR x WR,
   AMBAS politicas de MLL, reportando la forma del tradeoff -- NO un
   candidato final.

MES + M6E unicamente en este pase (mismo tick_value=$1.25/tick en
ambos -- aisla el efecto de volatilidad real/nc_cap del efecto de
granularidad de tick, que seria un factor de confusion si se mezclara
con 6E full-size u otro producto de tick_value distinto).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.funded_account import XFA_50K, simulate_xfa_lifetime
from scripts.camino_b_grid import ExactDayDist
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")

PRODUCTS = ["MES", "M6E"]
K_GRID = [5, 10, 20, 50]
SL_MULTIPLIERS = [3, 8, 15]  # x rango promedio de barra 5min, mismo criterio que Camino B
RR_GRID = [0.5, 1.0, 1.5, 2.0, 3.0]
WR_GRID = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
MLL_POLICIES = ["every_payout", "first_payout_only"]
MIN_WINNING_DAY_USD = 150.0

N_PATHS = 1_000    # pase barato -- reducido del default de 10k para exploracion rapida
MAX_DAYS = 500     # ~2 años habiles -- suficiente para ver la forma, no el horizonte final de 756


def avg_bar_range_ticks(stem: str, tick_size: float) -> float:
    df = pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet"))
    return float((df["high"] - df["low"]).mean() / tick_size)


def derive_nc(mll_distance: float, k: int, sl_ticks: int, tick_value: float, nc_cap: int):
    """Devuelve (nc, avg_loss_usd_actual) o None si nc redondea a 0 o excede el cap."""
    target = mll_distance / k
    nc = round(target / (sl_ticks * tick_value))
    if nc < 1 or nc > nc_cap:
        return None
    return nc, sl_ticks * tick_value * nc


def main():
    stems = {"MES": "mes", "M6E": "m6e"}
    avg_ranges = {p: avg_bar_range_ticks(stems[p], SPECS[p].tick_size) for p in PRODUCTS}
    print("Rango promedio de barra 5min (ticks):", {p: round(v, 1) for p, v in avg_ranges.items()})
    print(f"XFA-50K mll_distance=${XFA_50K.mll_distance:,.0f}\n")

    # ── Paso 1 del reporte pedido: filtro de nc por (k, producto, SL_ticks) ──
    survivors = []  # (product, k, sl_ticks, nc, avg_loss_usd)
    n_total = 0
    n_discarded_nc = 0

    print("=" * 100)
    print("FILTRO DE nc (Ajuste 1 pedido) -- ANTES de gastar computo en simulacion")
    print("=" * 100)
    for product in PRODUCTS:
        spec = SPECS[product]
        for mult in SL_MULTIPLIERS:
            sl_ticks = max(1, round(avg_ranges[product] * mult))
            for k in K_GRID:
                n_total += 1
                result = derive_nc(XFA_50K.mll_distance, k, sl_ticks, spec.tick_value_usd, spec.nc_cap)
                if result is None:
                    n_discarded_nc += 1
                    print(f"  DESCARTADO: {product} SL={sl_ticks}t (x{mult}) k={k} -> "
                          f"nc redondea fuera de [1,{spec.nc_cap}]")
                    continue
                nc, avg_loss_usd = result
                survivors.append((product, k, sl_ticks, nc, avg_loss_usd))

    print(f"\nTotal combinaciones (producto x SL_mult x k): {n_total}")
    print(f"Descartadas por nc invalido: {n_discarded_nc}")
    print(f"Sobrevivientes: {len(survivors)}\n")

    # ── Filtro adicional: avg_win_usd >= $150 para cada RR candidato ──
    valid_combos = []  # (product, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd)
    n_discarded_150 = 0
    for product, k, sl_ticks, nc, avg_loss_usd in survivors:
        for rr in RR_GRID:
            avg_win_usd = rr * avg_loss_usd
            if avg_win_usd < MIN_WINNING_DAY_USD:
                n_discarded_150 += 1
                continue
            valid_combos.append((product, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd))

    print(f"Combinaciones (sobreviviente x RR): {len(survivors) * len(RR_GRID)}")
    print(f"Descartadas por avg_win_usd < ${MIN_WINNING_DAY_USD:.0f}: {n_discarded_150}")
    print(f"Validas para simular: {len(valid_combos)}")
    print(f"x {len(WR_GRID)} valores de WR x {len(MLL_POLICIES)} politicas de MLL = "
          f"{len(valid_combos) * len(WR_GRID) * len(MLL_POLICIES)} corridas de simulate_xfa_lifetime\n")

    # ── Paso 2: grid completo sobre las combinaciones validas ──
    commission_rt = {"MES": SPECS["MES"].commission_roundturn, "M6E": SPECS["M6E"].commission_roundturn}
    rows = []
    for product, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd in valid_combos:
        commission_usd = commission_rt[product] * nc
        for wr in WR_GRID:
            dist = ExactDayDist(wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
            for policy in MLL_POLICIES:
                r = simulate_xfa_lifetime(dist, spec=XFA_50K, mll_reset_policy=policy,
                                           n_paths=N_PATHS, max_days=MAX_DAYS, seed=7)
                rows.append({
                    "product": product, "k": k, "sl_ticks": sl_ticks, "nc": nc,
                    "rr": rr, "wr": wr, "mll_policy": policy,
                    "avg_loss_usd": round(avg_loss_usd, 2), "avg_win_usd": round(avg_win_usd, 2),
                    "prob_at_least_1_payout": round(1 - r["prob_never_reached_first_payout"], 4),
                    "avg_lifetime_payout_usd": round(r["avg_lifetime_payout_usd"], 2),
                    "avg_lifetime_days": round(r["avg_lifetime_days"], 1),
                    "payouts_per_year_equiv": round(r["avg_lifetime_payouts"] / max(r["avg_lifetime_days"], 1) * 252, 3),
                })

    df = pd.DataFrame(rows)
    out_path = os.path.join(DATA_DIR, "cerebro2_grid_pass1.csv")
    df.to_csv(out_path, index=False)
    print(f"Guardado: {out_path}\n")

    # ── Reporte de la FORMA del tradeoff: para cada (producto, k), tabla RR x WR
    #     de avg_lifetime_payout_usd, promediando ambas politicas de MLL (ya
    #     confirmamos que divergen poco cuando el payout total es bajo -- se
    #     reportan por separado en el CSV para quien quiera el detalle) ──
    print("=" * 100)
    print("FORMA DEL TRADEOFF -- avg_lifetime_payout_usd, promedio de ambas politicas de MLL")
    print("(filas=RR, columnas=WR) -- '-' = combinacion no valida (nc o umbral $150)")
    print("=" * 100)
    for product in PRODUCTS:
        for k in K_GRID:
            sub = df[(df["product"] == product) & (df["k"] == k)]
            if sub.empty:
                continue
            pivot = sub.groupby(["rr", "wr"])["avg_lifetime_payout_usd"].mean().unstack("wr")
            print(f"\n--- {product}, k={k} (sl_ticks disponibles: {sorted(sub['sl_ticks'].unique())}) ---")
            print(pivot.round(0).to_string())


if __name__ == "__main__":
    main()
