"""
DD v2 -- Test 1: Stress test de friccion real (comision+slippage
escalonada 0/0.25/0.5/1.0/2.0 ticks POR LADO -- entrada y salida cada
una paga esa friccion, entonces el costo total por trade es
2 x friccion_ticks x tick_value x nc, ADEMAS de la comision real ya
modelada).

G2: recalcula pass_rate_15d / combines_por_ano (TopstepMonteCarloSimulator,
motor ya auditado, sin reimplementar).
MGC_XFA: recalcula prob(>=1 payout) / avg_lifetime_payout_usd /
payouts_per_year_equiv (simulate_xfa_lifetime_dynamic_nc, motor ya
auditado, sin reimplementar) -- la friccion entra como comission_roundturn
mas alta, WR/SL/TP en ticks no cambian (la friccion no mueve donde
toca la barrera, solo el costo de ejecutar cada leg).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prop_firm import TOPSTEP_50K, TOPSTEP_150K
from core.funded_account import XFA_150K, simulate_xfa_lifetime_dynamic_nc
from simulation.monte_carlo import TopstepMonteCarloSimulator
from scripts.camino_b_grid import ExactDayDist, N_PATHS, MAX_DAYS, TRADING_DAYS_PER_YEAR
from strategies.geometry_pure import SPECS
from dd_v2.common import G2, MGC_XFA

FRICTION_LEVELS = [0.0, 0.25, 0.5, 1.0, 2.0]
# G2 resulto INSENSIBLE al rango 0-2 pedido (ver research log -- sus
# swings de $ por trade a nc=40 son 1.5-2.5x mas grandes que los
# umbrales de $2,000/$3,000 del Combine, asi que unos pocos ticks de
# friccion no cambian que lado del umbral toca cada path). Extendido
# para encontrar el punto de colapso real, tal como pide el punto 1
# del pedido ("identificar el punto de colapso SI EXISTE").
FRICTION_LEVELS_EXTENDED_G2 = [0.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0]

# WR condicional REAL medido en dd_v2/common.py (daily, misma cadencia
# que produccion) -- no el denso -- para que la friccion se aplique
# sobre el WR que de verdad importa para el candidato tal como opera.
G2_WR = 0.7157        # ver dd_v2/common.py output
MGC_WR = 0.4940        # CORREGIDO 13-sep-2026: dd_v2/common.py usaba la hora de
                        # entrada de MES (9:30 CT) tambien para MGC -- bug real, MGC
                        # entra a las 7:13 CT en produccion (RTH_OPEN_HOUR=7 +
                        # ENTRY_WAIT_MINUTES=13, geometry_mgc_scheduler.py). Corregido,
                        # el valor anterior (0.4529) esta OBSOLETO -- ver research log.


def g2_friction_stress(levels=FRICTION_LEVELS):
    print("=" * 90)
    print("G2 (MES) -- Combine pass_rate bajo friccion creciente")
    print("=" * 90)
    spec = SPECS["MES"]
    for friction in levels:
        extra_cost_per_leg = friction * spec.tick_value_usd * G2.nc
        avg_win_usd = G2.tp_ticks * spec.tick_value_usd * G2.nc - extra_cost_per_leg
        avg_loss_usd = G2.sl_ticks * spec.tick_value_usd * G2.nc + extra_cost_per_leg
        commission_usd = spec.commission_roundturn * G2.nc  # comision real ya existente, sin cambios

        dist = ExactDayDist(G2_WR, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
        sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=42)
        r = sim.run()
        combines_ano = (r.pass_rate / r.avg_pass_days * TRADING_DAYS_PER_YEAR) if r.pass_rate > 0 and r.avg_pass_days else 0.0
        print(f"  friccion={friction:.2f} ticks/lado  ->  pass_rate_15d={r.pass_rate:.4f}  "
              f"blow_rate={r.blow_rate:.4f}  avg_pass_days={r.avg_pass_days or float('nan'):.2f}  "
              f"combines/ano={combines_ano:.2f}")


def mgc_combine_friction_stress(wr_label: str, wr: float):
    """Etapa 1 del candidato MGC_XFA (Combine, TOPSTEP_150K) -- mismo
    motor que g2_friction_stress(), completa la cadena de 2 etapas ya
    usada en scripts/cerebro2_cashflow_monte_carlo.py."""
    print("=" * 90)
    print(f"MGC_XFA (MGC/150K) -- Etapa 1: Combine pass_rate bajo friccion (WR={wr:.4f}, {wr_label})")
    print("=" * 90)
    spec = SPECS["MGC"]
    for friction in FRICTION_LEVELS:
        extra_cost_per_leg = friction * spec.tick_value_usd * MGC_XFA.nc
        avg_win_usd = MGC_XFA.tp_ticks * spec.tick_value_usd * MGC_XFA.nc - extra_cost_per_leg
        avg_loss_usd = MGC_XFA.sl_ticks * spec.tick_value_usd * MGC_XFA.nc + extra_cost_per_leg
        commission_usd = spec.commission_roundturn * MGC_XFA.nc

        dist = ExactDayDist(wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
        sim = TopstepMonteCarloSimulator(dist, TOPSTEP_150K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=42)
        r = sim.run()
        print(f"  friccion={friction:.2f} ticks/lado  ->  pass_rate_15d={r.pass_rate:.4f}  blow_rate={r.blow_rate:.4f}")


def mgc_friction_stress(wr_label: str, wr: float):
    print("=" * 90)
    print(f"MGC_XFA (MGC/150K) -- WR={wr:.4f} ({wr_label}) -- payout/prob bajo friccion creciente")
    print("=" * 90)
    spec = SPECS["MGC"]
    per_contract = MGC_XFA.tp_ticks * spec.tick_value_usd  # = SL tambien, RR=1.0
    for friction in FRICTION_LEVELS:
        extra_commission_per_contract = 2 * friction * spec.tick_value_usd  # 2 legs (entrada+salida)
        commission_rt = spec.commission_roundturn + extra_commission_per_contract
        r = simulate_xfa_lifetime_dynamic_nc(
            wr, per_contract, per_contract, commission_rt, spec=XFA_150K, product_code="MGC",
            nc_designed=MGC_XFA.nc, mll_reset_policy="every_payout", n_paths=30_000, max_days=756, seed=7,
        )
        print(f"  friccion={friction:.2f} ticks/lado  ->  prob(>=1 payout)={1-r['prob_never_reached_first_payout']:.4f}  "
              f"avg_payout_usd={r['avg_lifetime_payout_usd']:.2f}  avg_dias={r['avg_lifetime_days']:.2f}")


if __name__ == "__main__":
    g2_friction_stress(FRICTION_LEVELS)
    print("\n  (rango 0-2 sin cambio -- ver rango extendido abajo para el punto de colapso real)\n")
    g2_friction_stress(FRICTION_LEVELS_EXTENDED_G2)
    print()
    mgc_combine_friction_stress("WR diario real 1/dia", MGC_WR)
    print()
    mgc_combine_friction_stress("WR denso/calibracion (referencia)", 0.5020)
    print()
    mgc_friction_stress("WR diario real 1/dia", MGC_WR)
    print()
    mgc_friction_stress("WR denso/calibracion (referencia)", 0.5020)
