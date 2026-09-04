"""
Glitch — Cerebro 2: preflight de tamano/costo para el grid exhaustivo (04-sep-2026)
======================================================================================
Rama cerebro2-dev. NO corre ninguna simulacion completa -- calcula
exactamente cuantas combinaciones sobreviven los filtros de nc y de
avg_win_usd>=$150 para el grid EXHAUSTIVO pedido, y bench-marca el
costo real de una corrida de simulate_xfa_lifetime con los parametros
de produccion (N_PATHS, MAX_DAYS) para extrapolar el tiempo total.

Ejes (ver GLITCH_RESEARCH_LOG.md para la justificacion de cada rango):
  - k: fino en el rango agresivo, grueso en el conservador (24 valores)
  - RR: extendido a 8.0, fino en <=2.0, grueso arriba (16 valores)
  - WR: 0.30-0.80 paso 0.05 (11 valores) -- SIEMPRE el barrido completo
  - Productos: los 7 con datos confirmados (SL_MULTIPLIERS sin cambio,
    3 valores, mismo criterio que Camino B -- no es un eje que el
    usuario pidio expandir)
  - Cuentas: XFA_50K/100K/150K (3) -- OJO: nc_cap en SPECS esta citado
    para la cuenta 50K unicamente (ver docstring de ProductSpec). No
    hay una fuente confirmada en este repo de nc_cap especifico para
    100K/150K -- este preflight usa el nc_cap de 50K como aproximacion
    CONSERVADORA para las 3 cuentas (nunca sobreestima cuantos
    contratos se pueden operar). Reportado explicitamente, no
    silenciado -- si Topstep permite mas contratos en cuentas mas
    grandes, el grid de 100K/150K aqui sera pesimista, no optimista.
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.funded_account import XFA_50K, XFA_100K, XFA_150K, simulate_xfa_lifetime
from scripts.camino_b_grid import ExactDayDist
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")

PRODUCTS = ["MES", "M6E", "MGC", "M2K", "MCL", "ZC", "ZN"]
ACCOUNTS = {"50K": XFA_50K, "100K": XFA_100K, "150K": XFA_150K}
SL_MULTIPLIERS = [3, 8, 15]

K_GRID = (list(range(2, 11, 1))          # 2..10 paso 1   (9)
          + list(range(12, 21, 2))        # 12..20 paso 2  (5)
          + list(range(25, 51, 5))        # 25..50 paso 5  (6)
          + [60, 75, 90, 100])            # grueso         (4)
RR_GRID = ([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]   # paso 0.25 (8)
           + [2.5, 3.0, 3.5, 4.0]                          # paso 0.5  (4)
           + [5.0, 6.0, 7.0, 8.0])                          # paso 1.0  (4)
WR_GRID = [round(0.30 + 0.05 * i, 2) for i in range(11)]   # 0.30..0.80 (11)
MLL_POLICIES = ["every_payout", "first_payout_only"]
MIN_WINNING_DAY_USD = 150.0

STEM = {"MES": "mes", "M6E": "m6e", "MGC": "mgc", "M2K": "m2k", "MCL": "mcl", "ZC": "zc", "ZN": "zn"}


def avg_bar_range_ticks(stem: str, tick_size: float) -> float:
    df = pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet"))
    return float((df["high"] - df["low"]).mean() / tick_size)


def derive_nc(mll_distance, k, sl_ticks, tick_value, nc_cap):
    target = mll_distance / k
    nc = round(target / (sl_ticks * tick_value))
    if nc < 1 or nc > nc_cap:
        return None
    return nc, sl_ticks * tick_value * nc


def main():
    print(f"Ejes: productos={len(PRODUCTS)} x SL_mult={len(SL_MULTIPLIERS)} x k={len(K_GRID)} "
          f"x RR={len(RR_GRID)} x WR={len(WR_GRID)} x cuentas={len(ACCOUNTS)} x politicas={len(MLL_POLICIES)}")
    raw_total = len(PRODUCTS) * len(SL_MULTIPLIERS) * len(K_GRID) * len(RR_GRID) * len(WR_GRID) * len(ACCOUNTS) * len(MLL_POLICIES)
    print(f"Grid crudo (sin filtros): {raw_total:,}\n")

    avg_ranges = {p: avg_bar_range_ticks(STEM[p], SPECS[p].tick_size) for p in PRODUCTS}
    print("Rango promedio barra 5min (ticks):", {p: round(v, 1) for p, v in avg_ranges.items()})

    # ── Etapa 1: filtro de nc, por (producto, SL_mult, k, cuenta) ──
    survivors = []  # (product, acct_label, k, sl_ticks, nc, avg_loss_usd)
    n_stage1_total = 0
    for product in PRODUCTS:
        spec = SPECS[product]
        for mult in SL_MULTIPLIERS:
            sl_ticks = max(1, round(avg_ranges[product] * mult))
            for k in K_GRID:
                for acct_label, acct in ACCOUNTS.items():
                    n_stage1_total += 1
                    result = derive_nc(acct.mll_distance, k, sl_ticks, spec.tick_value_usd, spec.nc_cap)
                    if result is not None:
                        nc, avg_loss_usd = result
                        survivors.append((product, acct_label, k, sl_ticks, nc, avg_loss_usd))

    print(f"\nEtapa 1 (nc filter): {n_stage1_total:,} combos (producto x SL_mult x k x cuenta) "
          f"-> {len(survivors):,} sobreviven ({len(survivors)/n_stage1_total:.1%})")

    # ── Etapa 2: filtro avg_win_usd >= $150, por RR ──
    valid_combos = []
    n_stage2_total = len(survivors) * len(RR_GRID)
    for product, acct_label, k, sl_ticks, nc, avg_loss_usd in survivors:
        for rr in RR_GRID:
            avg_win_usd = rr * avg_loss_usd
            if avg_win_usd >= MIN_WINNING_DAY_USD:
                valid_combos.append((product, acct_label, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd))

    print(f"Etapa 2 ($150 filter): {n_stage2_total:,} combos (sobreviviente x RR) "
          f"-> {len(valid_combos):,} validas ({len(valid_combos)/n_stage2_total:.1%})")

    n_sim_calls = len(valid_combos) * len(WR_GRID) * len(MLL_POLICIES)
    print(f"\nTotal corridas de simulate_xfa_lifetime necesarias: "
          f"{len(valid_combos):,} combos x {len(WR_GRID)} WR x {len(MLL_POLICIES)} politicas "
          f"= {n_sim_calls:,}")

    # ── Benchmark real: tiempo de 1 corrida con params de produccion ──
    N_PATHS = 1_000
    MAX_DAYS = 500
    dist = ExactDayDist(0.5, 1000.0, 800.0, 5.0, trades_per_day=1)
    N_BENCH = 20
    t0 = time.perf_counter()
    for i in range(N_BENCH):
        simulate_xfa_lifetime(dist, spec=XFA_50K, mll_reset_policy="every_payout",
                               n_paths=N_PATHS, max_days=MAX_DAYS, seed=i)
    elapsed = time.perf_counter() - t0
    per_call = elapsed / N_BENCH
    print(f"\nBenchmark: {N_BENCH} corridas reales (N_PATHS={N_PATHS}, MAX_DAYS={MAX_DAYS}) "
          f"tomaron {elapsed:.2f}s -> {per_call*1000:.1f}ms/corrida")

    est_total_sec = n_sim_calls * per_call
    print(f"\nESTIMADO TOTAL: {n_sim_calls:,} corridas x {per_call*1000:.1f}ms "
          f"= {est_total_sec:,.0f}s = {est_total_sec/60:,.1f}min = {est_total_sec/3600:,.2f}h")

    # Tamano estimado del CSV de salida
    bytes_per_row = 200  # estimado conservador, columnas numericas + producto/cuenta/politica
    est_csv_mb = n_sim_calls * bytes_per_row / 1e6
    print(f"CSV estimado: ~{est_csv_mb:,.1f} MB ({n_sim_calls:,} filas)")


if __name__ == "__main__":
    main()
