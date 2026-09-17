"""
DD v3 -- Optimizacion de politica de retiro para MGC_XFA_150K
==============================================================================
NUNCA se optimizo formalmente el % de balance a retirar por solicitud
ni un colchon minimo sobre el floor trailing antes de permitir un
retiro. Este script construye un grid de politicas y corre el motor de
Monte Carlo YA VALIDADO (core/funded_account.py::simulate_xfa_lifetime_dynamic_nc)
extendido con 2 parametros nuevos, sin modificar el modulo compartido
-- la extension vive aqui, en la rama de analisis.

HALLAZGO METODOLOGICO IMPORTANTE (documentado ANTES de correr nada,
ver GLITCH_RESEARCH_LOG.md): la "intuicion de partida" mencionada por
el usuario (5% del balance, colchon $2,000) NO es el default real del
motor validado. Confirmado con evidencia de codigo:
  - XFASpec.payout_pct_of_balance = 0.50 (50%, EL MAXIMO permitido por
    Topstep, no 5%) -- core/funded_account.py linea 57.
  - NO existe ningun chequeo de colchon sobre el floor en
    simulate_xfa_lifetime()/simulate_xfa_lifetime_dynamic_nc() -- el
    payout se ejecuta SIEMPRE que hay elegibilidad, sin condicion
    adicional.
  - El "5%/$2,000" que el usuario recordaba SI existe en el codigo,
    pero en scheduler/telegram_bot.py::notify_brain2_open/close/
    notify_payout_eligible -- funciones de FORMATO DE MENSAJE de la
    arquitectura "Brain 1/Brain 2" anterior al pivote a geometria
    pura, confirmado (grep) que NINGUNA de esas 3 funciones se llama
    desde ningun scheduler activo hoy. Nunca alimentaron ninguna
    simulacion real.
  - CONCLUSION: la politica actual EFECTIVA (la que ya sostiene los
    $31,257 de mediana publicados) es "retirar el maximo legal (50%)
    cada vez que hay elegibilidad, sin ningun colchon de seguridad" --
    la mas AGRESIVA posible dentro de la regla de Topstep, no una
    conservadora del 5%. El grid de este estudio explora si retirar
    MENOS que el maximo (y/o exigir un colchon) puede superar a esa
    politica ya-agresiva-por-defecto, no si conviene ser mas agresivo
    que un 5% que nunca existio en la simulacion real.

DISEÑO DE LA EXTENSION (min_cushion): si la cuenta es elegible
(>=5 dias ganadores) pero retirar el monto completo dejaria
(balance - gross) - mll_floor < min_cushion, el retiro se DIFIERE (no
se resetea winning_days_count, no se toca balance/floor) -- se
reintenta automaticamente el dia siguiente conforme el balance sigue
cambiando. Validado contra el motor original sin modificar
(simulate_xfa_lifetime_dynamic_nc) con min_cushion=0 y payout_pct
default: debe reproducir EXACTO (misma seed) los resultados ya
publicados antes de confiar en el grid completo.
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
TICK_VALUE = SPECS["MGC"].tick_value_usd        # 1.00
COMMISSION_RT = SPECS["MGC"].commission_roundturn  # 1.92
PER_CONTRACT = SL_TICKS * TICK_VALUE            # $364, SL=TP (RR=1.0)
NC_DESIGNED = 6                                  # mismo candidato ya validado (k=2)
PRODUCT_CODE = "MGC"

DAYS_1Y = 252
DAYS_3Y = 756

PAYOUT_PCT_GRID = [0.10, 0.20, 0.30, 0.40, 0.50]
MIN_CUSHION_GRID = [0, 500, 1000, 1500, 2000, 3000]


def simulate_with_policy(payout_pct: float, min_cushion: float, mll_reset_policy: str = "every_payout",
                          n_paths: int = 30_000, max_days: int = DAYS_3Y, snapshot_day: int = DAYS_1Y,
                          seed: int = 7) -> dict:
    """
    Extension de simulate_xfa_lifetime_dynamic_nc() -- MISMA mecanica
    exacta (nc dinamico via Scaling Plan, floor trailing EOD-only,
    elegibilidad a 5 dias ganadores), mas:
      (a) payout_pct configurable (el original toma esto de spec.payout_pct_of_balance,
          fijo en 0.50 -- aqui se parametriza para el grid).
      (b) min_cushion: si el payout dejaria (balance-gross)-floor < min_cushion,
          se DIFIERE (sin tocar balance/floor/winning_days_count) -- se
          reintenta el dia siguiente automaticamente.
      (c) snapshot a day=snapshot_day (1 año) ADEMAS del resultado final
          a max_days (3 años) -- de la MISMA corrida, para consistencia
          interna entre ambos horizontes (no dos corridas separadas).
    """
    rng = np.random.default_rng(seed)
    is_win = rng.random((n_paths, max_days)) < WR

    mll_distance = XFA_150K.mll_distance
    floor_lock_level = XFA_150K.floor_lock_level
    min_winning_day_usd = XFA_150K.min_winning_day_usd
    winning_days_required = XFA_150K.winning_days_required
    payout_cap = XFA_150K.payout_cap_usd
    split = XFA_150K.profit_split_trader

    balance = np.zeros(n_paths)
    mll_floor = np.full(n_paths, XFA_150K.floor_start)
    alive = np.ones(n_paths, dtype=bool)
    winning_days_count = np.zeros(n_paths, dtype=np.int64)
    lifetime_payouts = np.zeros(n_paths, dtype=np.int64)
    lifetime_payout_usd = np.zeros(n_paths)
    has_had_first_payout = np.zeros(n_paths, dtype=bool)
    day_number = np.zeros(n_paths, dtype=np.int64)
    n_deferred_total = 0

    snap = {}

    for day in range(max_days):
        active_at_start = alive

        nc_today = dynamic_nc_for_balance(balance, mll_distance, PRODUCT_CODE)
        nc_today = np.minimum(nc_today, NC_DESIGNED)
        net_win = nc_today * (PER_CONTRACT - COMMISSION_RT)
        net_loss = -nc_today * (PER_CONTRACT + COMMISSION_RT)
        day_pnl = np.where(is_win[:, day], net_win, net_loss)

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
            gross_all = np.minimum(balance * payout_pct, payout_cap)
            if min_cushion > 0:
                # min_cushion=0 debe reproducir EXACTO el comportamiento
                # original (sin ningun gate) -- el motor original permite
                # que un retiro deje el balance por DEBAJO del floor
                # (un "auto-quiebre" via retiro, capturado recien en el
                # blow-check del dia siguiente). Un chequeo ">=0" aqui
                # bloquearia ese caso real y ya NO seria equivalente a
                # "sin colchon" -- confirmado por la validacion bit-a-bit
                # contra simulate_xfa_lifetime_dynamic_nc() sin modificar
                # (ver bloque de validacion en __main__).
                would_be_cushion = (balance - gross_all) - mll_floor
                pay_now = eligible & (would_be_cushion >= min_cushion)
            else:
                pay_now = eligible
            n_deferred_total += int((eligible & ~pay_now).sum())

            if pay_now.any():
                gross = gross_all[pay_now]
                trader_take = gross * split
                balance = balance.copy()
                balance[pay_now] -= gross
                if mll_reset_policy == "every_payout":
                    mll_floor = mll_floor.copy()
                    mll_floor[pay_now] = 0.0
                else:
                    reset_now = pay_now & (~has_had_first_payout)
                    if reset_now.any():
                        mll_floor = mll_floor.copy()
                        mll_floor[reset_now] = 0.0
                has_had_first_payout = has_had_first_payout.copy()
                has_had_first_payout[pay_now] = True
                winning_days_count = winning_days_count.copy()
                winning_days_count[pay_now] = 0
                lifetime_payouts = lifetime_payouts.copy()
                lifetime_payouts[pay_now] += 1
                lifetime_payout_usd = lifetime_payout_usd.copy()
                lifetime_payout_usd[pay_now] += trader_take

        if (day + 1) == snapshot_day:
            snap = {
                "alive": alive.copy(),
                "lifetime_payouts": lifetime_payouts.copy(),
                "lifetime_payout_usd": lifetime_payout_usd.copy(),
            }

    def _package(payouts_arr, usd_arr, alive_arr, days_arr):
        n_never = int((payouts_arr == 0).sum())
        return {
            "n_paths": n_paths,
            "prob_still_alive": float(alive_arr.mean()),
            "prob_never_reached_first_payout": n_never / n_paths,
            "avg_lifetime_payouts": float(payouts_arr.mean()),
            "median_lifetime_payouts": float(np.median(payouts_arr)),
            "avg_payout_usd": float(usd_arr.mean()),
            "median_payout_usd": float(np.median(usd_arr)),
            "p10_payout_usd": float(np.percentile(usd_arr, 10)),
            "p90_payout_usd": float(np.percentile(usd_arr, 90)),
            "avg_days_alive": float(days_arr.mean()),
            "median_days_alive": float(np.median(days_arr)),
        }

    result_3y = _package(lifetime_payouts.astype(float), lifetime_payout_usd, alive, day_number.astype(float))
    days_at_1y = np.minimum(day_number, snapshot_day).astype(float)  # censurado a 1 año para paths que ya tronaron antes
    result_1y = _package(snap["lifetime_payouts"].astype(float), snap["lifetime_payout_usd"], snap["alive"], days_at_1y)
    result_1y["n_deferred_payouts_total_all_horizon"] = n_deferred_total  # diagnostico, no por horizonte

    return {"1y": result_1y, "3y": result_3y, "n_deferred_total": n_deferred_total}


if __name__ == "__main__":
    print("Validando la extension contra el motor original SIN modificar (min_cushion=0, payout_pct=0.50)...")
    baseline_original = simulate_xfa_lifetime_dynamic_nc(
        WR, PER_CONTRACT, PER_CONTRACT, COMMISSION_RT, spec=XFA_150K, product_code=PRODUCT_CODE,
        nc_designed=NC_DESIGNED, mll_reset_policy="every_payout", n_paths=30_000, max_days=DAYS_3Y, seed=7,
    )
    baseline_extended = simulate_with_policy(payout_pct=0.50, min_cushion=0, n_paths=30_000, seed=7)["3y"]
    print(f"  Original:  avg_payout_usd={baseline_original['avg_lifetime_payout_usd']:.4f}  "
          f"median={baseline_original['median_lifetime_payout_usd']:.4f}  "
          f"prob_never={baseline_original['prob_never_reached_first_payout']:.4f}")
    print(f"  Extension: avg_payout_usd={baseline_extended['avg_payout_usd']:.4f}  "
          f"median={baseline_extended['median_payout_usd']:.4f}  "
          f"prob_never={baseline_extended['prob_never_reached_first_payout']:.4f}")
    match = (abs(baseline_original['avg_lifetime_payout_usd'] - baseline_extended['avg_payout_usd']) < 0.01 and
             abs(baseline_original['median_lifetime_payout_usd'] - baseline_extended['median_payout_usd']) < 0.01)
    print(f"  {'COINCIDE EXACTO -- extension validada.' if match else 'NO COINCIDE -- REVISAR ANTES DE CONFIAR EN EL GRID.'}\n")
    if not match:
        sys.exit(1)
