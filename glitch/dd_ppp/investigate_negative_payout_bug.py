"""
DD PPP -- investigacion del caso limite encontrado en
core/funded_account.py::simulate_xfa_lifetime()/simulate_xfa_lifetime_dynamic_nc():
la elegibilidad de payout solo chequea winning_days_count >=
winning_days_required -- NUNCA chequea que el BALANCE TOTAL de la
cuenta sea positivo antes de calcular gross = min(balance*payout_pct,
payout_cap). Si el balance sigue siendo negativo en el momento en que
se acumulan 5 dias ganadores (posible tras una perdida grande
temprana, recuperada solo parcialmente), gross sale NEGATIVO y se
resta de lifetime_payout_usd -- un "payout" que en la practica jamas
se solicitaria (nadie pide un retiro con balance negativo), pero que
el motor cuenta igual.

Esta es la MISMA logica de elegibilidad, sin modificar, en
simulate_xfa_lifetime_dynamic_nc() -- el motor EXACTO detras del
$31,257 ya publicado (scripts/cerebro2_cashflow_monte_carlo.py). Se
instrumenta una copia de solo-lectura para:
  (a) contar cuantos eventos de "elegible" ocurren con balance<=0,
  (b) cuantificar el monto total y el impacto en avg/mediana si se
      excluyen (fix conceptual: exigir balance>0 ademas de
      winning_days_count>=required),
  (c) proponer el fix sin implementarlo en el modulo compartido.

Mismos parametros EXACTOS que cerebro2_cashflow_monte_carlo.py::build_xfa_pool
(WR=0.5, per_contract=$364, commission=1.92, nc_designed=6, seed=SEED)
para que esto mida el mismo escenario que produjo el $31,257.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.funded_account import XFA_150K, dynamic_nc_for_balance, simulate_xfa_lifetime_dynamic_nc
from strategies.geometry_pure import SPECS

WR = 0.50
SL_TICKS = TP_TICKS = 364
TICK_VALUE = SPECS["MGC"].tick_value_usd
COMMISSION_RT = SPECS["MGC"].commission_roundturn
PER_CONTRACT = SL_TICKS * TICK_VALUE
NC_DESIGNED = 6
PRODUCT_CODE = "MGC"
SEED = 7
N_PATHS = 50_000   # mismo que build_xfa_pool() original
MAX_DAYS = 756      # mismo que build_xfa_pool() original (pool de episodios XFA)


def simulate_instrumented(mll_reset_policy: str, apply_fix: bool, n_paths=N_PATHS, max_days=MAX_DAYS, seed=SEED):
    """Copia de solo-lectura de simulate_xfa_lifetime_dynamic_nc(), MISMA
    logica exacta, instrumentada para contar/cuantificar payouts con
    balance<=0 en el momento de elegibilidad. apply_fix=True agrega
    balance>0 a la condicion de elegibilidad (el fix propuesto, NO
    aplicado al modulo compartido)."""
    rng = np.random.default_rng(seed)
    is_win = rng.random((n_paths, max_days)) < WR

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
    has_had_first_payout = np.zeros(n_paths, dtype=bool)

    n_negative_balance_events = 0
    n_total_payout_events = 0
    negative_balance_dollars = 0.0
    negative_balance_event_detail = []  # (day, balance_al_momento) muestra chica para inspeccion

    for day in range(max_days):
        active_at_start = alive
        nc_today = dynamic_nc_for_balance(balance, mll_distance, PRODUCT_CODE)
        nc_today = np.minimum(nc_today, NC_DESIGNED)
        net_win = nc_today * (PER_CONTRACT - COMMISSION_RT)
        net_loss = -nc_today * (PER_CONTRACT + COMMISSION_RT)
        day_pnl = np.where(is_win[:, day], net_win, net_loss)

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
        if apply_fix:
            eligible = eligible & (balance > 0)  # FIX PROPUESTO -- no aplicado al modulo compartido

        if eligible.any():
            n_total_payout_events += int(eligible.sum())
            neg_mask = eligible & (balance <= 0)
            n_this_round_negative = int(neg_mask.sum())
            if n_this_round_negative:
                n_negative_balance_events += n_this_round_negative
                gross_neg = np.minimum(balance[neg_mask] * payout_pct, payout_cap)
                negative_balance_dollars += float((gross_neg * split).sum())
                if len(negative_balance_event_detail) < 5:
                    negative_balance_event_detail.append((day, float(balance[neg_mask][0])))

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
            lifetime_payouts = lifetime_payouts.copy()
            lifetime_payouts[eligible] += 1
            lifetime_payout_usd = lifetime_payout_usd.copy()
            lifetime_payout_usd[eligible] += trader_take

    return {
        "lifetime_payout_usd": lifetime_payout_usd,
        "lifetime_payouts": lifetime_payouts,
        "n_total_payout_events": n_total_payout_events,
        "n_negative_balance_events": n_negative_balance_events,
        "negative_balance_dollars": negative_balance_dollars,
        "negative_balance_event_detail": negative_balance_event_detail,
    }


if __name__ == "__main__":
    print("Validando la copia instrumentada (apply_fix=False) contra simulate_xfa_lifetime_dynamic_nc() real...")
    real = simulate_xfa_lifetime_dynamic_nc(
        WR, PER_CONTRACT, PER_CONTRACT, COMMISSION_RT, spec=XFA_150K, product_code=PRODUCT_CODE,
        nc_designed=NC_DESIGNED, mll_reset_policy="every_payout", n_paths=N_PATHS, max_days=MAX_DAYS, seed=SEED,
    )
    mine = simulate_instrumented(mll_reset_policy="every_payout", apply_fix=False)
    match = (abs(real["avg_lifetime_payout_usd"] - mine["lifetime_payout_usd"].mean()) < 0.01 and
             abs(real["median_lifetime_payout_usd"] - np.median(mine["lifetime_payout_usd"])) < 0.01)
    print(f"  real avg=${real['avg_lifetime_payout_usd']:.4f}  mio avg=${mine['lifetime_payout_usd'].mean():.4f}")
    print(f"  {'COINCIDE -- validado.' if match else 'NO COINCIDE -- revisar.'}\n")
    if not match:
        sys.exit(1)

    print("=" * 100)
    print(f"Escenario EXACTO del $31,257 publicado (WR=0.5, nc_designed=6, seed={SEED}, n_paths={N_PATHS}, max_days={MAX_DAYS})")
    print("=" * 100)

    for policy in ("every_payout", "first_payout_only"):
        print(f"\n--- mll_reset_policy={policy} ---")
        without_fix = simulate_instrumented(mll_reset_policy=policy, apply_fix=False)
        with_fix = simulate_instrumented(mll_reset_policy=policy, apply_fix=True)

        pct_negative = without_fix["n_negative_balance_events"] / without_fix["n_total_payout_events"] * 100 if without_fix["n_total_payout_events"] else 0
        print(f"  Total de EVENTOS de payout (todas las trayectorias, todos los dias): {without_fix['n_total_payout_events']:,}")
        print(f"  De esos, con balance<=0 en el momento de elegibilidad: {without_fix['n_negative_balance_events']:,} "
              f"({pct_negative:.2f}%)")
        print(f"  Monto TOTAL 'pagado' sobre balance negativo (suma cruda, todas las trayectorias): "
              f"${without_fix['negative_balance_dollars']:,.2f}")
        if without_fix["negative_balance_event_detail"]:
            print(f"  Ejemplos (dia, balance en ese momento): {without_fix['negative_balance_event_detail']}")

        usd_sin_fix = without_fix["lifetime_payout_usd"]
        usd_con_fix = with_fix["lifetime_payout_usd"]
        print(f"\n  SIN fix (como esta hoy, produjo el $31,257):  avg=${usd_sin_fix.mean():,.2f}  median=${np.median(usd_sin_fix):,.2f}")
        print(f"  CON fix (balance>0 exigido tambien):           avg=${usd_con_fix.mean():,.2f}  median=${np.median(usd_con_fix):,.2f}")
        delta_avg = usd_con_fix.mean() - usd_sin_fix.mean()
        delta_median = np.median(usd_con_fix) - np.median(usd_sin_fix)
        print(f"  Diferencia: avg {delta_avg:+.2f} ({delta_avg/usd_sin_fix.mean()*100 if usd_sin_fix.mean() else 0:+.2f}%)  "
              f"median {delta_median:+.2f}")
