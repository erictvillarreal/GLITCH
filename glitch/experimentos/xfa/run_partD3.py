"""Parte D (3): politica optima de (tamano, cobro) por DP y validacion con Monte Carlo del motor completo (sin la regla de ganancia desde el ultimo pago, que la DP no impone).
    GLITCH_MGC_PARQUET=... python run_partD3.py [--quick] -> resultados_D3.md"""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from run_partD import HDR, metrics, row
from worlds import MGC, brownian_like, gold_mask, mgc_days
from xfa_dp import build_hist, dp_policy, solve
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
SEED = 20261020
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
N = 4000 if a.quick else 50000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
clean = mgc_days(True); mk_ng = gold_mask(clean, True)
NCS = (1, 2, 3, 4, 5, 6, 8)
R = Rules(profit_rule=False)
P(f"# resultados_D3 (DP de (tamano, cobro); N={N} vidas de validacion; semilla {SEED}; reglas base SIN la regla de ganancia desde el ultimo pago)\n")
P("Estados en rejilla de $50; transicion = distribucion empirica de W2 (MGC limpio SIN oro, ambos lados mezclados); acciones nc en " + str(NCS) + " y pedir/esperar el pago maximo cuando wd = 5.\n")
P(HDR)
for sl in (364, 550, 728):
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk_ng, cush_max=9000.0)
    H, PL = build_hist(days, NCS, sl)
    Vpre, Vpost, pp, pq, ypp, ypq, its, delta = solve(H, PL, NCS, R)
    v0 = Vpre[0, 0, 40]
    nc_fn, pay_fn = dp_policy(NCS, pp, pq, ypp, ypq)
    pol = Policy(f"DP SL=TP={sl}", nc_fn, pay_fn, sl, sl)
    r = simulate_life(days, R, pol, n=N, seed=SEED)
    P(row(f"DP SL=TP={sl}: V0 de la DP = ${v0:,.0f} ({its} barridos, delta {delta:.3f}); MC del motor completo:", metrics(r)))
    r3 = simulate_life(days, R, pol_fixed(3, sl, sl), n=N, seed=SEED)
    P(row(f"  referencia: nc 3 fijo, SL=TP={sl}, cobro al maximo (mismo motor y reglas)", metrics(r3)))
    # politica en estados de interes
    P(f"  nc optimo (indice -> nc) al inicio (b=0, wd=0): {NCS[pp[0, 0, 40]]}; wd=4, b=900 post: {NCS[pq[4, 18]]}; wd=5 b=1500 post: {NCS[pq[5, 30]]}, pedir pago: {bool(ypq[5, 30])}; wd=5 b=3000: pedir {bool(ypq[5, 60])}")
# ── fuera de muestra: la politica entrenada en W2 se evalua en W1 (con oro) y W3 (Browniano); y entrenada en una mitad -> evaluada en la otra ──
brown, binfo = brownian_like(clean, mk_ng, D=6000 if a.quick else 40000)
mk_all = np.ones(clean.D, bool); idx = np.nonzero(mk_ng)[0]; h = len(idx) // 2
mH1 = np.zeros(clean.D, bool); mH1[idx[:h]] = True; mH2 = np.zeros(clean.D, bool); mH2[idx[h:]] = True
P("\n## Fuera de muestra (la DP se entrena SOLO con los dias de entrenamiento; el motor completo evalua en otros dias/mundos)\n"); P(HDR)
for sl in (364, 728):
    for tr_name, tr_mask, ev_list in (("W2", mk_ng, (("W1 con oro (incluye dias de entrenamiento)", clean, mk_all), ("W3 Browniano", brown, np.ones(brown.D, bool)))),
                                      ("H1", mH1, (("H2", clean, mH2),)), ("H2", mH2, (("H1", clean, mH1),))):
        dtr = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=tr_mask, cush_max=9000.0)
        H, PL = build_hist(dtr, NCS, sl)
        Vpre, Vpost, pp, pq, ypp, ypq, its, delta = solve(H, PL, NCS, R)
        nc_fn, pay_fn = dp_policy(NCS, pp, pq, ypp, ypq)
        for ev_name, ev_dd, ev_mask in ev_list:
            dev = BarDays(ev_dd, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=ev_mask, cush_max=9000.0)
            r = simulate_life(dev, R, Policy("DP", nc_fn, pay_fn, sl, sl), n=N, seed=SEED)
            r3 = simulate_life(dev, R, pol_fixed(3, sl, sl), n=N, seed=SEED)
            d = r["paid"] - r3["paid"]
            P(row(f"DP entrenada en {tr_name}, SL=TP={sl}, evaluada en {ev_name}", metrics(r)))
            P(row(f"  vs nc 3 fijo (mismo mundo): diferencia pareada {d.mean():+,.0f} ± {1.96 * d.std() / np.sqrt(len(d)):,.0f}", metrics(r3)))
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D3.md"), "w").write("\n".join(out))
