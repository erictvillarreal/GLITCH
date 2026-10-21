"""Parte D (9): cadena anual con el WR como palanca (45/50/55 %) y la politica DP evaluada con fricciones. -> resultados_D9.md"""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
from xfa_dp import build_hist, dp_policy, solve
NB = 200000; NC = 50000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
P(f"# resultados_D9 (cadena anual; {NC} trayectorias; bancos de {NB}; reglas verificadas; MGC sin la ventana de oro; slip de entrada MGC 0)\n")
cb = {"P0 slip mezcla {1,3} (hoy)": combine_bank(mes, NB, "P0", (1.0, 3.0), (0.5, 0.5), seed=11), "P3 slip mezcla {1,3} (finish-line)": combine_bank(mes, NB, "P3", (1.0, 3.0), (0.5, 0.5), seed=11),
      "P0 slip 1": combine_bank(mes, NB, "P0", (1.0,), (1.0,), seed=11)}
P("## A. WR como palanca: neto anual por cuenta (media / mediana / p10–p90 / P(<0)); stop llenado a 0.5 (convención C1)\n")
P("| Combine | WR | candidato | cobrado por XFA | neto anual |\n|---|---|---|---|---|")
for frac in (0.5,):
    for wr in (0.45, 0.50, 0.55):
        dr = 0.0 if wr == 0.50 else drift_for_wr(clean, mk, wr)
        for cname, sl in (("a plan 3×364", 364), ("b 728×3", 728)):
            days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dr, stop_frac=frac)
            life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
            paid = pnet.sum(1).mean()
            for cn, (ps, ds) in cb.items():
                r = run_chain(ps, ds, life, pday, pnet, n=NC, seed=5); n_ = r["net"]
                P(f"| {cn} | {wr * 100:.0f} % | {cname} | ${paid:,.0f} | ${n_.mean():,.0f} / ${np.median(n_):,.0f} / ${np.percentile(n_, 10):,.0f}–${np.percentile(n_, 90):,.0f} / {np.mean(n_ < 0) * 100:.0f} % |")
# DP evaluada con fricciones (entrenada en W2 con stop exacto)
P("\n## B. Política DP (entrenada en W2, stop exacto, slip 0) evaluada con fricciones — cobrado por XFA\n")
NCS = (1, 2, 3, 4, 5, 6, 8); R = Rules(profit_rule=False)
P("| bracket | mundo / fricción | DP | nc 3 fijo | diferencia pareada |\n|---|---|---|---|---|")
from xfa_engine import simulate_life
for sl in (364, 728):
    dtr = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
    H, PL = build_hist(dtr, NCS, sl); Vp, Vq, pp, pq, ypp, ypq, its, dl = solve(H, PL, NCS, R)
    nc_fn, pay_fn = dp_policy(NCS, pp, pq, ypp, ypq)
    for lab, kw in (("stop exacto, slip 0", dict()), ("stop 0.5, slip 0", dict(stop_frac=0.5)), ("stop 0.5, slip 3 ticks", dict(stop_frac=0.5, slip=(3.0,))), ("stop 0.5, slip 10 ticks", dict(stop_frac=0.5, slip=(10.0,)))):
        k2 = dict(kw); slip = k2.pop("slip", (0.0,))
        dev = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=slip, mask=mk, cush_max=9000.0, **k2)
        r = simulate_life(dev, R, Policy("DP", nc_fn, pay_fn, sl, sl), n=50000, seed=20261020); r3 = simulate_life(dev, R, pol_fixed(3, sl, sl), n=50000, seed=20261020)
        d = r["paid"] - r3["paid"]
        P(f"| SL=TP={sl} | {lab} | ${r['paid'].mean():,.0f} | ${r3['paid'].mean():,.0f} | {d.mean():+,.0f} ± {1.96 * d.std() / np.sqrt(len(d)):,.0f} |")
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D9.md"), "w").write("\n".join(out))
