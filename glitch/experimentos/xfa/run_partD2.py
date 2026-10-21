"""Parte D (2): escenarios de reglas, slippage, consistencia, MES, H6, re-optimizacion para 50K (con mitades) y capa de costos. PREREGISTRO_D.md.

    GLITCH_MGC_PARQUET=... python run_partD2.py [--quick]   ->  resultados_D2.md
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import itertools
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from run_partD import HDR, fmt, metrics, row  # noqa: E402
from worlds import MGC, brownian_like, gold_mask, mgc_days  # noqa: E402
from xfa_engine import BarDays, Policy, Rules, SeqDays, pol_fixed, simulate_life  # noqa: E402

SEED = 20261020


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    N = 4000 if a.quick else 50000; NG = 3000 if a.quick else 20000
    t0 = time.time(); out = []
    P = lambda s="": (print(s, flush=True), out.append(s))
    clean = mgc_days(True); mk_ng = gold_mask(clean, True); mk_all = np.ones(clean.D, bool)
    brown, binfo = brownian_like(clean, mk_ng, D=6000 if a.quick else 40000)
    mkb = np.ones(brown.D, bool)
    B = lambda dd, mask, sl, tp, slip=(0.0,), cls=BarDays: cls(dd, MGC["tick_usd"], MGC["fee"], sl, tp, slip=slip, mask=mask, cush_max=9000.0)
    W = {"W2 MGC limpio SIN oro": (clean, mk_ng), "W3 Browniano sin deriva": (brown, mkb)}
    P(f"# resultados_D2 (N={N} vidas por celda; semilla {SEED}; reglas base del RULEBOOK salvo lo indicado)\n")

    # ── A. escenarios de reglas ──────────────────────────────────────────────────────────────────────────────────────
    scen = [("BASE (Standard, VERIFICADO)", Rules()), ("C  ruta Consistency (40 %, 3 días, tope $3,000)", Rules(path="cons", cap=3000.0)),
            ("R1 RTP: DLL $1,000 + ruta Consistency", Rules(path="cons", cap=3000.0, dll=1000.0)), ("F1 primeros $10k al 100 %", Rules(first100=10000.0)),
            ("T30 comisión de transferencia $30 por pago", Rules(wire_fee=30.0)), ("P2 saldo mínimo $1,500 para pedir pago", Rules(min_request_balance=1500.0)),
            ("W2 día ganador BRUTO de comisión", Rules(win_gross=True)), ("D4 tope $4,000 (DLL comprado, Standard)", Rules(cap=4000.0, dll=1000.0))]
    for wname, (dd, mask) in W.items():
        for cname, sl in (("a plan 3×364/364", 364), ("b 728×3 (stop = piso)", 728)):
            P(f"\n## A. Escenarios de reglas — {wname} — candidato {cname}\n"); P(HDR)
            for sname, R in scen:
                days = B(dd, mask, sl, sl)
                r = simulate_life(days, R, pol_fixed(3, sl, sl), n=N, seed=SEED)
                P(row(sname, metrics(r)))

    # ── B. slippage de entrada en MGC (NO medido): 0, 3 ticks, y peso relativo sobre el bracket ──────────────────────────
    P("\n## B. Slippage de entrada de MGC (ticks; supuesto, no medido) — W2, reglas base\n"); P(HDR)
    for cname, sl, tp in (("a 3×364/364", 364, 364), ("b 728×3", 728, 728), ("e1 TP 60/SL 364", 364, 60), ("e2 TP 70/SL 250", 250, 70)):
        for slip in (0.0, 3.0, 10.0):
            days = B(clean, mk_ng, sl, tp, (slip,))
            r = simulate_life(days, Rules(), pol_fixed(3, sl, tp), n=N, seed=SEED)
            P(row(f"{cname}, slip {slip:.0f} ticks (= {slip / tp * 100:.1f} % del TP)", metrics(r)))

    # ── C. consistencia: qué bracket es compatible con la ruta Consistency (hallazgo 4) ─────────────────────────────────
    P("\n## C. Ruta Consistency: P(pago) y cobro según el tamaño del bracket (3 micros, SL = TP; W2) \n"); P(HDR)
    for sl in (100, 150, 200, 250, 300, 364, 450):
        days = B(clean, mk_ng, sl, sl)
        r = simulate_life(days, Rules(path="cons", cap=3000.0), pol_fixed(3, sl, sl), n=N, seed=SEED)
        P(row(f"SL = TP = {sl} ticks (1 TP ≈ ${sl * 3 - 6:,.0f})", metrics(r)))

    # ── D. MES micros como competidor (d) ───────────────────────────────────────────────────────────────────────────────
    from daydata import load_days
    mes = load_days()
    P("\n## D. Competidor d: micros de MES (3 contratos, SL = TP = 291 ticks ≈ $1,092; entrada 9:30 CT; tope de escalado 20/30/50 micros), reglas base\n"); P(HDR)
    for slip in (0.0, 1.0, 3.0):
        days = BarDays(mes, 1.25, 1.22, 291, 291, slip=(slip,), cush_max=9000.0)
        r = simulate_life(days, Rules(product="MES"), pol_fixed(3, 291, 291), n=N, seed=SEED)
        P(row(f"d MES real 492 días, slip {slip:.0f} ticks (= {slip / 291 * 100:.1f} % del TP)", metrics(r)))

    # ── E. H6: no operar el día siguiente a un rango bajo ───────────────────────────────────────────────────────────────
    rng_ticks = clean.hi.max(1) - clean.lo.min(1)
    thr = np.percentile(rng_ticks, 25)
    P(f"\n## E. H6 (replay SECUENCIAL; no operar si el rango del día previo < percentil 25 = {thr:.0f} ticks) — W2\n"); P(HDR)
    sd = SeqDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk_ng, cush_max=9000.0)
    for lbl, skip in (("a sin filtro (secuencial)", False), ("H6 con filtro", True)):
        def nc_fn(st, sd=sd, skip=skip):
            if not skip or st.t == 0: return np.full(st.b.shape, 3)
            return np.where(rng_ticks[sd._last] < thr, 0, 3)
        r = simulate_life(sd, Rules(), Policy(lbl, nc_fn, "max", 364, 364), n=N, seed=SEED)
        P(row(lbl, metrics(r)))

    # ── F. re-optimización para 50K con mitades (hallazgo 1): 56 configuraciones ───────────────────────────────────────
    P(f"\n## F. Re-optimización para 50K: nc × (SL = TP) con selección en una mitad cronológica y evaluación en la otra (W2 sin oro; {NG} vidas por celda; 56 comparaciones)\n")
    idx_ng = np.nonzero(mk_ng)[0]; half = len(idx_ng) // 2
    mH1 = np.zeros(clean.D, bool); mH1[idx_ng[:half]] = True
    mH2 = np.zeros(clean.D, bool); mH2[idx_ng[half:]] = True
    ncs = (1, 2, 3, 4, 5, 6, 8); sls = (150, 200, 250, 300, 364, 450, 550, 728)
    base = {sl: B(clean, mk_ng, sl, sl) for sl in sls}
    grid = {}
    for sl in sls:
        for nc in ncs:
            for hn, m in (("H1", mH1), ("H2", mH2), ("ALL", mk_ng)):
                base[sl].pool = np.nonzero(m)[0]
                r = simulate_life(base[sl], Rules(), pol_fixed(nc, sl, sl), n=NG, seed=SEED)
                grid[(nc, sl, hn)] = (r["paid"].mean(), r["paid"].std() / np.sqrt(NG), (r["npay"] > 0).mean())
    P("Cobrado medio por XFA ($) — mitad H1 / mitad H2 / todos (fila = SL = TP en ticks, columna = nc):\n")
    P("| SL=TP \\ nc | " + " | ".join(str(n) for n in ncs) + " |\n|---|" + "---|" * len(ncs))
    for sl in sls:
        P(f"| {sl} | " + " | ".join(f"{grid[(nc, sl, 'H1')][0]:,.0f} / {grid[(nc, sl, 'H2')][0]:,.0f} / {grid[(nc, sl, 'ALL')][0]:,.0f}" for nc in ncs) + " |")
    for sel, ev in (("H1", "H2"), ("H2", "H1")):
        best = max(itertools.product(ncs, sls), key=lambda k: grid[(k[0], k[1], sel)][0])
        a3 = grid[(3, 364, ev)]; bv = grid[(best[0], best[1], ev)]
        P(f"\nSelección en {sel}: mejor = nc {best[0]}, SL=TP {best[1]} (cobrado {grid[(best[0], best[1], sel)][0]:,.0f} en {sel}); evaluado en {ev}: **{bv[0]:,.0f} ± {1.96 * bv[1]:,.0f}** vs plan actual 3×364 en {ev}: {a3[0]:,.0f} ± {1.96 * a3[1]:,.0f}.")
    bestall = max(itertools.product(ncs, sls), key=lambda k: grid[(k[0], k[1], 'ALL')][0])
    P(f"\nMejor global (informativo, in-sample): nc {bestall[0]}, SL=TP {bestall[1]}: {grid[(bestall[0], bestall[1], 'ALL')][0]:,.0f} ± {1.96 * grid[(bestall[0], bestall[1], 'ALL')][1]:,.0f}; plan actual: {grid[(3, 364, 'ALL')][0]:,.0f}.")
    P(f"\n(tiempo {time.time() - t0:.0f}s)")
    open(os.path.join(HERE, "resultados_D2.md"), "w").write("\n".join(out))


if __name__ == "__main__":
    main()
