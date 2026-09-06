"""
Glitch — Cerebro 2: validación empírica del WR=50% asumido para el
candidato de geometría pura MGC/150K contra datos REALES de MGC
(preparado 06-sep-2026 — NO CORRIDO TODAVÍA, ver GLITCH_RESEARCH_LOG.md)
============================================================================
El candidato de geometría pura de Cerebro 2 (MGC/150K, k=2, nc=6,
SL=TP=364 ticks, dirección alternada sin señal predictiva) usa
WR=0.5 como supuesto TEÓRICO de Monte Carlo (gambler's ruin para
RR=1.0 simétrico) -- nunca se verificó si ese 50% es alcanzable
empíricamente en datos REALES de MGC, a diferencia de G2 (Cerebro 1),
cuyo WR empírico (~70.6%, bracket optimista/conservador) SÍ se validó
contra MES real antes de confiar en el candidato (ver sección
"Consolidación — Camino B" arriba, 25-ago-2026).

Misma metodología EXACTA que esa validación de G2, reutilizando la
función ya auditada `measure_wr_bracket()` de scripts/camino_b_grid.py
(bracket optimista/pre-fix vs conservador/post-fix del bug de barras
ambiguas, alternando long/short sin ninguna señal predictiva real,
sobre CADA posición de barra posible -- no solo una vez al día, para
tener suficiente N de calibración).

max_holding_bars=100 (5min bars, ~1 sesión RTH) -- misma convención
que G2 (que también intenta 1 trade/día) y uno de los valores ya
usados en HOLDING_GRID de camino_b_grid.py, no un número inventado
para este script.

CÓMO CORRERLO (mañana, cuando el usuario decida):
    python scripts/validate_mgc_wr_empirical.py

QUÉ MIRAR EN EL RESULTADO:
  - wr_all_cons (bracket conservador, post-fix) vs 0.50 asumido.
  - Si wr_all_cons está MUY por debajo de 0.50: el candidato XFA es
    peor de lo que el Monte Carlo asumió (el WR=0.5 fue optimista).
  - Si está muy por ENCIMA: hay margen de seguridad no capturado, o
    hay una asimetría/sesgo real que valdría la pena investigar (con
    la misma cautela ya aplicada a los sesgos direccionales de G2 --
    "ruido con signo consistente por azar", no asumir edge real sin
    más evidencia).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from scripts.camino_b_grid import measure_wr_bracket
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MGC_PATH = os.path.join(DATA_DIR, "mgc_5min_2y.parquet")

# Candidato exacto validado en el Monte Carlo de flujo de caja
# (ver GLITCH_RESEARCH_LOG.md, 06-sep-2026): MGC/150K, k=2, nc=6.
SL_TICKS = TP_TICKS = 364
MAX_HOLDING_BARS = 100  # misma convención que G2 -- ~1 sesión RTH
WR_TEORICO_ASUMIDO = 0.50


def main():
    mgc = pd.read_parquet(MGC_PATH)
    tick_size = SPECS["MGC"].tick_size  # 0.10

    result = measure_wr_bracket(mgc, SL_TICKS, TP_TICKS, MAX_HOLDING_BARS, tick_size=tick_size)

    print(f"Candidato: MGC, SL={SL_TICKS} TP={TP_TICKS} ticks (RR=1.0), max_holding_bars={MAX_HOLDING_BARS}")
    print(f"N trades (calibracion densa, todas las posiciones de barra): {result['n_trades']}")
    print(f"\nWR bracket [optimista/pre-fix, conservador/post-fix]:")
    print(f"  wr_all_opt  = {result['wr_all_opt']:.4f}")
    print(f"  wr_all_cons = {result['wr_all_cons']:.4f}")
    print(f"  wr_long_cons  = {result['wr_long_cons']:.4f}")
    print(f"  wr_short_cons = {result['wr_short_cons']:.4f}")
    print(f"\nWR teorico asumido en el Monte Carlo (gambler's ruin, RR=1.0 simetrico): {WR_TEORICO_ASUMIDO:.4f}")
    midpoint = (result["wr_all_opt"] + result["wr_all_cons"]) / 2
    print(f"Punto medio del bracket empirico (misma convencion usada para G2): {midpoint:.4f}")
    diff = midpoint - WR_TEORICO_ASUMIDO
    print(f"\nDiferencia (empirico - teorico): {diff:+.4f} ({diff*100:+.2f} puntos porcentuales)")
    print("\nRECORDATORIO: esto es UNA corrida sobre UN dataset de 2 años -- si el resultado")
    print("es prometedor (empirico > teorico), reproducir en fresco antes de confiar en el")
    print("numero, mismo estandar aplicado a todo lo demas en esta sesion.")


if __name__ == "__main__":
    main()
