"""
Glitch — Camino B: chequeo de sesgo direccional + overfitting temporal
==========================================================================
El grid original (scripts/camino_b_grid.py) encontro que "always_short"
domina "alternate" en combines_por_año. Esto es sospechoso -- Camino B
esta diseñado para NO necesitar edge real, y un sesgo direccional
sistematico ES una forma de edge (o de sobreajuste). Este script:

  1. Compara las 3 direcciones lado a lado, MISMA geometria, nc=40 (no 50 --
     doble razon para margen de seguridad: limite duro de Topstep +
     sospecha de sobreajuste en la dimension "direccion").
  2. Split temporal 50/50 (primera mitad / segunda mitad de los 2 años) --
     si la ventaja de always_short sobre alternate NO se sostiene en
     ambas mitades por separado, es sobreajuste: descartar always_short.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.prop_firm import TOPSTEP_50K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from scripts.camino_b_grid import (
    measure_wr_bracket, ExactDayDist, TICK_VALUE_USD, COMMISSION_ROUNDTURN,
    N_PATHS, MAX_DAYS, TRADING_DAYS_PER_YEAR, MES_PATH,
)

NC = 40  # candidato "real" per instruccion del usuario -- no 50
HOLD = 100
GEOMETRIES = [
    ("G1 (grid winner)", 50, 20),
    ("G2 (refinado)", 100, 40),
]
DIRECTIONS = ["always_short", "always_long", "alternate"]


def combines_for(wr: float, sl: int, tp: int, nc: int) -> dict:
    avg_win_usd = tp * TICK_VALUE_USD * nc
    avg_loss_usd = sl * TICK_VALUE_USD * nc
    commission_usd = COMMISSION_ROUNDTURN * nc
    dist = ExactDayDist(wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=42)
    r = sim.run()
    if r.pass_rate > 0 and r.avg_pass_days:
        combines_ano = (r.pass_rate / r.avg_pass_days) * TRADING_DAYS_PER_YEAR
    else:
        combines_ano = 0.0
    return {"wr": round(wr, 4), "pass_rate": round(r.pass_rate, 4),
            "blow_rate": round(r.blow_rate, 4),
            "avg_days": round(r.avg_pass_days, 2) if r.avg_pass_days else None,
            "combines_ano": round(combines_ano, 2)}


def run_period(mes: pd.DataFrame, label: str, sl: int, tp: int) -> dict:
    br = measure_wr_bracket(mes, sl, tp, HOLD)
    out = {}
    for direction in DIRECTIONS:
        if direction == "always_short":
            wr = (br["wr_short_opt"] + br["wr_short_cons"]) / 2
        elif direction == "always_long":
            wr = (br["wr_long_opt"] + br["wr_long_cons"]) / 2
        else:
            wr = (br["wr_all_opt"] + br["wr_all_cons"]) / 2
        out[direction] = combines_for(wr, sl, tp, NC)
    return out


def main():
    mes = pd.read_parquet(MES_PATH)
    n = len(mes)
    mid = n // 2
    h1, h2 = mes.iloc[:mid], mes.iloc[mid:]
    print(f"MES: {n:,} barras. H1: {h1.index.min()} -> {h1.index.max()} ({len(h1):,} barras)")
    print(f"     H2: {h2.index.min()} -> {h2.index.max()} ({len(h2):,} barras)")
    print(f"nc={NC}, max_holding_bars={HOLD}\n")

    all_results = []
    for geo_label, sl, tp in GEOMETRIES:
        print("=" * 90)
        print(f"{geo_label}: SL={sl}/TP={tp} (RR={tp/sl:.2f})")
        print("=" * 90)

        for period_label, df in [("FULL (2y)", mes), ("H1 (primera mitad)", h1), ("H2 (segunda mitad)", h2)]:
            res = run_period(df, period_label, sl, tp)
            for direction, stats in res.items():
                row = {"geometria": geo_label, "periodo": period_label, "direction": direction, **stats}
                all_results.append(row)
            print(f"\n  -- {period_label} --")
            for direction in DIRECTIONS:
                s = res[direction]
                print(f"    {direction:14s} WR={s['wr']:.4f}  pass={s['pass_rate']:.4f}  "
                      f"blow={s['blow_rate']:.4f}  avg_days={s['avg_days']}  combines/año={s['combines_ano']}")

            gap = res["always_short"]["combines_ano"] - res["alternate"]["combines_ano"]
            print(f"    >>> GAP always_short - alternate: {gap:+.2f} combines/año")
        print()

    df_out = pd.DataFrame(all_results)
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data_cache", "camino_b_direction_check.csv")
    df_out.to_csv(out_path, index=False)
    print(f"Guardado: {out_path}\n")

    print("=" * 90)
    print("VEREDICTO DE SOBREAJUSTE (gap always_short - alternate, H1 vs H2)")
    print("=" * 90)
    for geo_label, sl, tp in GEOMETRIES:
        sub = df_out[df_out.geometria == geo_label]
        gaps = {}
        for period in ["H1 (primera mitad)", "H2 (segunda mitad)"]:
            p = sub[sub.periodo == period]
            gaps[period] = float(p[p.direction == "always_short"]["combines_ano"].iloc[0] -
                                  p[p.direction == "alternate"]["combines_ano"].iloc[0])
        print(f"{geo_label}: H1 gap={gaps['H1 (primera mitad)']:+.2f}  H2 gap={gaps['H2 (segunda mitad)']:+.2f}")
        both_positive = gaps["H1 (primera mitad)"] > 0 and gaps["H2 (segunda mitad)"] > 0
        print(f"  -> {'SOSTIENE en ambas mitades' if both_positive else 'NO sostiene en ambas mitades -- SOBREAJUSTE'}")


if __name__ == "__main__":
    main()
