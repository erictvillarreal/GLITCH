"""
Glitch — Cerebro 2: verificación adicional del candidato MGC/150K antes
de proponer paso a producción (07-sep-2026)
========================================================================
Rama cerebro2-dev. Dos verificaciones pedidas explícitamente por el
usuario, mismo estándar exigido a cualquier candidato antes de
confiar en él:

1. Reproducción en fresco / out-of-sample: ¿el WR condicional (49.97%
   agregado) se sostiene en CADA sub-período temporal, no solo en el
   agregado de 2 años?
2. ¿La asimetría long/short encontrada en el WR agregado (52.78% vs
   47.16%) se traduce en algo relevante al nivel de pass rate del
   Combine, no solo en el WR base?

Reutiliza `_label_fixed_ticks` (ya auditado, mismo fix de barras
ambiguas) y `TopstepMonteCarloSimulator` (ya auditado, mismo motor
usado para G2 y para el Monte Carlo de flujo de caja de este
candidato) -- ninguna lógica nueva de simulación, solo nuevos cortes
de los mismos datos/herramientas ya validados.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from scripts.camino_b_grid import _label_fixed_ticks
from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_150K
from strategies.geometry_pure import SPECS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
# Uso: python scripts/validate_mgc_subperiods_and_direction.py [ruta_parquet_alternativa]
MGC_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA_DIR, "mgc_5min_2y.parquet")

SL_TICKS = TP_TICKS = 364
MAX_HOLDING_BARS = 100
NC = 6
N_SUBPERIODS = 3


def wr_conditional_for_window(sub: pd.DataFrame, tick_size: float):
    sl_pts = tp_pts = SL_TICKS * tick_size
    n = len(sub)
    signal_indices = np.arange(0, n - MAX_HOLDING_BARS - 1, 1)
    longs = signal_indices[np.arange(len(signal_indices)) % 2 == 0]
    shorts = signal_indices[np.arange(len(signal_indices)) % 2 == 1]
    ll = _label_fixed_ticks(sub, longs, tp_pts, sl_pts, MAX_HOLDING_BARS, side=1, win_first=False)
    ls = _label_fixed_ticks(sub, shorts, tp_pts, sl_pts, MAX_HOLDING_BARS, side=-1, win_first=False)
    all_labels = np.concatenate([ll, ls])
    n_tp, n_sl, n_time = int((all_labels == 1).sum()), int((all_labels == -1).sum()), int((all_labels == 0).sum())
    total = len(all_labels)
    wr_cond = n_tp / (n_tp + n_sl) if (n_tp + n_sl) > 0 else float("nan")
    wr_long = (ll == 1).sum() / ((ll == 1).sum() + (ll == -1).sum()) if len(ll) else float("nan")
    wr_short = (ls == 1).sum() / ((ls == 1).sum() + (ls == -1).sum()) if len(ls) else float("nan")
    return {"n": total, "tp_pct": n_tp / total, "sl_pct": n_sl / total, "time_exit_pct": n_time / total,
            "wr_conditional": wr_cond, "wr_long": wr_long, "wr_short": wr_short}


def part1_subperiods():
    print("=" * 100 + "\nPARTE 1: WR condicional por sub-periodo temporal\n" + "=" * 100)
    mgc = pd.read_parquet(MGC_PATH)
    tick_size = SPECS["MGC"].tick_size
    start, end = mgc.index.min(), mgc.index.max()
    bounds = pd.date_range(start, end + pd.Timedelta(days=1), periods=N_SUBPERIODS + 1)
    print(f"Rango total: {start.date()} a {end.date()}  |  {N_SUBPERIODS} sub-periodos de igual duracion\n")

    results = []
    for i in range(N_SUBPERIODS):
        sub = mgc[(mgc.index >= bounds[i]) & (mgc.index < bounds[i + 1])]
        r = wr_conditional_for_window(sub, tick_size)
        r["periodo"] = i + 1
        r["inicio"], r["fin"] = bounds[i].date(), bounds[i + 1].date()
        results.append(r)
        print(f"Sub-periodo {i+1} ({r['inicio']} a {r['fin']}): N={r['n']}  "
              f"TP={r['tp_pct']:.1%} SL={r['sl_pct']:.1%} time-exit={r['time_exit_pct']:.1%}")
        print(f"  WR_condicional={r['wr_conditional']:.4f}  (long={r['wr_long']:.4f}  short={r['wr_short']:.4f})  "
              f"diff_vs_0.50={((r['wr_conditional']-0.5)*100):+.2f}pp\n")
    return results


def part2_combine_direction_sensitivity(subperiod_results):
    print("=" * 100 + "\nPARTE 2: sensibilidad del pass rate del Combine a la asimetria long/short\n" + "=" * 100)
    tick_value = SPECS["MGC"].tick_value_usd
    commission_rt = SPECS["MGC"].commission_roundturn
    gross = SL_TICKS * tick_value * NC
    commission = commission_rt * NC

    scenarios = [
        ("Alternado (agregado, ya validado)", 0.4997),
        ("Solo LONG (agregado 2 anios)", 0.5278),
        ("Solo SHORT (agregado 2 anios)", 0.4716),
    ]
    for r in subperiod_results:
        scenarios.append((f"Solo LONG, sub-periodo {r['periodo']}", r["wr_long"]))
        scenarios.append((f"Solo SHORT, sub-periodo {r['periodo']}", r["wr_short"]))

    for label, wr in scenarios:
        dist = DailyReturnDist(win_rate=wr, avg_win=gross - commission, avg_loss=gross + commission, name=label)
        sim = TopstepMonteCarloSimulator(dist, spec=TOPSTEP_150K, n_paths=100_000, max_days=250, seed=7)
        r = sim.run()
        print(f"{label:38s} WR={wr:.4f}  pass_rate={r.pass_rate:.4f}  blow_rate={r.blow_rate:.4f}")


if __name__ == "__main__":
    subperiod_results = part1_subperiods()
    part2_combine_direction_sensitivity(subperiod_results)
