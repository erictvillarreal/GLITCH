"""
Glitch — Cerebro 2: Monte Carlo de flujo de caja real, 2 etapas
encadenadas (Combine -> XFA), horizonte de 365 dias (06-sep-2026)
========================================================================
Rama cerebro2-dev. El usuario pidio un Monte Carlo de cash flow real
(no aritmetica lineal de "81 intentos") sobre el candidato de geometria
pura de Cerebro 2 (MGC/150K, k=2, nc=6, SL=TP=364 ticks, WR=0.5).

GAP encontrado y resuelto ANTES de construir esto (ver
GLITCH_RESEARCH_LOG.md): los numeros previamente citados ($2,169
esperado, 46.2% prob de payout) son SOLO de la fase XFA
(simulate_xfa_lifetime_dynamic_nc) -- asumen que la cuenta YA esta
fondeada desde $0. Nunca se habia corrido esta geometria especifica a
traves de la fase COMBINE (la evaluacion que hay que pasar, pagando la
fee, ANTES de llegar a la XFA). Decision del usuario: construir el
modelo de 2 etapas completo, no una version simplificada que asuma que
pagar la fee garantiza pasar.

Etapa 1 (Combine, TOPSTEP_150K via simulation/monte_carlo.py, mismo
motor ya usado y auditado para G2): distribucion diaria WR=50%,
avg_win=avg_loss=$2,184 (SL=TP=364 ticks x $1.00/tick x 6 contratos),
menos comision ($1.92 x 6 = $11.52/dia). RESULTADO CENTRAL: pass_rate
solo 47.2% -- muy por debajo del ~81.4% de G2. Este candidato fue
diseñado para sobrevivir en XFA (bajo nc, muchas pocas perdidas
consecutivas), NO para pasar el Combine rapido -- son objetivos de
diseño distintos y este resultado lo confirma.

Etapa 2 (XFA, core/funded_account.py::simulate_xfa_lifetime_dynamic_nc,
ya validada con nc dinamico): SI se pasa el Combine, se paga la
activation fee y se entra a la XFA -- 46.2% prob de al menos 1 payout,
$2,169 esperado de por vida antes de tronar (~10.5 dias promedio,
politica every_payout).

Encadenamiento: pool grande de resultados de cada etapa (ya
vectorizados), luego un Monte Carlo secuencial de 365 "dias de
calendario" por trayectoria, muestreando CON REEMPLAZO de esos pools
en cada evento -- estadisticamente equivalente a resimular desde cero
cada vez, mucho mas rapido.

SUPUESTO EXPLICITO (declarado, no escondido): el payout total de una
XFA se acredita al FINAL del ciclo de vida de esa XFA (no distribuido
en el momento exacto de cada pago dentro del ciclo, que no esta
disponible a este nivel de agregacion) -- esto es CONSERVADOR para el
calculo de colchon de capital (retrasa el ingreso de caja lo mas
posible dentro de cada episodio, nunca lo adelanta).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_150K
from core.funded_account import XFA_150K, simulate_xfa_lifetime_dynamic_nc
from strategies.geometry_pure import SPECS

# ── Candidato ────────────────────────────────────────────────────────────
NC = 6
SL_TICKS = TP_TICKS = 364
TICK_VALUE = SPECS["MGC"].tick_value_usd       # 1.00
COMMISSION_RT = SPECS["MGC"].commission_roundturn  # 1.92
WR = 0.5

N_TRAJECTORIES = 20_000
HORIZON_DAYS = 365
SEED = 7


def build_combine_pool(n_paths=200_000, max_days=250, seed=SEED):
    gross = SL_TICKS * TICK_VALUE * NC
    commission = COMMISSION_RT * NC
    dist = DailyReturnDist(win_rate=WR, avg_win=gross - commission, avg_loss=gross + commission, name="MGC_150K_candidate")
    print("Combine dist:", dist.describe())
    sim = TopstepMonteCarloSimulator(dist, spec=TOPSTEP_150K, n_paths=n_paths, max_days=max_days, seed=seed)
    r = sim.run()
    print(f"Combine pass_rate={r.pass_rate:.4f}  blow_rate={r.blow_rate:.4f}  "
          f"avg_pass_days={r.avg_pass_days:.2f}  avg_blown_days={r.avg_blown_days:.2f}  "
          f"n_alive_sin_resolver={r.n_alive}")
    return {
        "pass_rate": r.pass_rate,
        "pass_days_pool": r.pass_days,     # dias-a-resolucion, solo paths que pasaron
        "blown_days_pool": r.blown_days,   # dias-a-resolucion, solo paths que tronaron
        "fee_monthly": TOPSTEP_150K.monthly_fee,
        "fee_activation": TOPSTEP_150K.activation_fee,
    }


def build_xfa_pool(mll_reset_policy, n_paths=50_000, max_days=756, seed=SEED):
    per_contract = SL_TICKS * TICK_VALUE  # = TP tambien, RR=1.0
    r = simulate_xfa_lifetime_dynamic_nc(
        WR, per_contract, per_contract, COMMISSION_RT, spec=XFA_150K, product_code="MGC",
        nc_designed=NC, mll_reset_policy=mll_reset_policy, n_paths=n_paths, max_days=max_days,
        seed=seed, return_raw=True,
    )
    print(f"XFA ({mll_reset_policy}): prob>=1 payout={1-r['prob_never_reached_first_payout']:.4f}  "
          f"avg_payout_usd={r['avg_lifetime_payout_usd']:.2f}  avg_days={r['avg_lifetime_days']:.2f}")
    return {
        "payout_usd_pool": r["raw_lifetime_payout_usd"],
        "n_payouts_pool": r["raw_lifetime_payouts"],
        "days_pool": r["raw_lifetime_days"],
    }


def run_cashflow_simulation(combine_pool, xfa_pool, n_trajectories=N_TRAJECTORIES, horizon_days=HORIZON_DAYS, seed=SEED):
    rng = np.random.default_rng(seed)
    n_pass_pool, n_blown_pool = len(combine_pool["pass_days_pool"]), len(combine_pool["blown_days_pool"])
    n_xfa_pool = len(xfa_pool["payout_usd_pool"])
    fee_monthly, fee_activation = combine_pool["fee_monthly"], combine_pool["fee_activation"]
    pass_rate = combine_pool["pass_rate"]

    total_payouts, n_combine_attempts_l, n_combine_passes_l = [], [], []
    n_xfa_payouts_l, min_cash_l = [], []
    all_cycle_lengths = []  # para la pregunta de "dias por N intentos completos"

    for _ in range(n_trajectories):
        days_elapsed, cash, min_cash = 0.0, 0.0, 0.0
        n_attempts = n_passes = n_xfa_payouts = 0
        total_payout = 0.0

        while days_elapsed < horizon_days:
            cycle_start_days = days_elapsed
            cash -= fee_monthly
            n_attempts += 1
            min_cash = min(min_cash, cash)

            passed = rng.random() < pass_rate
            if passed:
                days = combine_pool["pass_days_pool"][rng.integers(0, n_pass_pool)]
            else:
                days = combine_pool["blown_days_pool"][rng.integers(0, n_blown_pool)]
            days_elapsed += days

            if passed:
                n_passes += 1
                cash -= fee_activation
                min_cash = min(min_cash, cash)

                idx = rng.integers(0, n_xfa_pool)
                episode_payout = xfa_pool["payout_usd_pool"][idx]
                episode_days = xfa_pool["days_pool"][idx]
                episode_n_payouts = xfa_pool["n_payouts_pool"][idx]

                days_elapsed += episode_days
                cash += episode_payout
                total_payout += episode_payout
                n_xfa_payouts += episode_n_payouts

            all_cycle_lengths.append(days_elapsed - cycle_start_days)

        total_payouts.append(total_payout)
        n_combine_attempts_l.append(n_attempts)
        n_combine_passes_l.append(n_passes)
        n_xfa_payouts_l.append(n_xfa_payouts)
        min_cash_l.append(min_cash)

    return {
        "total_payout": np.array(total_payouts),
        "n_combine_attempts": np.array(n_combine_attempts_l),
        "n_combine_passes": np.array(n_combine_passes_l),
        "n_xfa_payouts": np.array(n_xfa_payouts_l),
        "capital_colchon": -np.array(min_cash_l),
        "avg_cycle_length_days": float(np.mean(all_cycle_lengths)),
    }


def percentile_table(arr, label):
    ps = [10, 25, 50, 75, 90]
    vals = np.percentile(arr, ps)
    print(f"{label:35s}" + "".join(f"  p{p}={v:>10,.1f}" for p, v in zip(ps, vals)) + f"   mean={arr.mean():>10,.1f}")


def main():
    combine_pool = build_combine_pool()
    print()
    for policy in ("every_payout", "first_payout_only"):
        xfa_pool = build_xfa_pool(policy)
        print(f"\n{'='*100}\nCASH FLOW 365 DIAS -- politica MLL: {policy}\n{'='*100}")
        result = run_cashflow_simulation(combine_pool, xfa_pool)

        percentile_table(result["total_payout"], "Payout total acumulado ($)")
        percentile_table(result["n_combine_attempts"], "N intentos de Combine")
        percentile_table(result["n_combine_passes"], "N veces que llego a XFA")
        percentile_table(result["n_xfa_payouts"], "N payouts XFA exitosos")
        percentile_table(result["capital_colchon"], "Capital colchon maximo necesario ($)")
        print(f"Duracion promedio de un ciclo completo (Combine + XFA si aplica): {result['avg_cycle_length_days']:.2f} dias")

        for n_target in (30, 50):
            days_needed = n_target * result["avg_cycle_length_days"]
            print(f"Dias reales para acumular {n_target} intentos completos: ~{days_needed:.0f} dias "
                  f"(~{days_needed/365:.2f} años)")

        # Cola izquierda: P(necesitar >=k intentos de Combine consecutivos sin NINGUN payout)
        p_success_per_attempt = combine_pool["pass_rate"] * (1 - (xfa_pool["n_payouts_pool"] == 0).mean())
        print(f"\nP(un intento cualquiera termina en >=1 payout) = pass_rate x prob(>=1 payout | paso) = {p_success_per_attempt:.4f}")
        for k in (5, 10):
            p_need_k_or_more = (1 - p_success_per_attempt) ** (k - 1)
            print(f"P(se necesitan >= {k} intentos consecutivos SIN ningun payout antes del primer exito) = {p_need_k_or_more:.4f}")


if __name__ == "__main__":
    main()
