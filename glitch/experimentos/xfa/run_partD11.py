"""Parte D (11): reglas simples SIN loteria (nc inicial 3-4: el stop del bracket manda, no el piso) y cobro; mismas mitades. -> resultados_D11.md"""
import itertools, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
SEED = 20261020; NG = 30000
clean = mgc_days(True); mk = gold_mask(clean, True); idx = np.nonzero(mk)[0]; h = len(idx) // 2
mH1 = np.zeros(clean.D, bool); mH1[idx[:h]] = True; mH2 = np.zeros(clean.D, bool); mH2[idx[h:]] = True
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_D11 (reglas simples SIN lotería: con 3-4 micros el SL de 364 ticks ($1,092–$1,456) es menor que el colchón inicial; stop exacto, slip 0; 30,000 vidas)\n")
for sl in (364,):
    base = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
    P("| regla | H1 | H2 | todos [P(≥1)] | P(liquidar el día 1) |\n|---|---|---|---|---|")
    rows = [("plan actual: 3 fijo, pedir al tener 5 días ganadores", lambda st: np.full(st.b.shape, 3), 0.0)]
    for n1, n2, thr in itertools.product((3, 4), (1, 2, 3), (250.0, 1500.0)):
        rows.append((f"{n1} micros hasta $1,500 de saldo y {n2} después; pedir si saldo ≥ ${thr:,.0f}", lambda st, n1=n1, n2=n2: np.where(st.b < 1500.0, n1, n2), thr))
    for lab, nc_fn, thr in rows:
        pol = Policy(lab, nc_fn, (lambda st, g, thr=thr: np.where(st.b >= thr, g, 0.0)), sl, sl)
        cells = []
        for m in (mH1, mH2, mk):
            base.pool = np.nonzero(m)[0]
            r = simulate_life(base, Rules(), pol, n=NG, seed=SEED); cells.append(r)
        P(f"| {lab} | ${cells[0]['paid'].mean():,.0f} | ${cells[1]['paid'].mean():,.0f} | ${cells[2]['paid'].mean():,.0f} ± {1.96 * cells[2]['paid'].std() / np.sqrt(NG):,.0f} [{(cells[2]['npay'] > 0).mean() * 100:.0f} %] | {np.mean(cells[2]['life'] == 1) * 100:.1f} % |")
open(os.path.join(HERE, "resultados_D11.md"), "w").write("\n".join(out))
