"""Prueba de replica del sesgo direccional (short +, long -) del candidato MGC 143/143 nc=15 en otros productos.
Version A: MISMOS ticks/nc (143/143, nc=15) tal cual pidio el usuario. Version B: mismo ancho RELATIVO (c x R con R =
rango mediano entrada->flatten del producto), c in {0.25,0.30,0.35,0.40}, nc con SL$ ~ $2,184.
MGC como control (entrada 7:13); M2K/M6E entrada 8:43 (8:30+13), flatten 14:30. Motor empirico (bar-walk real)."""
import numpy as np, pandas as pd
from scipy import stats
from dd_wr.product_sweep import PRODUCTS, load_sessions, walk_all, median_range_ticks
from dd_wr.rr_experiment import combine_pool, Emp, xfa_pool_fixed_nc, summarize

def ls_report(label, t, nc):
    x = t.pnl.values; n = len(t)
    L, Sh = t[t.side == 1].pnl.values, t[t.side == -1].pnl.values
    w = stats.ttest_ind(Sh, L, equal_var=False)
    thirds = []
    for lo, hi in ((0, n // 3), (n // 3, 2 * n // 3), (2 * n // 3, n)):
        s = t.iloc[lo:hi]; thirds.append(f"L={s[s.side==1].pnl.mean():6.0f}/S={s[s.side==-1].pnl.mean():6.0f}")
    tp, sl, fl = (t.result == "TP").sum(), (t.result == "SL").sum(), (t.result == "FLATTEN").sum()
    tstat = x.mean() / (x.std(ddof=1) / np.sqrt(n))
    same = all((s[s.side == -1].pnl.mean() > s[s.side == 1].pnl.mean()) for s in (t.iloc[:n//3], t.iloc[n//3:2*n//3], t.iloc[2*n//3:]))
    print(f"{label:34s} nc={nc:3d} EV={x.mean():6.0f} (t={tstat:5.2f}) | LONG={L.mean():6.0f} SHORT={Sh.mean():6.0f} dif(S-L)={Sh.mean()-L.mean():6.0f} Welch p={w.pvalue:.3f} | terciosT1..T3: {' '.join(thirds)} | short>long en 3/3: {same} | TP/SL/FL={tp}/{sl}/{fl}", flush=True)

for label, spec in (("MGC", PRODUCTS["MGC"]), ("M2K", PRODUCTS["M2K"]), ("M6E", PRODUCTS["M6E"])):
    stem, tick, tv, comm, cap, open_m, flat_m, _ = spec
    S = load_sessions(stem); entry = open_m + 13
    R = median_range_ticks(S, tick, entry, flat_m)
    print(f"\n=== {label}  entrada {entry//60}:{entry%60:02d} CT, R={R:.0f} ticks, 143 ticks = {143/R:.2f}R, SL$ con nc=15 = ${143*tv*15:,.0f} ===")
    ls_report(f"A) literal 143/143 nc=15", walk_all(S, tick, tv, comm, 15, 143, 143, entry, flat_m), 15)
    for c in (0.25, 0.30, 0.35, 0.40):
        sl = max(2, int(round(c * R))); nc = int(np.clip(round(2184 / (sl * tv)), 1, max(cap, 1) if label != "MGC" else 60))
        ls_report(f"B) c={c:.2f}R ({sl}/{sl})", walk_all(S, tick, tv, comm, nc, sl, sl, entry, flat_m), nc)
