"""
research/mgc-wr-improvement -- experimento de 6 puntos: RR in {1.0,.67,.43,.33,.25,.18}
sobre MGC_XFA (SL en $ fijo ~$2,184: SL=364 ticks x nc=6), entrada real 7:13 CT,
flatten real 14:30 CT, 1 trade/dia alternando (bar-walk de sesion, misma convencion
conservadora win_first=False que dd_ppp/bar_walk.py).

Pista A (parametrica, MISMO motor que el $31,257 publicado): binario con el WR
empirico condicional TP/(TP+SL) medido; XFA con simulate_xfa_lifetime_dynamic_nc.
  -> los flatten se ignoran (mismo tratamiento que el baseline publicado).
Pista B (empirica, nc fijo=6): bootstrap del PnL REAL por trade (incluye flatten y
  comision), Combine con TopstepMonteCarloSimulator + XFA con logica de
  simulate_xfa_lifetime (copiada, con flag para el fix balance>0).
Ambas encadenan Combine->XFA con run_cashflow_simulation (sin modificar).
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd

from core.prop_firm import TOPSTEP_150K
from core.funded_account import XFA_150K, simulate_xfa_lifetime_dynamic_nc
from simulation.monte_carlo import TopstepMonteCarloSimulator, DailyReturnDist
from strategies.geometry_pure import SPECS, trading_day_index, decide_side
from scripts.cerebro2_cashflow_monte_carlo import run_cashflow_simulation

MGC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data_cache", "mgc_5min_2y_corrected_window.parquet")
SPEC = SPECS["MGC"]; TICK = SPEC.tick_size; TV = SPEC.tick_value_usd
COMM = SPEC.commission_roundturn; NC = 6; SL_TICKS = 364
PT = TV / TICK
ENTRY_MIN = 7 * 60 + 13; FLAT_MIN = 14 * 60 + 30
TP_TICKS = {1.0: 364, 0.67: 243, 0.43: 156, 0.33: 120, 0.25: 91, 0.18: 66}
SEED = 7


def load():
    df = pd.read_parquet(MGC_PATH)
    df.index = df.index.tz_convert("America/Chicago")
    df["session_date"] = df.index.date
    df["mod"] = df.index.hour * 60 + df.index.minute
    return df


def walk(bars, ep, side, sl_t, tp_t):
    hi, lo, cl, md = bars["high"].values, bars["low"].values, bars["close"].values, bars["mod"].values
    e = cl[ep]; tp = e + side * tp_t * TICK; sl = e - side * sl_t * TICK
    for j in range(ep + 1, len(bars)):
        w, l = (hi[j] >= tp, lo[j] <= sl) if side == 1 else (lo[j] <= tp, hi[j] >= sl)
        if w or l:
            if w and not l: return "TP", (tp - e) * side * PT * NC - COMM * NC
            return "SL", (sl - e) * side * PT * NC - COMM * NC
        if md[j] >= FLAT_MIN:
            return "FLATTEN", (cl[j] - e) * side * PT * NC - COMM * NC
    return "FLATTEN", (cl[-1] - e) * side * PT * NC - COMM * NC


def trades(data, sl_t, tp_t):
    rows = []
    for d, b in data.groupby("session_date", sort=True):
        b = b.reset_index(drop=True)
        a = b.index[b["mod"] >= ENTRY_MIN]
        if len(a) == 0: continue
        side = decide_side(trading_day_index(d), "alternate")
        r, p = walk(b, int(a[0]), side, sl_t, tp_t)
        rows.append((str(d), side, r, p))
    return pd.DataFrame(rows, columns=["date", "side", "result", "pnl"])


class Emp:
    def __init__(self, arr): self.a = np.asarray(arr, float)
    def sample(self, n, rng): return rng.choice(self.a, size=n, replace=True)


def xfa_pool_fixed_nc(arr, fix_negative, n_paths=50_000, max_days=756, seed=SEED):
    rng = np.random.default_rng(seed)
    pnls = Emp(arr).sample(n_paths * max_days, rng).reshape(n_paths, max_days)
    S = XFA_150K
    bal = np.zeros(n_paths); floor = np.full(n_paths, S.floor_start); alive = np.ones(n_paths, bool)
    wd = np.zeros(n_paths, np.int64); npay = np.zeros(n_paths, np.int64)
    usd = np.zeros(n_paths); dn = np.zeros(n_paths, np.int64)
    for day in range(max_days):
        act = alive; p = pnls[:, day]
        bal = np.where(act, bal + p, bal); dn = np.where(act, day + 1, dn)
        cand = bal - S.mll_distance
        upd = act & (cand > floor)
        floor = np.where(upd, np.minimum(cand, S.floor_lock_level), floor)
        blown = act & (bal <= floor); alive = alive & ~blown
        still = act & ~blown
        wd = np.where(still & (p >= S.min_winning_day_usd), wd + 1, wd)
        elig = still & (wd >= S.winning_days_required)
        if fix_negative: elig = elig & (bal > 0)
        if elig.any():
            gross = np.minimum(bal[elig] * S.payout_pct_of_balance, S.payout_cap_usd)
            bal = bal.copy(); bal[elig] -= gross
            floor = floor.copy(); floor[elig] = 0.0
            wd = wd.copy(); wd[elig] = 0
            npay = npay.copy(); npay[elig] += 1
            usd = usd.copy(); usd[elig] += gross * S.profit_split_trader
    return {"payout_usd_pool": usd, "n_payouts_pool": npay.astype(float), "days_pool": dn.astype(float)}


def combine_pool(dist, n_paths=100_000, max_days=250):
    r = TopstepMonteCarloSimulator(dist, TOPSTEP_150K, n_paths=n_paths, max_days=max_days, seed=42).run()
    return {"pass_rate": r.pass_rate, "pass_days_pool": r.pass_days, "blown_days_pool": r.blown_days,
            "fee_monthly": TOPSTEP_150K.monthly_fee, "fee_activation": TOPSTEP_150K.activation_fee}


def summarize(cp, xp, ntraj=20_000):
    res = run_cashflow_simulation(cp, xp, n_trajectories=ntraj, horizon_days=365, seed=SEED)
    tp = res["total_payout"]; q = np.percentile(tp, [10, 25, 50, 75, 90])
    return {"combine_pass": cp["pass_rate"], "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4],
            "mean": tp.mean(), "p_ge1_payout_1y": float((res["n_xfa_payouts"] >= 1).mean()),
            "xfa_p_ge1_payout": float((xp["n_payouts_pool"] >= 1).mean()), "xfa_avg_days": float(xp["days_pool"].mean()),
            "xfa_mean_payout": float(xp["payout_usd_pool"].mean())}


if __name__ == "__main__":
    data = load()
    rows = []
    for rr, tpt in TP_TICKS.items():
        t = trades(data, SL_TICKS, tpt)
        n = len(t); ntp = (t.result == "TP").sum(); nsl = (t.result == "SL").sum(); nfl = (t.result == "FLATTEN").sum()
        wr_c = ntp / (ntp + nsl)
        h = n // 2
        def wc(x): a = (x.result == "TP").sum(); b = (x.result == "SL").sum(); return a / (a + b)
        theo = SL_TICKS / (SL_TICKS + tpt)
        base = dict(rr=rr, tp_ticks=tpt, rr_actual=round(tpt / SL_TICKS, 3), n=n, tp=ntp, sl=nsl, flat=nfl,
                    wr_cond=wr_c, wr_theory=theo, wr_h1=wc(t.iloc[:h]), wr_h2=wc(t.iloc[h:]),
                    wr_uncond=ntp / n, ev_trade=t.pnl.mean(), flat_mean_pnl=t[t.result == "FLATTEN"].pnl.mean(),
                    tp_usd=tpt * TV * NC - COMM * NC, sl_usd=-(SL_TICKS * TV * NC + COMM * NC))
        # Pista A: parametrico, dynamic-nc, mismo motor que $31,257
        per_c_sl, per_c_tp = SL_TICKS * TV, tpt * TV
        dist = DailyReturnDist(win_rate=wr_c, avg_win=per_c_tp * NC - COMM * NC, avg_loss=per_c_sl * NC + COMM * NC, name="A")
        cpA = combine_pool(dist)
        r = simulate_xfa_lifetime_dynamic_nc(wr_c, per_c_sl, per_c_tp, COMM, spec=XFA_150K, product_code="MGC",
                nc_designed=NC, mll_reset_policy="every_payout", n_paths=50_000, max_days=756, seed=SEED, return_raw=True)
        xpA = {"payout_usd_pool": r["raw_lifetime_payout_usd"], "n_payouts_pool": r["raw_lifetime_payouts"], "days_pool": r["raw_lifetime_days"]}
        A = summarize(cpA, xpA)
        # Pista B: empirica, nc fijo, con y sin fix balance>0
        cpB = combine_pool(Emp(t.pnl.values))
        B = summarize(cpB, xfa_pool_fixed_nc(t.pnl.values, False))
        Bf = summarize(cpB, xfa_pool_fixed_nc(t.pnl.values, True))
        for tag, d in (("A_param_dynnc", A), ("B_emp_fixednc", B), ("B_emp_fixednc_fixneg", Bf)):
            rows.append({**base, "track": tag, **d})
        print(f"RR={rr}: WR_cond={wr_c:.4f} (teo {theo:.4f}) flat={nfl}/{n} | A p50=${A['p50']:,.0f} B p50=${B['p50']:,.0f} Bfix p50=${Bf['p50']:,.0f}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rr_experiment_results.csv"), index=False)
