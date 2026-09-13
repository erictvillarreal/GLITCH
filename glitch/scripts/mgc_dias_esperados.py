"""
Glitch — Calculo formal de "dias_calendario_esperados" para el candidato
MGC/150K (geometria pura, Cerebro 2), misma formula que G2 (09-sep-2026)
==============================================================================
Pedido explicito del usuario: antes de hardcodear un "dias esperados" para
MGC en scheduler/geometry_mgc_scheduler.py (template de Telegram, "Dias vs.
Estimado"), calcularlo formalmente con la MISMA formula ya usada y
documentada para G2 (ver GLITCH_RESEARCH_LOG.md, "Duracion recomendada del
periodo de paper trading", 25-ago-2026) -- NO un numero de servilleta.

Formula (identica a la de G2):
    dias_promedio_resolucion = SimResult.avg_resolution_days
        (promedio de TODOS los intentos resueltos, pase o truene -- ya
        existe como property en simulation/monte_carlo.py::SimResult,
        agregada en esta misma sesion para el calculo de G2 -- MISMO
        codigo, no una reimplementacion aparte)
    intentos_esperados_para_pasar = 1 / pass_rate
    dias_calendario_esperados = dias_promedio_resolucion * intentos_esperados_para_pasar

Reusa el mismo motor ya auditado (simulation/monte_carlo.py::TopstepMonteCarloSimulator)
y la misma geometria/distribucion ya usada en
scripts/cerebro2_cashflow_monte_carlo.py::build_combine_pool() (SL=TP=364
ticks, nc=6, TOPSTEP_150K) -- no una simulacion nueva ni distinta.

Corre con 2 valores de WR, reportados por separado (sin promediarlos ni
elegir uno "por defecto" en el codigo -- la eleccion de cual usar en
produccion la hace el usuario, no este script):
  - WR=0.50 (teorico, el que ya usa cerebro2_cashflow_monte_carlo.py)
  - WR=0.5020 (empirico, ventana horaria corregida 7:00-15:00 CT --
    dataset de referencia actual para este candidato, ver
    GLITCH_RESEARCH_LOG.md, "Fase 1 (continuacion)", 07-sep-2026)

No requiere API key -- Monte Carlo puro (numpy), sin dependencia de red.

Uso:
    python scripts/mgc_dias_esperados.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_150K
from strategies.geometry_pure import SPECS

NC = 6
SL_TICKS = TP_TICKS = 364
TICK_VALUE = SPECS["MGC"].tick_value_usd
COMMISSION_RT = SPECS["MGC"].commission_roundturn

N_PATHS = 200_000
MAX_DAYS = 250
SEED = 7  # mismo seed que scripts/cerebro2_cashflow_monte_carlo.py::build_combine_pool()


def compute(wr: float, label: str) -> dict:
    gross = SL_TICKS * TICK_VALUE * NC
    commission = COMMISSION_RT * NC
    dist = DailyReturnDist(win_rate=wr, avg_win=gross - commission, avg_loss=gross + commission,
                            name=f"MGC_150K_candidate_{label}")
    sim = TopstepMonteCarloSimulator(dist, spec=TOPSTEP_150K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=SEED)
    r = sim.run()

    dias_promedio_resolucion = r.avg_resolution_days
    intentos_esperados = 1 / r.pass_rate
    dias_calendario_esperados = dias_promedio_resolucion * intentos_esperados

    print(f"\n=== WR={wr:.4f} ({label}) ===")
    print(f"pass_rate               = {r.pass_rate:.4f} ({r.pass_rate:.1%})")
    print(f"blow_rate                = {r.blow_rate:.4f}")
    print(f"n_alive (sin resolver)   = {r.n_alive} de {N_PATHS}")
    print(f"avg_pass_days            = {r.avg_pass_days:.4f}")
    print(f"avg_blown_days           = {r.avg_blown_days:.4f}")
    print(f"dias_promedio_resolucion = {dias_promedio_resolucion:.4f}")
    print(f"intentos_esperados       = {intentos_esperados:.4f}")
    print(f"dias_calendario_esperados = {dias_calendario_esperados:.4f}")

    return {
        "wr": wr, "pass_rate": r.pass_rate, "avg_pass_days": r.avg_pass_days,
        "avg_blown_days": r.avg_blown_days, "dias_promedio_resolucion": dias_promedio_resolucion,
        "dias_calendario_esperados": dias_calendario_esperados,
    }


if __name__ == "__main__":
    theoretical = compute(0.50, "teorico")
    empirical = compute(0.5020, "empirico, ventana corregida")

    print("\n=== Comparacion ===")
    print(f"{'WR':<30} {'pass_rate':<12} {'dias_calendario_esperados'}")
    print(f"{'0.50 (teorico)':<30} {theoretical['pass_rate']:<12.4f} {theoretical['dias_calendario_esperados']:.4f}")
    print(f"{'0.5020 (empirico, corregido)':<30} {empirical['pass_rate']:<12.4f} {empirical['dias_calendario_esperados']:.4f}")
