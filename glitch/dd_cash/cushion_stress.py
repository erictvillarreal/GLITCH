import numpy as np
import dd_cash.cushion_50kb as C
n = C.n; third = C.third
print("\n== ESTRES del colchon 6m (base | T3), lags 2d/5d: payouts x factor")
for nm, (lo, hi) in {"base": (0, n), "T3": (n - third, n)}.items():
    r, _ = C.run(lo, hi, 2, 5)
    take = r["take_d"].astype(np.float64); take = np.concatenate([np.zeros((take.shape[0], 5)), take[:, :-5]], axis=1)
    ops = np.zeros(C.H); ops[::C.M] = C.OPS
    for f in (1.0, 0.75, 0.5, 0.25, 0.0):
        c = np.cumsum(f * take - r["fee_d"], axis=1) - np.cumsum(ops)[None, :]
        cu = C.cushion(c, 126)
        print(f"  {nm:4s} payouts x{f:4.2f}: colchon 6m p90 {np.percentile(cu,90):6,.0f} p95 {np.percentile(cu,95):6,.0f} p99 {np.percentile(cu,99):6,.0f}")
