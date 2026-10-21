"""Parte A, escenarios y sensibilidades (§2.8, §2.9). Un solo comando:  python run_partA2.py [--quick]
Escribe resultados_A2.md. Requiere los mismos datos que run_partA.py. Semillas fijas."""
from __future__ import annotations

import argparse
import time

import numpy as np

import dp as DP
from daydata import FEE_RT, TICK_USD, load_days, sim_day
from m1 import fit, make_days, real_profile
from run_partA import EXIT_SLIP, SEED, SLIP_P, SLIPS, START, md_table, tabs_for
from sim import (MLL, NC_MAX, RESET_FEE, START_IDX, SUB_PER_DAY, TARGET, OutcomeTable, pol_fixed, pol_p2, pol_p3, pol_p4,
                 pol_p4b, run_mc, sl_full_cost_per_contract)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    N = 4000 if a.quick else 30000
    t0 = time.time(); out = []
    log = lambda s: (out.append(s), print(s, flush=True))
    dd = load_days()
    H0, LIQ0 = DP.build_hist(dd, SLIPS, SLIP_P, EXIT_SLIP)
    # DP PRINCIPAL = lado-neutral (promedio LONG/SHORT): la asimetria long/short de esta muestra es anecdotica (encargo §3.1)
    # y dejaria a la DP 'saltar' los dias de un lado. La DP lado-especifica (H0) se reporta solo como referencia.
    H = H0.copy(); H[:] = H0.mean(axis=0, keepdims=True); LIQ = LIQ0.copy(); LIQ[:] = LIQ0.mean(axis=0, keepdims=True)
    # DP P(pase): dos paridades de inicio (hoy SHORT / hoy LONG), horizonte 60
    Vs_s, pol_s, Q0_s = DP.solve(H, LIQ, START_IDX, horizon=60, want_q0=True)       # t=0 = SHORT (START_IDX impar)
    Vs_l, pol_l, Q0_l = DP.solve(H, LIQ, START_IDX + 1, horizon=60, want_q0=True)   # t=0 = LONG
    C, polc, F, Qc = DP.solve_cost(H, LIQ, SUB_PER_DAY, RESET_FEE, delay=0.0, sweeps=400, want_q=True)
    C8, polc8, F8, Qc8 = DP.solve_cost(H, LIQ, SUB_PER_DAY, RESET_FEE, delay=8.0, sweeps=400, want_q=True)
    pi, bi = DP.idx_state(round(START["bal"] / 25) * 25, round(START["peak"] / 25) * 25)
    Vs_ref, pol_ref = DP.solve(H0, LIQ0, START_IDX, horizon=60)
    log(f"# resultados_A2 (N={N}; semilla {SEED})\n")
    log(f"DP lado-especifica (referencia, hoy SHORT con los datos reales): P(pase) optima = {Vs_ref[0, pi, bi] * 100:.1f}% (nc hoy {pol_ref[0, pi, bi]}); DP lado-neutral (principal) = {Vs_s[0, pi, bi] * 100:.1f}% (nc hoy {pol_s[0, pi, bi]}).\n")

    # ── A2.1 manana (miercoles 21-oct, SHORT) ────────────────────────────────────────────────────────────────
    cush = START["bal"] - min(START["peak"] - MLL, 50000.0)
    cost1 = sl_full_cost_per_contract()
    nc_safe_analytic = int(np.floor(cush / cost1))
    log(f"## Manana (miercoles 21-oct, SHORT por paridad, day_index={START_IDX}). Colchon = ${cush:,.1f}")
    log(f"Costo por contrato de un SL completo con slip entrada 3 + slip salida {EXIT_SLIP:.0f} (supuesto): "
        f"({100}+3+{EXIT_SLIP:.0f}) ticks x $1.25 + $1.22 = **${cost1:.2f}** -> nc maximo que hace IMPOSIBLE liquidar en un dia = floor({cush:.0f}/{cost1:.2f}) = **{nc_safe_analytic}**, margen = **${cush - nc_safe_analytic * cost1:,.2f}**.")
    # chequeo empirico: mayor nc con 0 liquidaciones en los 492 dias reales (slip entrada 3, salida 3)
    nc_emp = 0
    for nc in range(1, NC_MAX + 1):
        k, p = sim_day(dd, -1, nc, cush, slip=3.0, exit_slip=EXIT_SLIP)
        if (k == 2).sum() == 0: nc_emp = nc
        else: break
    log(f"Chequeo empirico (replay de {dd.D} dias reales, SHORT, slip 3/3): mayor nc sin ninguna liquidacion = {nc_emp}.\n")
    rows = []
    for nc in (1, 2, 3, 5, 8, 10, 12, nc_safe_analytic, nc_safe_analytic + 1, 18, 20, 25, 30, 35, 40):
        fr = np.zeros(4); e = 0.0
        for slip, w in zip(SLIPS, SLIP_P):
            k, p = sim_day(dd, -1, nc, cush, slip=slip, exit_slip=EXIT_SLIP)
            fr += w * np.array([(k == i).mean() for i in range(4)]); e += w * p.mean()
        tp_net = {s: (32 - s) * nc * TICK_USD - nc * FEE_RT for s in SLIPS}
        q = Q0_s[nc, pi, bi]; qc = Qc[1, nc, pi, bi]; qc8 = Qc8[1, nc, pi, bi]
        rows.append([nc, f"{fr[0] * 100:.1f}%", f"{fr[1] * 100:.1f}%", f"{fr[2] * 100:.1f}%", f"{fr[3] * 100:.1f}%", f"{e:+,.0f}",
                     f"+{tp_net[1]:,.0f} / +{tp_net[3]:,.0f}", f"-{min(cush, nc * cost1):,.0f}", f"{q * 100:.1f}%", f"${qc:,.0f}", f"${qc8:,.0f}"])
    log(md_table(rows, ["nc hoy", "P(TP)", "P(SL)", "P(LIQUIDA)", "P(flatten)", "P&L esp. dia", "neto TP (slip1 / slip3)", "perdida SL (tope=colchon)",
                        "P(pase) total con continuacion OPTIMA (DP)", "costo de bolsillo esp. hasta pasar (DP)", "idem con $8/dia de demora (DP)"]))
    log(f"\nP(pase) optima DP (cualquier nc hoy) = {Vs_s[0, pi, bi] * 100:.1f}%, nc optimo hoy = {pol_s[0, pi, bi]}; costo optimo = ${C[1][pi, bi]:,.0f} (nc optimo hoy {polc[1][pi, bi]}); techo teorico {(START['bal'] - 49401.2) / (TARGET - 49401.2) * 100:.1f}%.")
    log(f"Costo esperado de bolsillo desde una cuenta NUEVA (50,000/50,000): ${F[1]:,.0f} (empieza SHORT) / ${F[0]:,.0f} (empieza LONG).\n")

    # ── A2.2 "a $100 de la meta" ───────────────────────────────────────────────────────────────────────────────
    log("## A $100 de la meta (peak = bal >= 52,000 -> piso congelado en 50,000; colchon = bal - 50,000). Promedio de empezar SHORT y LONG.")
    tabs = tabs_for(dd)
    rows = []
    for bal in (52700.0, 52800.0, 52900.0, 52950.0):
        cu = bal - 50000.0
        pols = [("40 fijo", pol_fixed(40)), ("20 fijo", pol_fixed(20)), ("10 fijo", pol_fixed(10)), ("5 fijo", pol_fixed(5)),
                ("3 fijo", pol_fixed(3)), ("1 fijo", pol_fixed(1)), ("P3 finish-line", pol_p3())]
        for pname, pol in pols:
            rs = [run_mc(pol, tabs, n=N, seed=SEED + 7, bal0=bal, peak0=bal, start_idx=si_, slip_mix=(SLIPS, SLIP_P), maxdays=60) for si_ in (START_IDX, START_IDX + 1)]
            pp = np.mean([r.p_pass for r in rs]); pl = np.mean([r.p_liq for r in rs]); op = np.mean([r.p_open for r in rs])
            dm = np.mean([r.days_pass[0] for r in rs]); lo = min(r.ci_pass[0] for r in rs); hi = max(r.ci_pass[1] for r in rs)
            rows.append([f"{bal:,.0f} (faltan {TARGET - bal:,.0f})", pname, f"{pp * 100:.1f}% [{lo * 100:.1f},{hi * 100:.1f}]", f"{pl * 100:.1f}%", f"{op * 100:.1f}%", f"{dm:.0f}"])
        pi_, bi_ = DP.idx_state(bal, bal)
        vd = (Vs_s[0, pi_, bi_] + Vs_l[0, pi_, bi_]) / 2
        rows.append([f"{bal:,.0f} (faltan {TARGET - bal:,.0f})", f"**DP optima** (nc hoy SHORT={pol_s[0, pi_, bi_]}, LONG={pol_l[0, pi_, bi_]})", f"{vd * 100:.1f}%", f"{(1 - vd) * 100:.1f}% (incl. abiertas)", "-", "-"])
    log(md_table(rows, ["balance", "politica", "P(pase) [IC]", "P(liquidar antes de pasar)", "abierto a 60 dias", "dias a pase (mediana)"]))

    # ── A2.3 sensibilidades ───────────────────────────────────────────────────────────────────────────────────
    log("\n## Sensibilidades (P(pase) %, n=" + str(N) + " por celda; estado de partida; politicas P0=40 fijo, P2=SL-safe, P3=finish-line, P4=min(P2,P3), P4b=40 hoy y luego P4)")
    prof = real_profile(dd)
    _, sg, s_ln, _ = fit(prof, (0.657, 0.239, 0.105), with_ln=True, D=6000)
    pset = [("P0", pol_fixed(40)), ("P2", pol_p2()), ("P3", pol_p3()), ("P4", pol_p4()), ("P4b", pol_p4b())]
    def cell(label, d=dd, mix=(SLIPS, SLIP_P), exit_slip=EXIT_SLIP, order="adverse", tp=32, drift=0.0, fee=FEE_RT, block=1, ratchet=True, slip_set=None):
        slips = slip_set or mix[0]
        tb = {s: OutcomeTable(d, s, exit_slip, order, 100, tp, drift=drift, fee=fee) for s in slips}
        res = []
        for pn, pol in pset:
            r = run_mc(pol, tb, n=N, seed=SEED + 11, bal0=START["bal"], peak0=START["peak"], slip_mix=mix, block=block, ratchet=ratchet)
            res.append(f"{r.p_pass * 100:.1f}")
        return [label] + res
    rows = [cell("BASE (M2 iid, slip {1,3}, salida 3, TP 32)")]
    for sg_mult in (0.8, 1.2):
        d = make_days(20000 if not a.quick else 5000, sg * sg_mult, s_ln, prof, seed=5)
        rows.append(cell(f"M1 sigma x{sg_mult} (sigma_dia={sg * sg_mult:.0f})", d=d))
    for dr in (-2.0, 2.0, 5.0):
        rows.append(cell(f"deriva a favor {dr:+.0f} ticks/dia (M3)", drift=dr))
    for s in (0, 1, 3, 5):
        rows.append(cell(f"slip entrada fijo {s}", mix=([s], [1.0])))
    for es in (0, 1, 5):
        rows.append(cell(f"slip salida SL {es}", exit_slip=float(es)))
    for tp in (31, 33):
        rows.append(cell(f"TP efectivo {tp} ticks", tp=tp))
    rows.append(cell("orden intra-barra OHLC (en vez de adverso primero)", order="ohlc"))
    rows.append(cell("sin ratchet (piso = pico - 2000 siempre)", ratchet=False))
    rows.append(cell("sin comision", fee=0.0))
    rows.append(cell("bloques de 5 dias (vs iid)", block=5))
    log(md_table(rows, ["escenario", "P0 40 fijo", "P2 SL-safe", "P3 finish-line", "P4 min(P2,P3)", "P4b 40 hoy+P4"]))
    open("resultados_A2.md", "w").write("\n".join(out)); print(f"\nlisto en {time.time() - t0:.0f}s -> resultados_A2.md")


if __name__ == "__main__":
    main()
