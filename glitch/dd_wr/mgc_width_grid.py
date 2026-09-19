"""
Grid extendido de ancho de SL para MGC_XFA (entrada 7:13 CT SIN cambiar, flatten 14:30 CT, alternar).
MOTOR EMPIRICO (bar-walk real de sesion + bootstrap del PnL real por trade que incluye FLATTEN;
XFA con Scaling Plan real via xfa_dyn_emp, Combine con bootstrap empirico, cadena run_cashflow_simulation).
NO usa el motor binario original.
Por config: p10..p90, FLATTEN share, share de barras AMBIGUAS (TP y SL tocados en la misma barra de 5min,
resueltas SL-primero = conservador), bracket optimista (empates -> TP), friccion slip=1 tick.
SL$ objetivo ~$2,184: nc_disenado = round(2184 / (SL_ticks * $1)); el Scaling Plan lo recorta por balance en la XFA.
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from strategies.geometry_pure import trading_day_index, decide_side
from dd_wr.product_sweep import PRODUCTS, load_sessions, median_range_ticks
from dd_wr.rr_experiment import combine_pool, Emp, summarize
from dd_wr.flatten_check import xfa_dyn_emp

STEM, TICK, TV, COMM, CAP, OPEN_M, FLAT_M, _ = PRODUCTS["MGC"]
ENTRY_M = OPEN_M + 13   # 7:13 CT
SL_USD = 2184.0
C_GRID = [0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
RR_GRID = [1.0, 0.67, 0.43, 0.33]


def walk(S, nc, sl_t, tp_t, win_first):
    pp = TV / TICK; out = []
    for day, h, l, c, m in S:
        a = np.nonzero(m >= ENTRY_M)[0]
        if len(a) == 0: continue
        ep = int(a[0]); side = decide_side(trading_day_index(day), "alternate")
        e = c[ep]; tp = e + side * tp_t * TICK; sl = e - side * sl_t * TICK
        res = None; amb = 0
        for j in range(ep + 1, len(c)):
            w, lo = (h[j] >= tp, l[j] <= sl) if side == 1 else (l[j] <= tp, h[j] >= sl)
            if w or lo:
                if w and lo:
                    amb = 1; win = win_first
                else: win = w
                px = tp if win else sl
                res = ("TP" if win else "SL", (px - e) * side * pp * nc - COMM * nc); break
            if m[j] >= FLAT_M:
                res = ("FLATTEN", (c[j] - e) * side * pp * nc - COMM * nc); break
        if res is None: res = ("FLATTEN", (c[-1] - e) * side * pp * nc - COMM * nc)
        out.append((str(day), side, res[0], res[1], amb))
    return pd.DataFrame(out, columns=["date", "side", "result", "pnl", "ambig"])


def chain(pnl, nc, n_paths_xfa=50_000):
    cp = combine_pool(Emp(pnl), n_paths=50_000)
    return summarize(cp, xfa_dyn_emp(np.sort(pnl / nc)[::-1], nc_designed=nc, n_paths=n_paths_xfa), ntraj=10_000)


if __name__ == "__main__":
    S = load_sessions(STEM); R = median_range_ticks(S, TICK, ENTRY_M, FLAT_M)
    print(f"R (rango mediano 7:13->14:30) = {R:.0f} ticks. MOTOR: empirico (dyn-nc Scaling Plan + bootstrap real). NO binario.", flush=True)
    rows = []; t0 = time.time()
    cfgs = [(c, int(round(c * R)), rr) for c in C_GRID for rr in RR_GRID]
    cfgs.append((364 / R, 364, 1.0))
    for c, sl, rr in cfgs:
        tp = max(1, int(round(sl * rr))); nc = max(1, int(round(SL_USD / (sl * TV))))
        t = walk(S, nc, sl, tp, False); pnl = t.pnl.values
        n = len(t); ntp = (t.result == "TP").sum(); nsl = (t.result == "SL").sum(); nfl = (t.result == "FLATTEN").sum()
        d0 = chain(pnl, nc)
        slip = pnl - nc * TV * (1 + np.where(t.result.isin(["SL", "FLATTEN"]), 1, 0))
        d1 = chain(slip, nc, 30_000)
        to = walk(S, nc, sl, tp, True); dopt = chain(to.pnl.values, nc, 30_000)
        r = dict(c=round(c, 3), sl=sl, tp=tp, rr=rr, nc=nc, sl_usd=sl * TV * nc + COMM * nc, tp_net=tp * TV * nc - COMM * nc,
                 n=n, tp_n=ntp, sl_n=nsl, flat_n=nfl, flat_share=nfl / n, ambig_share=t.ambig.mean(),
                 wr_cond=ntp / max(1, ntp + nsl), ev=pnl.mean(), ev_slip1=slip.mean(),
                 combine_pass=d0["combine_pass"], p10=d0["p10"], p25=d0["p25"], p50=d0["p50"], p75=d0["p75"], p90=d0["p90"],
                 xfa_p_ge1=d0["xfa_p_ge1_payout"], xfa_days=d0["xfa_avg_days"],
                 p50_slip1=d1["p50"], p50_optimistic=dopt["p50"])
        rows.append(r)
        print(f"c={r['c']:.3f} SL={sl:3d} TP={tp:3d} rr={rr} nc={nc:3d} flat={r['flat_share']:.2f} amb={r['ambig_share']:.2f} WRc={r['wr_cond']:.3f} "
              f"EV=${r['ev']:5.0f} p50=${r['p50']:8,.0f} slip1=${r['p50_slip1']:8,.0f} opt=${r['p50_optimistic']:8,.0f} ({time.time()-t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mgc_width_grid_results.csv"), index=False)
