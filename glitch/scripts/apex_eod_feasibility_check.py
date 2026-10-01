"""
Glitch -- Factibilidad RAPIDA de G2 (MES, SL100/TP40) bajo las reglas REALES de
Apex Trader Funding "All New Apex" (EOD Trail, post-01-mar-2026), 30-sep-2026.
==============================================================================
Pedido explicito del usuario: evaluar si el sistema es elegible en otras prop
firms, con pruebas rapidas calculadas, no solo lectura de reglas de marketing.

Reglas de Apex verificadas HOY contra help.apextraderfunding.com (texto citado
en el research log, seccion "Prop firms alternativas 30-sep-2026"):
  * EOD Drawdown: el piso se calcula UNA VEZ AL DIA al cierre (4:59:59pm ET),
    basado en el balance REALIZADO de cierre -- NUNCA se mueve por un pico de
    P&L no realizado intradia. Enforced en tiempo real contra el balance
    actual (si se toca intradia, liquida). Nunca baja.
  * Daily Loss Limit (DLL): SOLO existe en evaluaciones EOD (no en Intraday
    Trail). Monto FIJO por tamaño de cuenta durante el eval (no escala con
    profit): 25K=$500, 50K=$1,000, 100K=$1,500, 150K=$2,000. Monitoreado en
    tiempo real contra equity total (realizado + no realizado). Si se toca:
    liquida posiciones, pausa el dia, la CUENTA sigue viva (no es quiebre).
  * Max Drawdown (= MLL-equivalente): 25K=$1,000, 50K=$2,000, 100K=$3,000,
    150K=$4,000 (EOD Trail).
  * SIN regla de consistencia durante la evaluacion ("NO Eval consistency
    rules" -- confirmado en homepage). El 50% consistency SOLO bloquea
    payouts ya en PA, no hace fallar el eval ni la cuenta.
  * Min dias para pasar: 1 (no hay minimo de 2 dias como en Topstep).

REUTILIZACION: el motor de bar-walk 5min (build_tables/simulate) es LITERAL
el mismo de scripts/g2_real_rules_scan.py (24-sep-2026) -- MISMO dataset
(mes_5min_2y.parquet), MISMA entrada 9:45 CT / flatten 14:30 CT, MISMA
convencion de "piso fijo al inicio del dia, k=min(SL, floor(distancia/unit))
intradia" -- que para una estrategia de 1 trade/dia es, de hecho, una
representacion MAS fiel de la regla de Apex (piso literalmente fijo todo el
dia) que de la de Topstep (MLL que el texto oficial de Topstep dice que
puede re-trailear con el pico NO REALIZADO dentro del mismo trade, algo que
este motor simplificado nunca modelo tampoco del lado Topstep -- ver nota en
GLITCH_RESEARCH_LOG.md). CERO cambio al motor; solo cambian los parametros
(MLL, DLL, cons=None, min_days=1) para reflejar las reglas de Apex en vez de
las de Topstep.

NO INCLUYE: comision especifica de Apex (se asume la misma $1.22/contrato de
Topstep MES -- Apex no publica su comision por contrato en las paginas leidas
hoy; esto es una aproximacion declarada, no un dato verificado de Apex).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.g2_real_rules_scan import build_tables, simulate, TICK, TV, COMM

APEX_TIERS = {
    # tier: (max_drawdown, dll, profit_target)
    "25K":  (1_000.0, 500.0, 1_500.0),
    "50K":  (2_000.0, 1_000.0, 3_000.0),
    "100K": (3_000.0, 1_500.0, 6_000.0),
    "150K": (4_000.0, 2_000.0, 9_000.0),
}

if __name__ == "__main__":
    T = build_tables()
    nd = len(T[0])
    print(f"dias MES disponibles: {nd}. Motor: bar-walk 5min, 1 trade/dia 9:45-14:30 CT, alternando.\n")

    print("=== REFERENCIA: G2 (nc=40, TP40, SL100) bajo Topstep real (ya conocido, re-derivado aqui mismo motor) ===")
    import numpy as np
    r = simulate(T, np.arange(nd), 40, 40, 100, dll=False, cons=0.55, min_days=2, liquidate=True)
    print(f"  Topstep 50K Combine: pass={r['pass_rate']:.3f} dias_pase={r['days_pass']:.2f} pases/ano={r['passes_yr']:.1f}\n")

    print("=== Apex EOD Trail -- G2 SIN modificar (nc=40, TP40, SL100), por tamaño de cuenta ===")
    print("    (sin consistencia en eval, min_days=1, MLL propio + DLL propio de cada tier)")
    import scripts.g2_real_rules_scan as m
    for tier, (mll, dll_usd, target) in APEX_TIERS.items():
        m.MLL, m.DLL_USD, m.TARGET = mll, dll_usd, target
        r = simulate(T, np.arange(nd), 40, 40, 100, dll=True, cons=None, min_days=1, liquidate=True, max_days=30)
        print(f"  Apex {tier} (MLL=${mll:.0f}, DLL=${dll_usd:.0f}, target=${target:.0f}): pass={r['pass_rate']:.3f} blow={r['blow']:.3f} "
              f"dias_pase={r['days_pass']:.2f} pases/ano={r['passes_yr']:.1f}")

    print("\n=== Apex EOD Trail -- G2 REDIMENSIONADO para respetar el DLL (nc = floor(DLL/(100*1.25))) ===")
    print("    (max_days=30, igual a la ventana REAL de 30 dias del eval de Apex -- 15 subestimaba el pass real)")
    for tier, (mll, dll_usd, target) in APEX_TIERS.items():
        nc_fit = max(1, int(dll_usd // (100 * TV)))
        m.MLL, m.DLL_USD, m.TARGET = mll, dll_usd, target
        r = simulate(T, np.arange(nd), nc_fit, 40, 100, dll=True, cons=None, min_days=1, liquidate=True, max_days=30)
        print(f"  Apex {tier} (nc={nc_fit}, MLL=${mll:.0f}, DLL=${dll_usd:.0f}, target=${target:.0f}): pass={r['pass_rate']:.3f} blow={r['blow']:.3f} "
              f"dias_pase={r['days_pass']:.2f} pases/ano={r['passes_yr']:.1f}")
