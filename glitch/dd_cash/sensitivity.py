import numpy as np
from dd_cash.data import build
from dd_cash.engine import Account, simulate
from core.prop_firm import TOPSTEP_50K, TOPSTEP_100K, TOPSTEP_150K
from core.funded_account import XFA_50K, XFA_100K, XFA_150K
OPS = 45.0; T, H = 20000, 252
df = build(); n = len(df)
SIZES = {"50K": (TOPSTEP_50K, XFA_50K, 3, 40), "100K": (TOPSTEP_100K, XFA_100K, 4, 80), "150K": (TOPSTEP_150K, XFA_150K, 6, 120)}
pc = lambda x: " ".join(f"{v:8,.0f}" for v in np.percentile(x, [10, 25, 50, 75, 90]))
def run(label, lo, hi):
    sub = df.iloc[lo:hi]; mgc, mes = sub.mgc.values, sub.mes.values
    D = np.random.default_rng(7).integers(0, len(sub), (T, H))
    for size in SIZES:
        cs, xs, ncx, ncg = SIZES[size]
        for pipe in "AB":
            a = Account(cs, xs, ncx if pipe == "A" else ncg, ncx, mgc if pipe == "A" else mes, mgc)
            r = simulate(a, D); tot = r["pay_m"].sum(1); nm = (r["pay_m"] - r["fee_m"] - OPS)[:, 3:].ravel()
            fp = r["first_pass"]
            print(f"{label:9s} {size:>4}-{pipe} payout/año {pc(tot)} | media {tot.mean():7,.0f} | mes P(payout=0) {np.mean(r['pay_m'][:,3:]<=0):.2f} P(neto<0) {np.mean(nm<0):.2f} | 1er Combine pase {np.mean(fp==1):.2f}", flush=True)
third = n // 3
run("completo", 0, n); run("T1 (baja vol)", 0, third); run("T3 (reciente)", n - third, n)
