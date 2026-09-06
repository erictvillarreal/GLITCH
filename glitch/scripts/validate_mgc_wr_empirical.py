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

import numpy as np
import pandas as pd

from scripts.camino_b_grid import measure_wr_bracket, _label_fixed_ticks
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
# Uso: python scripts/validate_mgc_wr_empirical.py [ruta_parquet_alternativa]
# -- para re-correr contra data_cache/mgc_5min_2y_corrected_window.parquet
# (ventana RTH corregida, ver scripts/fetch_mgc_correct_window.py) sin editar el script.
MGC_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA_DIR, "mgc_5min_2y.parquet")

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
    print(f"\nWR bracket [optimista/pre-fix, conservador/post-fix] -- METRICA CRUDA de")
    print("measure_wr_bracket() (wr_all = TP / TOTAL, incluye time-exits en el denominador):")
    print(f"  wr_all_opt  = {result['wr_all_opt']:.4f}")
    print(f"  wr_all_cons = {result['wr_all_cons']:.4f}")

    # CORRECCION (06-sep-2026): wr_all diluye el denominador con trades que
    # expiran por tiempo (ni TP ni SL tocado dentro de max_holding_bars) --
    # el MISMO problema de metrica ya diagnosticado y corregido para el
    # win_rate de wf_slow_mr.py. Para G2 (SL=100/TP=40, barreras angostas
    # relativas a su holding window) el time-exit share es solo ~1.2% y
    # wr_all~=WR_condicional -- ahi no importa. Para MGC (barreras 8x mas
    # anchas que el rango promedio de barra) el time-exit share es ~30% --
    # SI importa, y mucho. La metrica correcta para comparar contra el
    # WR=0.5 teorico es TP/(TP+SL), no TP/total.
    sl_pts = tp_pts = SL_TICKS * tick_size
    n = len(mgc)
    signal_indices = np.arange(0, n - MAX_HOLDING_BARS - 1, 1)
    longs = signal_indices[np.arange(len(signal_indices)) % 2 == 0]
    shorts = signal_indices[np.arange(len(signal_indices)) % 2 == 1]
    ll = _label_fixed_ticks(mgc, longs, tp_pts, sl_pts, MAX_HOLDING_BARS, side=1, win_first=False)
    ls = _label_fixed_ticks(mgc, shorts, tp_pts, sl_pts, MAX_HOLDING_BARS, side=-1, win_first=False)
    all_labels = np.concatenate([ll, ls])
    n_tp, n_sl, n_time = int((all_labels == 1).sum()), int((all_labels == -1).sum()), int((all_labels == 0).sum())
    total = len(all_labels)
    wr_conditional = n_tp / (n_tp + n_sl)
    wr_long_cond = (ll == 1).sum() / ((ll == 1).sum() + (ll == -1).sum())
    wr_short_cond = (ls == 1).sum() / ((ls == 1).sum() + (ls == -1).sum())

    print(f"\nDistribucion real: TP={n_tp} ({n_tp/total:.1%})  SL={n_sl} ({n_sl/total:.1%})  "
          f"time-exit={n_time} ({n_time/total:.1%})")
    print(f"\nWR CONDICIONAL (TP/(TP+SL), excluye time-exits -- la metrica correcta a comparar "
          f"contra el WR=0.5 teorico):")
    print(f"  wr_condicional (todo)  = {wr_conditional:.4f}")
    print(f"  wr_condicional (long)  = {wr_long_cond:.4f}")
    print(f"  wr_condicional (short) = {wr_short_cond:.4f}")

    print(f"\nWR teorico asumido en el Monte Carlo (gambler's ruin, RR=1.0 simetrico): {WR_TEORICO_ASUMIDO:.4f}")
    diff = wr_conditional - WR_TEORICO_ASUMIDO
    print(f"\nDiferencia (empirico condicional - teorico): {diff:+.4f} ({diff*100:+.2f} puntos porcentuales)")
    print("\nRECORDATORIO: esto es UNA corrida sobre UN dataset de 2 años -- si el resultado")
    print("es prometedor (empirico > teorico), reproducir en fresco antes de confiar en el")
    print("numero, mismo estandar aplicado a todo lo demas en esta sesion.")


if __name__ == "__main__":
    main()
