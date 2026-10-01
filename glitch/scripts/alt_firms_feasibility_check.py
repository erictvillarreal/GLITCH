"""
Glitch -- Factibilidad de G2 (MES, SL100/TP40) en Tradeify, Bulenox y MyFundedFutures
(MFFU), 30-sep-2026 (continuacion). Los 3 sobrevivieron los filtros de automatizacion
(fuente propia, verbatim) y de pais (Mexico no aparece en ninguna lista de restriccion).
Ninguno de los 3 tiene, en la pagina mas relevante de cada uno, una regla explicita
tipo "no usar el drawdown/DLL como stop-loss" (a diferencia de Apex) -- MISMO motor
que apex_eod_feasibility_check.py / g2_real_rules_scan.py, solo cambian los
parametros por los de cada firma (fuente: research log, 30-sep-2026 continuacion).

Parametros (50K, plan mas representativo de cada firma, verificados hoy):
  Tradeify Growth 50K:  target=$3,000 MLL(EOD)=$2,000 DLL=$1,250 cons=None(eval) min_days=1
  Bulenox Opcion 2 50K: target=$3,000 MLL(EOD)=$2,500 DLL=$1,100 cons=None(eval, no confirmado explicito) min_days=1 (asumido, no confirmado)
  MFFU Rapid EOD 50K:   target=$3,000 MLL(EOD)=$2,000 DLL=None   cons=0.30(EVAL, a diferencia de las otras 2) min_days=4
                        + limite DURO de contratos = 30 micro (nc=40 ni siquiera esta permitido, es breach directo)

Dos variantes de nc por firma:
  "sin modificar": el nc mas grande PERMITIDO por cada firma (40 para Tradeify/Bulenox,
    30 para MFFU por su limite duro de contrato) con el SL nominal de 100 ticks --
    el DLL/MLL trunca el SL efectivo igual que en el chequeo de Apex. Ninguna de las 3
    tiene una regla textual que prohiba esto (a diferencia de Apex), pero sigue siendo
    la misma practica que ahi se nombro explicitamente -- se reporta con esa advertencia,
    no como recomendacion.
  "redimensionado": nc = floor(MLL/(100*1.25)) para no depender de la liquidacion
    anticipada via MLL/DLL.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.g2_real_rules_scan import build_tables, simulate, TV
import scripts.g2_real_rules_scan as m

FIRMS = {
    # firma: (mll, dll_or_None, target, cons_or_None, min_days, nc_max_permitido)
    "Tradeify Growth 50K":  (2000.0, 1250.0, 3000.0, None, 1, 40),
    "Bulenox Opcion2 50K":  (2500.0, 1100.0, 3000.0, None, 1, 40),
    "MFFU Rapid EOD 50K":   (2000.0, None,   3000.0, 0.30, 4, 30),
}

if __name__ == "__main__":
    T = build_tables()
    nd = len(T[0])
    print(f"dias MES: {nd}. Motor: bar-walk 5min, 1 trade/dia 9:45-14:30 CT, alternando, max_days=30.\n")
    print("=== REFERENCIA (ya conocida, mismo motor) ===")
    r = simulate(T, np.arange(nd), 40, 40, 100, dll=False, cons=0.55, min_days=2, liquidate=True)
    print(f"  Topstep 50K Combine:        pass={r['pass_rate']:.3f} pases/ano={r['passes_yr']:.1f}")
    m.MLL, m.DLL_USD, m.TARGET = 2000.0, 1000.0, 3000.0  # Apex 50K real: MLL=$2,000, DLL=$1,000 (NO $2,000 -- ver correccion 30d55b1)
    r = simulate(T, np.arange(nd), 40, 40, 100, dll=True, cons=None, min_days=1, liquidate=True, max_days=30)
    print(f"  Apex 50K EOD (ya conocido): pass={r['pass_rate']:.3f} pases/ano={r['passes_yr']:.1f}\n")

    for label, (mll, dll_usd, target, cons, min_days, nc_max) in FIRMS.items():
        m.MLL, m.TARGET = mll, target
        has_dll = dll_usd is not None
        m.DLL_USD = dll_usd if has_dll else 10**9
        print(f"=== {label} (MLL=${mll:.0f}, DLL={'$'+str(int(dll_usd)) if has_dll else 'ninguno'}, "
              f"target=${target:.0f}, cons={cons}, min_days={min_days}, nc_max_permitido={nc_max}) ===")
        r = simulate(T, np.arange(nd), nc_max, 40, 100, dll=has_dll, cons=cons, min_days=min_days, liquidate=True, max_days=30)
        print(f"  sin modificar   (nc={nc_max}):  pass={r['pass_rate']:.3f} blow={r['blow']:.3f} "
              f"dias_pase={r['days_pass']:.2f} pases/ano={r['passes_yr']:.1f}")
        nc_fit = max(1, int(mll // (100 * TV))) if not has_dll else max(1, int(dll_usd // (100 * TV)))
        nc_fit = min(nc_fit, nc_max)
        r = simulate(T, np.arange(nd), nc_fit, 40, 100, dll=has_dll, cons=cons, min_days=min_days, liquidate=True, max_days=30)
        print(f"  redimensionado  (nc={nc_fit}): pass={r['pass_rate']:.3f} blow={r['blow']:.3f} "
              f"dias_pase={r['days_pass']:.2f} pases/ano={r['passes_yr']:.1f}\n")
