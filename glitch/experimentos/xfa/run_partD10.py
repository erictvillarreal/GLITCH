"""Parte D (10): reglas SIMPLES de (tamano, cobro) que Eric pueda operar, derivadas de la estructura de la DP; EXPLORATORIA (48 reglas x 2 brackets), con seleccion en una mitad y evaluacion en la otra.
Regla = (nc_inicial mientras balance < B1, nc_despues, umbral de balance para pedir el pago maximo cuando hay >= 5 dias ganadores). -> resultados_D10.md"""
import itertools, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
SEED = 20261020; NG = 20000
clean = mgc_days(True); mk = gold_mask(clean, True); idx = np.nonzero(mk)[0]; h = len(idx) // 2
mH1 = np.zeros(clean.D, bool); mH1[idx[:h]] = True; mH2 = np.zeros(clean.D, bool); mH2[idx[h:]] = True
out = []; P = lambda s="": (print(s, flush=True), out.append(s)); t0 = time.time()
P("# resultados_D10 (EXPLORATORIA: reglas simples de tamaño y cobro; reglas base verificadas; MGC limpio sin oro; stop exacto, slip 0; 20,000 vidas por celda; 48 reglas por bracket)\n")
B1 = 1500.0
for sl in (364, 728):
    base = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
    res = {}
    rules = list(itertools.product((3, 4, 6, 8), (1, 2, 3), (250.0, 1500.0, 3000.0, 4000.0)))
    for (n1, n2, thr) in rules:
        pol = Policy("r", lambda st, n1=n1, n2=n2: np.where(st.b < B1, n1, n2), lambda st, gmax, thr=thr: np.where(st.b >= thr, gmax, 0.0), sl, sl)
        for hn, m in (("H1", mH1), ("H2", mH2), ("ALL", mk)):
            base.pool = np.nonzero(m)[0]
            r = simulate_life(base, Rules(), pol, n=NG, seed=SEED)
            res[(n1, n2, thr, hn)] = (r["paid"].mean(), r["paid"].std() / np.sqrt(NG), (r["npay"] > 0).mean())
    ref = {}
    for hn, m in (("H1", mH1), ("H2", mH2), ("ALL", mk)):
        base.pool = np.nonzero(m)[0]; r = simulate_life(base, Rules(), pol_fixed(3, sl, sl), n=NG, seed=SEED); ref[hn] = (r["paid"].mean(), r["paid"].std() / np.sqrt(NG), (r["npay"] > 0).mean())
    P(f"\n## SL = TP = {sl}: nc 3 fijo y cobro al llegar a 5 días ganadores (plan actual): H1 ${ref['H1'][0]:,.0f} · H2 ${ref['H2'][0]:,.0f} · todos ${ref['ALL'][0]:,.0f}\n")
    P("| nc inicial (b < $1,500) | nc después | pedir pago si b ≥ | H1 | H2 | todos [P(≥1 pago)] |\n|---|---|---|---|---|---|")
    top = sorted(rules, key=lambda k: -res[(*k, "ALL")][0])[:12]
    for k in top:
        P(f"| {k[0]} | {k[1]} | ${k[2]:,.0f} | ${res[(*k, 'H1')][0]:,.0f} | ${res[(*k, 'H2')][0]:,.0f} | ${res[(*k, 'ALL')][0]:,.0f} ± {1.96 * res[(*k, 'ALL')][1]:,.0f} [{res[(*k, 'ALL')][2] * 100:.0f} %] |")
    for sel, ev in (("H1", "H2"), ("H2", "H1")):
        kb = max(rules, key=lambda k: res[(*k, sel)][0]); v = res[(*kb, ev)]
        P(f"\nSelección en {sel}: nc {kb[0]}→{kb[1]}, pedir si b ≥ ${kb[2]:,.0f} (${res[(*kb, sel)][0]:,.0f} en {sel}); evaluada en {ev}: **${v[0]:,.0f} ± {1.96 * v[1]:,.0f}** vs plan actual en {ev}: ${ref[ev][0]:,.0f} ± {1.96 * ref[ev][1]:,.0f}.")
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D10.md"), "w").write("\n".join(out))
