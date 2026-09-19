"""Primera pasada de robustez (NO es el due diligence completo) sobre anchos de SL de MGC:
motor dyn-nc con Scaling Plan real, por tercio de calendario, y sensibilidad a slippage (ticks)."""
import numpy as np
from dd_wr.product_sweep import *
from dd_wr.flatten_check import xfa_dyn_emp

stem, tick, tv, comm, cap, open_m, flat_m, _ = PRODUCTS["MGC"]
S = load_sessions(stem); entry = open_m + 13


def chain(x, nc):
    cp = combine_pool(Emp(x), n_paths=50_000)
    return summarize(cp, xfa_dyn_emp(np.sort(x / nc)[::-1], nc_designed=nc, n_paths=30_000), ntraj=8000)


def run(sl, tp, nc, label):
    t = walk_all(S, tick, tv, comm, nc, sl, tp, entry, flat_m); pnl = t.pnl.values; n = len(pnl)
    thirds = " | ".join(f"{k} p50=${chain(x, nc)['p50']:,.0f}" for k, x in
                        (("full", pnl), ("T1", pnl[:n // 3]), ("T2", pnl[n // 3:2 * n // 3]), ("T3", pnl[2 * n // 3:])))
    fr = []
    for slip in (0, 1, 2, 3):
        p = pnl - nc * tv * (slip + np.where(t.result.isin(["SL", "FLATTEN"]), slip, 0))
        fr.append(f"slip{slip}t EV=${p.mean():,.0f} p50=${chain(p, nc)['p50']:,.0f}")
    print(f"{label} SL={sl} TP={tp} nc={nc}\n  {thirds}\n  {' | '.join(fr)}", flush=True)


if __name__ == "__main__":
    run(364, 364, 6, "baseline")
    for c in (0.25, 0.35, 0.4, 0.5, 0.6):
        sl = int(round(c * 477)); nc = int(np.clip(round(2184 / (sl * tv)), 1, cap))
        for rr in (1.0, 0.67):
            run(sl, max(1, int(round(sl * rr))), nc, f"c={c} rr={rr}")
