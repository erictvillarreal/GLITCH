"""Utilidades del due diligence de MGC (motor EMPIRICO): PnL por config sobre las 515 sesiones reales alineadas
por dia + estadistico rapido de renovacion-recompensa S = payout esperado por año (media), consistente entre configs."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from dd_wr.mgc_width_grid import walk, chain, load_sessions, STEM, TV, COMM
from dd_wr.rr_experiment import combine_pool, Emp
from dd_wr.flatten_check import xfa_dyn_emp
from core.funded_account import XFA_150K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_150K

CAND = (143, 143, 15)
BASE = (364, 364, 6)


def config_trades(S, sl, tp, nc):
    return walk(S, nc, sl, tp, False)


def fast_S(pnl, nc, seed=11, n_c=4000, n_x=4000, xdays=300):
    """Payout esperado por año (renewal-reward): pass*E[payout XFA] / (E[dias combine] + pass*E[dias XFA]) * 365."""
    class D:
        def sample(self, n, rng): return rng.choice(pnl, size=n, replace=True)
    r = TopstepMonteCarloSimulator(D(), TOPSTEP_150K, n_paths=n_c, max_days=120, seed=seed).run()
    pr = r.pass_rate
    dp = float(np.mean(r.pass_days)) if len(r.pass_days) else 0.0
    db = float(np.mean(r.blown_days)) if len(r.blown_days) else 0.0
    x = xfa_dyn_emp(np.sort(pnl / nc)[::-1], nc_designed=nc, n_paths=n_x, max_days=xdays, seed=seed)
    cyc = pr * dp + (1 - pr) * db + pr * float(x["days_pool"].mean()) + 1e-9
    return 365.0 * pr * float(x["payout_usd_pool"].mean()) / cyc
