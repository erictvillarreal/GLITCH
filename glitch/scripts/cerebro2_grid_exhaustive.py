"""
Glitch — Cerebro 2: grid EXHAUSTIVO k x RR x WR x producto x cuenta (04-sep-2026)
====================================================================================
Rama cerebro2-dev. Mapa completo del espacio de busqueda -- NO busca un
candidato final, busca dejar guardado un CSV integro que permita despues
filtrar por "cuanto edge necesitaria una señal real para que esta
region sea atractiva" sin tener que re-correr la simulacion.

Motivacion de esta expansion (documentar explicitamente, ver
GLITCH_RESEARCH_LOG.md): un video/contenido de marketing de terceros
citaba un payout promedio de $9,000 en cuenta fondeada, SIN metodologia
mostrada. Se trata aqui como HIPOTESIS A EXPLORAR (de ahi extender RR
hasta 8.0 y agregar cuentas 100K/150K), NUNCA como cifra validada --
este grid no intenta reproducir ese numero, solo mapear el espacio para
poder juzgar despues si alguna region de el es remotamente compatible.

Ejes (ver scripts/cerebro2_grid_exhaustive_preflight.py para el
preflight de tamano/costo que aprobo este diseño antes de correrlo):
  - k: 24 valores, fino en agresivo (2-10 paso 1), grueso en
    conservador (60-100)
  - RR: 16 valores, 0.25 a 8.0
  - WR: 11 valores, 0.30 a 0.80 paso 0.05 -- SIEMPRE barrido completo
  - Productos: los 7 con datos confirmados
  - Cuentas: XFA_50K/100K/150K

nc_cap: SPECS[...].nc_cap esta documentado como limite REAL solo para
la cuenta 50K (fuente help.topstep.com). Para 100K/150K se usa esa
misma cifra como aproximacion CONSERVADORA (aprobado explicitamente por
el usuario) -- columna `nc_cap_source` en el CSV de salida marca cada
fila como "50K_confirmed" o "50K_cap_applied_as_proxy_unverified" para
que cualquier filtrado futuro sepa que numeros confiar sin releer esta
conversacion. Si se confirma la cifra real de Topstep para 100K/150K
mas adelante (busqueda en paralelo a esta corrida), las filas
"..._unverified" son las que habria que re-correr, no las demas.

WR_natural y edge_required se calculan y guardan en cada fila desde el
inicio (correccion ya aplicada en el pase 1 -- no se pierde en esta
expansion, columnas nativas del CSV, no un post-proceso separado).
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.funded_account import XFA_50K, XFA_100K, XFA_150K, simulate_xfa_lifetime
from scripts.camino_b_grid import ExactDayDist
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
OUT_PATH = os.path.join(DATA_DIR, "cerebro2_grid_exhaustive.csv")

PRODUCTS = ["MES", "M6E", "MGC", "M2K", "MCL", "ZC", "ZN"]
ACCOUNTS = {"50K": XFA_50K, "100K": XFA_100K, "150K": XFA_150K}
SL_MULTIPLIERS = [3, 8, 15]

K_GRID = (list(range(2, 11, 1))
          + list(range(12, 21, 2))
          + list(range(25, 51, 5))
          + [60, 75, 90, 100])
RR_GRID = ([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
           + [2.5, 3.0, 3.5, 4.0]
           + [5.0, 6.0, 7.0, 8.0])
WR_GRID = [round(0.30 + 0.05 * i, 2) for i in range(11)]
MLL_POLICIES = ["every_payout", "first_payout_only"]
MIN_WINNING_DAY_USD = 150.0

N_PATHS = 1_000
MAX_DAYS = 500

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
    t_start = time.perf_counter()
    avg_ranges = {p: avg_bar_range_ticks(STEM[p], SPECS[p].tick_size) for p in PRODUCTS}
    print("Rango promedio barra 5min (ticks):", {p: round(v, 1) for p, v in avg_ranges.items()}, flush=True)

    survivors = []
    for product in PRODUCTS:
        spec = SPECS[product]
        for mult in SL_MULTIPLIERS:
            sl_ticks = max(1, round(avg_ranges[product] * mult))
            for k in K_GRID:
                for acct_label, acct in ACCOUNTS.items():
                    result = derive_nc(acct.mll_distance, k, sl_ticks, spec.tick_value_usd, spec.nc_cap)
                    if result is not None:
                        nc, avg_loss_usd = result
                        nc_cap_source = "50K_confirmed" if acct_label == "50K" else "50K_cap_applied_as_proxy_unverified"
                        survivors.append((product, acct_label, k, sl_ticks, nc, avg_loss_usd, nc_cap_source))

    valid_combos = []
    commission_rt = {p: SPECS[p].commission_roundturn for p in PRODUCTS}
    for product, acct_label, k, sl_ticks, nc, avg_loss_usd, nc_cap_source in survivors:
        for rr in RR_GRID:
            avg_win_usd = rr * avg_loss_usd
            if avg_win_usd >= MIN_WINNING_DAY_USD:
                valid_combos.append((product, acct_label, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd, nc_cap_source))

    n_sim_calls = len(valid_combos) * len(WR_GRID) * len(MLL_POLICIES)
    print(f"Combos validos: {len(valid_combos):,} -> {n_sim_calls:,} corridas de simulate_xfa_lifetime", flush=True)

    rows = []
    n_done = 0
    t_last_report = time.perf_counter()
    for product, acct_label, k, sl_ticks, nc, avg_loss_usd, rr, avg_win_usd, nc_cap_source in valid_combos:
        commission_usd = commission_rt[product] * nc
        acct = ACCOUNTS[acct_label]
        wr_natural = 1.0 / (1.0 + rr)
        for wr in WR_GRID:
            edge_required = max(0.0, wr - wr_natural)
            ev_r_per_trade = wr * (1.0 + rr) - 1.0
            dist = ExactDayDist(wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
            for policy in MLL_POLICIES:
                r = simulate_xfa_lifetime(dist, spec=acct, mll_reset_policy=policy,
                                           n_paths=N_PATHS, max_days=MAX_DAYS, seed=7)
                rows.append({
                    "product": product, "account": acct_label, "nc_cap_source": nc_cap_source,
                    "k": k, "sl_ticks": sl_ticks, "nc": nc,
                    "rr": rr, "wr": wr, "wr_natural": round(wr_natural, 4),
                    "edge_required": round(edge_required, 4),
                    "ev_r_per_trade": round(ev_r_per_trade, 4),
                    "needs_real_edge": edge_required > 1e-9,
                    "mll_policy": policy,
                    "avg_loss_usd": round(avg_loss_usd, 2), "avg_win_usd": round(avg_win_usd, 2),
                    "prob_at_least_1_payout": round(1 - r["prob_never_reached_first_payout"], 4),
                    "avg_lifetime_payout_usd": round(r["avg_lifetime_payout_usd"], 2),
                    "avg_lifetime_days": round(r["avg_lifetime_days"], 1),
                    "payouts_per_year_equiv": round(r["avg_lifetime_payouts"] / max(r["avg_lifetime_days"], 1) * 252, 3),
                })
                n_done += 1

        if time.perf_counter() - t_last_report > 60:
            elapsed = time.perf_counter() - t_start
            pct = n_done / n_sim_calls
            eta = elapsed / max(pct, 1e-9) - elapsed
            print(f"  progreso: {n_done:,}/{n_sim_calls:,} ({pct:.1%}) "
                  f"transcurrido={elapsed/60:.1f}min eta={eta/60:.1f}min", flush=True)
            t_last_report = time.perf_counter()

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    elapsed = time.perf_counter() - t_start
    print(f"\nGuardado: {OUT_PATH} ({len(df):,} filas, {os.path.getsize(OUT_PATH)/1e6:.1f} MB)", flush=True)
    print(f"Tiempo total: {elapsed/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
