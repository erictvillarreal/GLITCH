"""Corre toda la Parte A y escribe resultados_A.md (tablas). Un solo comando:

    python run_partA.py            # completo (~10-20 min)
    python run_partA.py --quick    # n reducido, para depurar

Semillas fijas. Estado de partida parametrizado en START (confirmar con el encabezado de TopstepX).
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np

import dp as DP
from daydata import FEE_RT, TICK_USD, load_days
from m1 import fit, make_days, real_profile
from sim import (CONSIST_CAP, MLL, NC_MAX, RESET_FEE, START_IDX, SUB_PER_DAY, TARGET, Ctx, OutcomeTable, pol_fixed,
                 pol_p2, pol_p3, pol_p4, pol_p4b, pol_p5, pol_p6, run_mc, side_of, sl_full_cost_per_contract,
                 tp_net_per_contract)

START = dict(bal=51401.2, peak=51401.2)          # SUPUESTO: confirmar con TopstepX (BAL y MLL). Fuente: encargo §1.
SLIPS, SLIP_P = [1, 3], [0.5, 0.5]               # "empirica": lun 19-oct = 1 tick; mar 20-oct ~3 ticks (inferido). N=2, ver REPORTE_A.
EXIT_SLIP = 3.0                                  # SUPUESTO (sin medicion): gap de salida en SL, igual al peor slippage de entrada observado.
SEED = 20261020


def tabs_for(dd, slips=SLIPS, exit_slip=EXIT_SLIP, order="adverse", sl=100, tp=32, drift=0.0, step=10.0):
    return {s: OutcomeTable(dd, s, exit_slip, order, sl, tp, step=step, drift=drift) for s in slips}


def fmt(r, with_cost=False):
    lo, hi = r.ci_pass
    return (f"{r.p_pass * 100:.1f}% [{lo * 100:.1f},{hi * 100:.1f}] / {r.p_liq * 100:.1f}% / {r.p_open * 100:.1f}% / "
            f"{r.days_pass[0]:.0f} ({r.days_pass[1]:.0f}-{r.days_pass[2]:.0f}) / {r.p_liq_day1 * 100:.1f}%")


def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def total_cost(r_cur, r_fresh):
    """Costo de bolsillo esperado para llegar a pasar (renovacion): suscripcion por dia habil + $49 por cada liquidacion."""
    c_cur = SUB_PER_DAY * r_cur.mean_days + RESET_FEE * r_cur.p_liq
    c_f = SUB_PER_DAY * r_fresh.mean_days + RESET_FEE * r_fresh.p_liq
    p_f = max(r_fresh.p_pass, 1e-9)
    F = c_f / p_f
    days = r_cur.mean_days + r_cur.p_liq * (r_fresh.mean_days / p_f)
    return c_cur + r_cur.p_liq * F, days, r_fresh


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    N = 5000 if a.quick else 50000
    t0 = time.time(); out = []
    log = lambda s: (out.append(s), print(s, flush=True))
    dd = load_days()
    log(f"# resultados_A (generado por run_partA.py; N={N} por celda; semilla base {SEED})\n")
    log(f"Datos: {dd.D} dias completos de {dd.D + len(dd.dropped)} (MES 5min, {dd.dates[0]} -> {dd.dates[-1]}); {len(dd.dropped)} descartados (cierres anticipados/huecos).")
    log(f"Estado de partida (SUPUESTO a confirmar): bal={START['bal']}, peak={START['peak']}, piso={min(START['peak'] - MLL, 50000)}, meta={TARGET}, "
        f"slip entrada {{1,3}} 50/50, slip salida SL supuesto {EXIT_SLIP}, comision {FEE_RT}/contrato, suscripcion ${SUB_PER_DAY:.2f}/dia habil, reset ${RESET_FEE}.\n")

    # ── modelos ───────────────────────────────────────────────────────────────────────────────────────────────
    prof = real_profile(dd)
    e1, sg1, s1, sh1 = fit(prof, tuple(np.array([0.657, 0.239, 0.105])), with_ln=True, D=8000)      # M1 calibrado a los DATOS (TP40/SL100)
    e2, sg2, s2, sh2 = fit(prof, (0.59, 0.24, 0.17), with_ln=True, D=8000)                         # M1 calibrado al DOC 7-oct (59/24/17)
    log(f"M1-datos: sigma_dia={sg1:.0f} ticks, s_lognormal={s1:.1f}, shares TP40/SL100 {np.round(sh1, 3)} (objetivo M2 real 0.657/0.239/0.105)")
    log(f"M1-doc  : sigma_dia={sg2:.0f} ticks, s_lognormal={s2:.1f}, shares TP40/SL100 {np.round(sh2, 3)} (objetivo doc 7-oct 0.59/0.24/0.17; NO reproducible con los datos reales: M2 da 0.657/0.239/0.105)\n")
    D_SYN = 30000 if not a.quick else 6000
    models = {
        "M2 iid": (dd, tabs_for(dd), 1),
        "M2 bloques5": (dd, tabs_for(dd), 5),
        "M2 orden OHLC": (dd, tabs_for(dd, order="ohlc"), 1),
        "M1-datos": (None, None, 1),
        "M1-doc": (None, None, 1),
    }
    syn = {"M1-datos": make_days(D_SYN, sg1, s1, prof, seed=1), "M1-doc": make_days(D_SYN, sg2, s2, prof, seed=2)}
    for k, d in syn.items():
        models[k] = (d, tabs_for(d), 1)

    # ── A1: politicas x modelos ───────────────────────────────────────────────────────────────────────────────
    pols = [("P0 40 fijo", pol_fixed(40))] + [(f"P1 {n} fijo", pol_fixed(n)) for n in (5, 10, 15, 20, 25, 30, 35)] + [
        ("P2 SL-safe", pol_p2()), ("P3 finish-line", pol_p3()), ("P4 min(P2,P3)", pol_p4()), ("P4b 40 hoy y P4", pol_p4b()), ("P5 P2->P3 piso congelado", pol_p5()),
        ("P6 P4 + saltar si colchon<500", pol_p6(500, pol_p4())), ("P6 P4 + saltar si colchon<1000", pol_p6(1000, pol_p4()))]
    # DP optima (benchmark): resuelta con M2 iid
    H0, LIQ0 = DP.build_hist(dd, SLIPS, SLIP_P, EXIT_SLIP)
    H = H0.copy(); H[:] = H0.mean(axis=0, keepdims=True); LIQ = LIQ0.copy(); LIQ[:] = LIQ0.mean(axis=0, keepdims=True)   # DP lado-neutral
    Vs, pols_dp = DP.solve(H, LIQ, START_IDX, horizon=60)
    pi0, bi0 = DP.idx_state(round(START["bal"] / 25) * 25, round(START["peak"] / 25) * 25)
    log(f"DP (value iteration, horizonte 60 dias, M2 iid): P(pase) optimo desde estado de partida = {Vs[0, pi0, bi0] * 100:.1f}%  (techo teorico {(START['bal'] - 49401.2) / (TARGET - 49401.2) * 100:.1f}%); nc optimo dia 1 = {pols_dp[0, pi0, bi0]}\n")
    np.save("pols_dp.npy", pols_dp)
    rows_by_model = {}
    for mi, (mname, (d, tabs, blk)) in enumerate(models.items()):
        log(f"\n## A1 - {mname}: politicas desde el estado de partida (n={N}, maximo 60 dias)\n")
        rows = []
        res_m = {}
        for pname, pol in pols:
            r = run_mc(pol, tabs, n=N, seed=SEED + mi, bal0=START["bal"], peak0=START["peak"], slip_mix=(SLIPS, SLIP_P), block=blk)
            res_m[pname] = r
            rf = run_mc(pol, tabs, n=N // 2, seed=SEED + 100 + mi, bal0=50000.0, peak0=50000.0, slip_mix=(SLIPS, SLIP_P), block=blk)
            cost, days, _ = total_cost(r, rf)
            rows.append([pname, fmt(r), f"${cost:,.0f}", f"{days:.1f}"])
        if mname == "M2 iid":
            from dp import policy_from_dp
            pdp = policy_from_dp(pols_dp, START_IDX)
            r = run_mc(pdp, tabs, n=N, seed=SEED + mi, bal0=round(START['bal'] / 25) * 25, peak0=round(START['peak'] / 25) * 25, slip_mix=(SLIPS, SLIP_P), snap=25.0)
            rows.append(["PD (DP optima lado-neutral, rejilla $25)", fmt(r), "-", "-"])
        log(md_table(rows, ["politica", "P(pase) [IC95%] / P(liq) / abierto60 / dias a pase med (p10-p90) / P(liq dia 1)", "costo de bolsillo esperado hasta pasar", "dias habiles esperados hasta pasar"]))
        rows_by_model[mname] = res_m

    open("resultados_A.md", "w").write("\n".join(out)); print(f"\nlisto en {time.time() - t0:.0f}s -> resultados_A.md")


if __name__ == "__main__":
    main()
