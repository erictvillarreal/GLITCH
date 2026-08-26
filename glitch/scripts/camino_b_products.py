"""
Glitch — Camino B: extension a 6 productos (25-ago-2026)
==========================================================================
Extiende la geometria pura (RR<=0.5, WR = punto medio del bracket
empirico, comision real, direccion=alternar por default) a productos
fuera de MES/MNQ. Metodologia identica a scripts/camino_b_grid.py y
scripts/camino_b_direction_check.py, no reinventada por producto.

Alcance: 6 productos (7 pedidos, MBT excluido -- ver nota abajo),
familias distintas, NO los 46 completos -- evita multiple-testing sin
correccion.

MBT EXCLUIDO: fetch_mes_2y.py MBT trajo un hueco de ~13 MESES (feb-2025
a mar-2026) con 0-20 barras/contrato bajo la regla de roll "vencimiento
mas cercano" -- la liquidez de Bitcoin micro NO sigue esa convencion de
forma confiable (a diferencia de indices/tasas/FX/metales/energia, que
si la siguen limpio). Arreglar esto necesitaria roll por volumen real,
no por fecha -- fuera de alcance de esta pasada. Correr con datos con
ese hueco habria producido un resultado invalido, no un resultado debil.

Contratos y limites reales de Topstep 50K (verificados contra
help.topstep.com, no supuestos -- ver reporte):
  ZC  (Corn, full)         tick=0.0025  $12.50/tick  comision $5.28 RT  nc<=5
  ZN  (10Y Note, full)     tick=0.015625 $15.625/tick comision $2.62 RT nc<=5
  MGC (Micro Gold)         tick=0.10    $1.00/tick   comision $1.92 RT  nc<=30 (risk-adjusted)
  M6E (Micro EUR/USD)      tick=0.0001  $1.25/tick   comision $1.00 RT  nc<=50
  M2K (Micro Russell 2000) tick=0.10    $0.50/tick   comision $1.22 RT  nc<=50
  MCL (Micro WTI Crude)    tick=0.01    $1.00/tick   comision $1.52 RT  nc<=30 (risk-adjusted)

Geometrias candidatas por producto: derivadas del rango promedio de
barra 5min de CADA producto (no ticks fijos copiados de MES) -- 3
candidatos (ancho x RR), igual criterio para todos.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.prop_firm import TOPSTEP_50K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from scripts.camino_b_grid import measure_wr_bracket, ExactDayDist, N_PATHS, MAX_DAYS, TRADING_DAYS_PER_YEAR

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
HOLD = 100

PRODUCTS = {
    # label: (parquet_stem, tick_size, tick_value_usd, commission_rt, nc_cap, familia)
    # BUG FIX (25-ago-2026): ZC (grano) se cotiza en CENTAVOS/bushel (close~437 =
    # 437 centavos = $4.37) pero el tick_size original (0.0025) estaba en
    # DOLARES/bushel -- mismatch de unidades de 100x contra el feed de precios,
    # que corrompia la economia en $ (WR/labeling de barras no se vio afectado,
    # se cancelaba internamente, pero avg_win_usd/avg_loss_usd si). Tick real:
    # 1/4 de centavo = 0.25 en las mismas unidades que el feed (centavos).
    "ZC (Corn)":        ("zc",  0.25,      12.50,  5.28, 5,  "Agricola"),
    "ZN (10Y Note)":    ("zn",  0.015625,  15.625, 2.62, 5,  "Tasas"),
    "GC/MGC (Gold)":    ("mgc", 0.10,      1.00,   1.92, 30, "Metales"),
    "6E/M6E (Euro FX)": ("m6e", 0.0001,    1.25,   1.00, 50, "FX mayor"),
    "RTY/M2K (Russell)":("m2k", 0.10,      0.50,   1.22, 50, "Equity index (control)"),
    "CL/MCL (Crude)":   ("mcl", 0.01,      1.00,   1.52, 30, "Energia"),
}

RR_CANDIDATES = [0.33, 0.40, 0.50]
WIDTH_MULTIPLIERS = [3, 5, 8]  # x rango promedio de barra, en ticks


def avg_bar_range_ticks(df: pd.DataFrame, tick_size: float) -> float:
    return float((df["high"] - df["low"]).mean() / tick_size)


def combines_for(wr: float, sl_ticks: float, tp_ticks: float, tick_value: float,
                  commission_rt: float, nc: int) -> dict:
    avg_win_usd = tp_ticks * tick_value * nc
    avg_loss_usd = sl_ticks * tick_value * nc
    commission_usd = commission_rt * nc
    dist = ExactDayDist(wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=42)
    r = sim.run()
    combines_ano = (r.pass_rate / r.avg_pass_days) * TRADING_DAYS_PER_YEAR if r.pass_rate > 0 and r.avg_pass_days else 0.0
    return {"pass_rate": round(r.pass_rate, 4), "blow_rate": round(r.blow_rate, 4),
            "avg_days": round(r.avg_pass_days, 2) if r.avg_pass_days else None,
            "combines_ano": round(combines_ano, 2)}


def main():
    all_rows = []
    winners = {}

    for label, (stem, tick_size, tick_value, commission, nc, familia) in PRODUCTS.items():
        path = os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")
        if not os.path.exists(path):
            print(f"[SKIP] {label}: no existe {path}")
            continue
        df = pd.read_parquet(path)
        avg_range = avg_bar_range_ticks(df, tick_size)
        print(f"\n{'='*90}\n{label}  ({familia})  --  {len(df):,} barras RTH, rango promedio barra = {avg_range:.1f} ticks, nc<={nc}\n{'='*90}")

        candidates = []
        for w, rr in zip(WIDTH_MULTIPLIERS, RR_CANDIDATES):
            sl = max(1, round(avg_range * w))
            tp = max(1, round(sl * rr))
            candidates.append((sl, tp))

        best = None
        for sl, tp in candidates:
            br = measure_wr_bracket(df, sl, tp, HOLD, tick_size=tick_size)
            wr_alt = (br["wr_all_opt"] + br["wr_all_cons"]) / 2
            stats = combines_for(wr_alt, sl, tp, tick_value, commission, nc)
            row = {"producto": label, "familia": familia, "sl_ticks": sl, "tp_ticks": tp,
                   "rr": round(tp / sl, 3), "nc": nc, "wr_alternate": round(wr_alt, 4),
                   "wr_bracket_width": round(br["wr_all_opt"] - br["wr_all_cons"], 4), **stats}
            all_rows.append(row)
            print(f"  SL={sl:5d} TP={tp:5d} RR={tp/sl:.2f}  WR={wr_alt:.4f}  "
                  f"pass={stats['pass_rate']:.4f}  blow={stats['blow_rate']:.4f}  combines/año={stats['combines_ano']:.2f}")
            if best is None or row["combines_ano"] > best["combines_ano"]:
                best = row
                best_br = br

        winners[label] = (best, best_br, df, tick_value, commission, nc, tick_size)
        print(f"  >>> Mejor: SL={best['sl_ticks']}/TP={best['tp_ticks']} (RR={best['rr']}) -> {best['combines_ano']:.2f} combines/año")

    # ── Chequeo de sobreajuste temporal sobre el ganador de cada producto ──
    print(f"\n\n{'='*90}\nCHEQUEO DE SOBREAJUSTE TEMPORAL (H1 vs H2) SOBRE EL GANADOR DE CADA PRODUCTO\n{'='*90}")
    overfit_rows = []
    for label, (best, br_full, df, tick_value, commission, nc, tick_size) in winners.items():
        n = len(df)
        mid = n // 2
        h1, h2 = df.iloc[:mid], df.iloc[mid:]
        sl, tp = best["sl_ticks"], best["tp_ticks"]

        gaps = {}
        dir_results = {}
        for period_label, pdf in [("H1", h1), ("H2", h2)]:
            br = measure_wr_bracket(pdf, sl, tp, HOLD, tick_size=tick_size)
            wr_short = (br["wr_short_opt"] + br["wr_short_cons"]) / 2
            wr_alt = (br["wr_all_opt"] + br["wr_all_cons"]) / 2
            c_short = combines_for(wr_short, sl, tp, tick_value, commission, nc)["combines_ano"]
            c_alt = combines_for(wr_alt, sl, tp, tick_value, commission, nc)["combines_ano"]
            gaps[period_label] = c_short - c_alt
            dir_results[period_label] = (c_short, c_alt)

        both_positive = gaps["H1"] > 0 and gaps["H2"] > 0
        both_negative = gaps["H1"] < 0 and gaps["H2"] < 0
        consistent = both_positive or both_negative
        verdict = "direccion consistente ambas mitades" if consistent else "NO consistente -- sobreajuste, usar alternar"

        print(f"\n{label}: SL={sl}/TP={tp}")
        print(f"  H1: always_short={dir_results['H1'][0]:.2f}  alternate={dir_results['H1'][1]:.2f}  gap={gaps['H1']:+.2f}")
        print(f"  H2: always_short={dir_results['H2'][0]:.2f}  alternate={dir_results['H2'][1]:.2f}  gap={gaps['H2']:+.2f}")
        print(f"  -> {verdict}")

        overfit_rows.append({"producto": label, "gap_h1": round(gaps["H1"], 2), "gap_h2": round(gaps["H2"], 2),
                              "veredicto": verdict})

    df_all = pd.DataFrame(all_rows)
    df_all.to_csv(os.path.join(DATA_DIR, "camino_b_products_grid.csv"), index=False)
    df_overfit = pd.DataFrame(overfit_rows)
    df_overfit.to_csv(os.path.join(DATA_DIR, "camino_b_products_overfit.csv"), index=False)

    print(f"\n\n{'='*90}\nTABLA FINAL — MEJOR CANDIDATO POR PRODUCTO\n{'='*90}")
    final_rows = []
    for label, (best, br_full, df, tick_value, commission, nc, tick_size) in winners.items():
        ov = df_overfit[df_overfit.producto == label].iloc[0]
        final_rows.append({
            "producto": label, "sl_ticks": best["sl_ticks"], "tp_ticks": best["tp_ticks"],
            "rr": best["rr"], "nc": nc, "wr_alternate": best["wr_alternate"],
            "pass_rate": best["pass_rate"], "blow_rate": best["blow_rate"],
            "combines_ano": best["combines_ano"], "veredicto_temporal": ov["veredicto"],
        })
    df_final = pd.DataFrame(final_rows).sort_values("combines_ano", ascending=False)
    print(df_final.to_string(index=False))
    df_final.to_csv(os.path.join(DATA_DIR, "camino_b_products_final.csv"), index=False)


if __name__ == "__main__":
    main()
