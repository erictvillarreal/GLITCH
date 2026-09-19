"""
DD PPP -- reporte puramente descriptivo: percentiles p10/p25/p50/p75/p90
de payout total a 1 año, 1 cuenta, para las 10 combinaciones ya
generadas en dd_ppp/run_experiment.py -- mismo motor
(simulate_xfa_lifetime), mismos PnL empiricos, sin re-simular el
bar-walk (reusa dd_ppp/bar_walk.py::run_all_trades tal cual).

simulate_xfa_lifetime() no expone el array crudo de payouts (solo
media/mediana/p10-p90 agregados) -- _simulate_xfa_lifetime_raw() de
abajo es una copia de solo-lectura de su misma logica vectorizada
exacta (core/funded_account.py, lineas ~325-391), unicamente para
poder calcular p25/p75 tambien. Validada contra la funcion real antes
de usarla (ver bloque de validacion en __main__).

SIN analisis de confiabilidad estadistica aqui a proposito -- eso ya
quedo documentado por separado en GLITCH_RESEARCH_LOG.md. Esta tabla
es solo los numeros de resultado.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.funded_account import XFA_150K, simulate_xfa_lifetime
from dd_ppp.bar_walk import run_all_trades
from dd_ppp.run_experiment import EmpiricalDist, THRESHOLDS, VARIANTS, N_TRAJECTORIES_XFA, N_DAYS_1Y


def _simulate_xfa_lifetime_raw(dist, spec=XFA_150K, mll_reset_policy="every_payout",
                                n_paths=30_000, max_days=252, seed=7) -> np.ndarray:
    """Copia de solo-lectura de simulate_xfa_lifetime() -- misma logica
    exacta, solo para exponer el array crudo de payouts y calcular
    p25/p75 (la funcion original solo devuelve p10/p90 agregados)."""
    rng = np.random.default_rng(seed)
    pnls = dist.sample(n_paths * max_days, rng).reshape(n_paths, max_days)

    mll_distance = spec.mll_distance
    floor_lock_level = spec.floor_lock_level
    min_winning_day_usd = spec.min_winning_day_usd
    winning_days_required = spec.winning_days_required
    payout_pct = spec.payout_pct_of_balance
    payout_cap = spec.payout_cap_usd
    split = spec.profit_split_trader

    balance = np.zeros(n_paths)
    mll_floor = np.full(n_paths, spec.floor_start)
    alive = np.ones(n_paths, dtype=bool)
    winning_days_count = np.zeros(n_paths, dtype=np.int64)
    lifetime_payout_usd = np.zeros(n_paths)
    has_had_first_payout = np.zeros(n_paths, dtype=bool)

    for day in range(max_days):
        active_at_start = alive
        day_pnl = pnls[:, day]
        balance = np.where(active_at_start, balance + day_pnl, balance)

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
            else:
                reset_now = eligible & (~has_had_first_payout)
                if reset_now.any():
                    mll_floor = mll_floor.copy()
                    mll_floor[reset_now] = 0.0
            has_had_first_payout = has_had_first_payout.copy()
            has_had_first_payout[eligible] = True
            winning_days_count = winning_days_count.copy()
            winning_days_count[eligible] = 0
            lifetime_payout_usd = lifetime_payout_usd.copy()
            lifetime_payout_usd[eligible] += trader_take

    return lifetime_payout_usd


def percentiles(usd_arr: np.ndarray) -> dict:
    p = np.percentile(usd_arr, [10, 25, 50, 75, 90])
    return {"p10": p[0], "p25": p[1], "p50": p[2], "p75": p[3], "p90": p[4]}


if __name__ == "__main__":
    print("Validando _simulate_xfa_lifetime_raw contra simulate_xfa_lifetime() real (misma seed)...")
    base_pnl = run_all_trades(threshold=None, variant=None)["pnl_per_contract_total"].values
    dist = EmpiricalDist(base_pnl, "baseline")
    real = simulate_xfa_lifetime(dist, spec=XFA_150K, n_paths=N_TRAJECTORIES_XFA, max_days=N_DAYS_1Y, seed=7)
    raw = _simulate_xfa_lifetime_raw(dist, spec=XFA_150K, n_paths=N_TRAJECTORIES_XFA, max_days=N_DAYS_1Y, seed=7)
    match = (abs(real["median_lifetime_payout_usd"] - np.median(raw)) < 0.01 and
             abs(real["avg_lifetime_payout_usd"] - raw.mean()) < 0.01)
    print(f"  real median=${real['median_lifetime_payout_usd']:.4f}  raw median=${np.median(raw):.4f}")
    print(f"  real avg=${real['avg_lifetime_payout_usd']:.4f}  raw avg=${raw.mean():.4f}")
    print(f"  {'COINCIDE -- validado.' if match else 'NO COINCIDE -- revisar.'}\n")
    if not match:
        sys.exit(1)

    rows = []

    p = percentiles(raw)
    rows.append({"umbral": "—", "variante": "baseline (este experimento)", **p})

    for variant_label, variant_code in VARIANTS.items():
        for threshold in THRESHOLDS:
            df = run_all_trades(threshold=threshold, variant=variant_code)
            pnl = df["pnl_per_contract_total"].values
            d = EmpiricalDist(pnl, f"{variant_label}_{threshold}")
            usd = _simulate_xfa_lifetime_raw(d, spec=XFA_150K, n_paths=N_TRAJECTORIES_XFA, max_days=N_DAYS_1Y, seed=7)
            p = percentiles(usd)
            rows.append({"umbral": f"${threshold}", "variante": variant_label, **p})

    out = pd.DataFrame(rows)
    print("=" * 100)
    print("Payout TOTAL esperado a 1 año, 1 cuenta MGC_XFA_150K ($) -- percentiles")
    print("(referencia externa ya publicada, otra metodologia -- ver nota en el research log: mediana $31,257)")
    print("=" * 100)
    for _, r in out.iterrows():
        print(f"{r['variante']:30s} umbral={r['umbral']:>6s}   "
              f"p10=${r['p10']:>9,.0f}  p25=${r['p25']:>9,.0f}  p50=${r['p50']:>9,.0f}  "
              f"p75=${r['p75']:>9,.0f}  p90=${r['p90']:>9,.0f}")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppp_percentiles.csv")
    out.to_csv(out_path, index=False)
    print(f"\nGuardado: {out_path}")
