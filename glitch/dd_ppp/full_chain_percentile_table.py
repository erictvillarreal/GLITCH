"""
DD PPP -- Tarea 1: percentiles de payout total a 1 año usando la
CADENA COMPLETA (scripts/cerebro2_cashflow_monte_carlo.py::run_cashflow_simulation,
importada SIN modificar) -- la misma que produjo el $31,257 ya
publicado, para comparacion manzanas-con-manzanas real, no
simulate_xfa_lifetime() aislado (ver correccion metodologica pedida
por el usuario tras la primera tabla).

LIMITACION METODOLOGICA DECLARADA (no escondida): el $31,257 original
usa nc DINAMICO (simulate_xfa_lifetime_dynamic_nc, capped en
nc_designed=6 por el Scaling Plan real segun balance). El bar-walk de
este experimento (dd_ppp/bar_walk.py) calcula el PnL de cada trade
HISTORICO REAL a nc FIJO=6 -- no hay forma de reconciliar esto con nc
dinamico sin re-correr el bar-walk con un balance simulado
path-por-path (arquitectura fundamentalmente distinta: el bar-walk es
UNA secuencia determinista atada a precios reales; el Monte Carlo de
balance necesita miles de trayectorias, cada una con su propio balance
evolutivo). Se usa simulate_xfa_lifetime() (dist-based, nc fijo) para
la etapa XFA de la cadena en vez de la version dynamic_nc -- mas
cercano al $31,257 que la tabla anterior (que ni siquiera encadenaba
Combine+XFA), pero todavia no 100% identico. Declarado explicitamente.

NO se aplica el fix del bug de balance negativo aqui -- se usa la
MISMA logica exacta (con el bug) que produjo el $31,257, para que la
comparacion sea contra ese numero tal como esta hoy, no contra una
version hipotetica corregida (eso se reporta por separado).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.prop_firm import TOPSTEP_150K
from core.funded_account import XFA_150K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from scripts.cerebro2_cashflow_monte_carlo import run_cashflow_simulation
from dd_ppp.bar_walk import run_all_trades
from dd_ppp.run_experiment import EmpiricalDist, THRESHOLDS, VARIANTS

N_PATHS_COMBINE = 100_000
MAX_DAYS_COMBINE = 15
N_PATHS_XFA_POOL = 50_000   # mismo que build_xfa_pool() original
MAX_DAYS_XFA_POOL = 756      # mismo que build_xfa_pool() original
N_TRAJECTORIES_CASHFLOW = 20_000  # mismo que run_cashflow_simulation() default
HORIZON_DAYS = 365
SEED = 7


def build_combine_pool_empirical(pnl_array: np.ndarray, label: str) -> dict:
    dist = EmpiricalDist(pnl_array, label)
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_150K, n_paths=N_PATHS_COMBINE, max_days=MAX_DAYS_COMBINE, seed=42)
    r = sim.run()
    return {
        "pass_rate": r.pass_rate,
        "pass_days_pool": r.pass_days,
        "blown_days_pool": r.blown_days,
        "fee_monthly": TOPSTEP_150K.monthly_fee,
        "fee_activation": TOPSTEP_150K.activation_fee,
    }


def build_xfa_pool_empirical(pnl_array: np.ndarray, label: str, mll_reset_policy: str,
                              n_paths=N_PATHS_XFA_POOL, max_days=MAX_DAYS_XFA_POOL, seed=SEED) -> dict:
    """Misma logica exacta de simulate_xfa_lifetime() (core/funded_account.py,
    SIN el fix del bug de balance negativo -- ver nota del modulo),
    exponiendo tambien lifetime_payouts y day_number crudos (la funcion
    real no los expone, solo agregados) para construir el pool de
    episodios que run_cashflow_simulation() espera."""
    dist = EmpiricalDist(pnl_array, label)
    rng = np.random.default_rng(seed)
    pnls = dist.sample(n_paths * max_days, rng).reshape(n_paths, max_days)

    mll_distance = XFA_150K.mll_distance
    floor_lock_level = XFA_150K.floor_lock_level
    min_winning_day_usd = XFA_150K.min_winning_day_usd
    winning_days_required = XFA_150K.winning_days_required
    payout_pct = XFA_150K.payout_pct_of_balance
    payout_cap = XFA_150K.payout_cap_usd
    split = XFA_150K.profit_split_trader

    balance = np.zeros(n_paths)
    mll_floor = np.full(n_paths, XFA_150K.floor_start)
    alive = np.ones(n_paths, dtype=bool)
    winning_days_count = np.zeros(n_paths, dtype=np.int64)
    lifetime_payouts = np.zeros(n_paths, dtype=np.int64)
    lifetime_payout_usd = np.zeros(n_paths)
    day_number = np.zeros(n_paths, dtype=np.int64)

    for day in range(max_days):
        active_at_start = alive
        day_pnl = pnls[:, day]
        balance = np.where(active_at_start, balance + day_pnl, balance)
        day_number = np.where(active_at_start, day + 1, day_number)

        new_floor_candidate = balance - mll_distance
        floor_should_update = active_at_start & (new_floor_candidate > mll_floor)
        mll_floor = np.where(floor_should_update, np.minimum(new_floor_candidate, floor_lock_level), mll_floor)

        newly_blown = active_at_start & (balance <= mll_floor)
        alive = alive & ~newly_blown

        still_active_today = active_at_start & ~newly_blown
        counted = still_active_today & (day_pnl >= min_winning_day_usd)
        winning_days_count = np.where(counted, winning_days_count + 1, winning_days_count)

        eligible = still_active_today & (winning_days_count >= winning_days_required)
        if eligible.any():
            gross = np.minimum(balance[eligible] * payout_pct, payout_cap)
            trader_take = gross * split
            balance = balance.copy()
            balance[eligible] -= gross
            if mll_reset_policy == "every_payout":
                mll_floor = mll_floor.copy()
                mll_floor[eligible] = 0.0
            winning_days_count = winning_days_count.copy()
            winning_days_count[eligible] = 0
            lifetime_payouts = lifetime_payouts.copy()
            lifetime_payouts[eligible] += 1
            lifetime_payout_usd = lifetime_payout_usd.copy()
            lifetime_payout_usd[eligible] += trader_take

    return {
        "payout_usd_pool": lifetime_payout_usd,
        "n_payouts_pool": lifetime_payouts.astype(float),
        "days_pool": day_number.astype(float),
    }


def percentiles(arr):
    p = np.percentile(arr, [10, 25, 50, 75, 90])
    return {"p10": p[0], "p25": p[1], "p50": p[2], "p75": p[3], "p90": p[4]}


def run_full_chain(pnl_array: np.ndarray, label: str) -> dict:
    combine_pool = build_combine_pool_empirical(pnl_array, label)
    xfa_pool = build_xfa_pool_empirical(pnl_array, label, mll_reset_policy="every_payout")
    result = run_cashflow_simulation(combine_pool, xfa_pool, n_trajectories=N_TRAJECTORIES_CASHFLOW,
                                      horizon_days=HORIZON_DAYS, seed=SEED)
    return percentiles(result["total_payout"])


if __name__ == "__main__":
    print("Validando build_combine_pool_empirical/build_xfa_pool_empirical con WR=0.5 sintetico "
          "contra el $31,257 ya publicado (misma logica, misma distribucion binaria)...")
    # Reconstruye la MISMA distribucion binaria WR=0.5/avg_win=avg_loss=$2,184 del script original,
    # como bootstrap empirico de 2 valores -- debe reproducir ~$31,257 si el chaining esta bien.
    synthetic_binary = np.array([2172.48] * 5000 + [-2195.52] * 5000)  # WR=50% exacto, mismos $ que el original
    r = run_full_chain(synthetic_binary, "validacion_wr50_sintetico")
    print(f"  p50 reproducido: ${r['p50']:,.0f}  (referencia: $31,257)")
    print(f"  {'Razonablemente cerca -- diferencias esperadas por el pool XFA fijo-nc vs dinamico-nc, no un error.' if abs(r['p50']-31257)/31257 < 0.15 else 'DIFERENCIA GRANDE -- revisar antes de confiar en la tabla.'}\n")

    rows = []
    base_pnl = run_all_trades(threshold=None, variant=None)["pnl_per_contract_total"].values
    r = run_full_chain(base_pnl, "baseline")
    rows.append({"variante": "baseline (este experimento)", "umbral": "—", **r})
    print(f"baseline: p50=${r['p50']:,.0f}")

    for variant_label, variant_code in VARIANTS.items():
        for threshold in THRESHOLDS:
            pnl = run_all_trades(threshold=threshold, variant=variant_code)["pnl_per_contract_total"].values
            r = run_full_chain(pnl, f"{variant_label}_{threshold}")
            rows.append({"variante": variant_label, "umbral": f"${threshold}", **r})
            print(f"{variant_label} umbral=${threshold}: p50=${r['p50']:,.0f}")

    out = pd.DataFrame(rows)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppp_full_chain_percentiles.csv")
    out.to_csv(out_path, index=False)

    print(f"\n{'='*100}\nPayout TOTAL a 1 año, 1 cuenta -- CADENA COMPLETA (comparable a $31,257)\n{'='*100}")
    for _, r in out.iterrows():
        print(f"{r['variante']:30s} umbral={r['umbral']:>6s}   "
              f"p10=${r['p10']:>9,.0f}  p25=${r['p25']:>9,.0f}  p50=${r['p50']:>9,.0f}  "
              f"p75=${r['p75']:>9,.0f}  p90=${r['p90']:>9,.0f}")
    print(f"\nGuardado: {out_path}")
