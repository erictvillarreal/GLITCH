"""
Prioridad 1: el $31,257 publicado, ¿es consistente con la distribucion real que incluye FLATTEN?
Engine copiado de simulate_xfa_lifetime_dynamic_nc con UNA diferencia: el PnL diario por contrato
sale de una distribucion empirica (inverse-CDF sobre el mismo u ~ U(0,1) que usa el original), no
de un binario. Con una distribucion de 2 puntos 'ganadores primero' reproduce el original bit a bit.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from core.funded_account import XFA_150K, dynamic_nc_for_balance, simulate_xfa_lifetime_dynamic_nc
from simulation.monte_carlo import DailyReturnDist
from scripts.cerebro2_cashflow_monte_carlo import run_cashflow_simulation
from dd_wr.rr_experiment import load, trades, combine_pool, Emp, summarize, NC, COMM, SEED, SL_TICKS


def xfa_dyn_emp(per_contract_sorted, nc_designed=NC, n_paths=50_000, max_days=756, seed=SEED, fix_neg=False):
    s = np.asarray(per_contract_sorted, float); N = len(s)
    rng = np.random.default_rng(seed)
    u = rng.random((n_paths, max_days))
    idx = np.minimum((u * N).astype(np.int64), N - 1)
    S = XFA_150K
    bal = np.zeros(n_paths); floor = np.full(n_paths, S.floor_start); alive = np.ones(n_paths, bool)
    wd = np.zeros(n_paths, np.int64); npay = np.zeros(n_paths, np.int64); usd = np.zeros(n_paths); dn = np.zeros(n_paths, np.int64)
    for day in range(max_days):
        act = alive
        nc = np.minimum(dynamic_nc_for_balance(bal, S.mll_distance, "MGC"), nc_designed)
        p = nc * s[idx[:, day]]
        bal = np.where(act, bal + p, bal); dn = np.where(act, day + 1, dn)
        cand = bal - S.mll_distance
        floor = np.where(act & (cand > floor), np.minimum(cand, S.floor_lock_level), floor)
        blown = act & (bal <= floor); alive = alive & ~blown
        still = act & ~blown
        wd = np.where(still & (p >= S.min_winning_day_usd), wd + 1, wd)
        elig = still & (wd >= S.winning_days_required)
        if fix_neg: elig = elig & (bal > 0)
        if elig.any():
            g = np.minimum(bal[elig] * S.payout_pct_of_balance, S.payout_cap_usd)
            bal = bal.copy(); bal[elig] -= g
            floor = floor.copy(); floor[elig] = 0.0
            wd = wd.copy(); wd[elig] = 0
            npay = npay.copy(); npay[elig] += 1
            usd = usd.copy(); usd[elig] += g * S.profit_split_trader
    return {"payout_usd_pool": usd, "n_payouts_pool": npay.astype(float), "days_pool": dn.astype(float)}


def chain(t_pnl_total, label, fix_neg=False):
    per_c = np.sort(np.asarray(t_pnl_total, float) / NC)[::-1]   # ganadores primero
    cp = combine_pool(Emp(t_pnl_total))
    return summarize(cp, xfa_dyn_emp(per_c, fix_neg=fix_neg))


if __name__ == "__main__":
    # 1) validacion bit a bit del engine copiado contra el original (binario WR=.5, $364/contrato, comision 1.92)
    win, loss = 364 - COMM, -(364 + COMM)
    bin_sorted = np.array([win] * 500 + [loss] * 500)
    mine = xfa_dyn_emp(bin_sorted)
    orig = simulate_xfa_lifetime_dynamic_nc(.5, 364., 364., COMM, spec=XFA_150K, product_code="MGC", nc_designed=NC,
                mll_reset_policy="every_payout", n_paths=50_000, max_days=756, seed=SEED, return_raw=True)
    print("bit-a-bit payout_usd:", np.array_equal(mine["payout_usd_pool"], orig["raw_lifetime_payout_usd"]),
          "| days:", np.array_equal(mine["days_pool"], orig["raw_lifetime_days"]))

    data = load()
    t = trades(data, SL_TICKS, 364)
    n = len(t)
    t["date"] = pd.to_datetime(t["date"])
    print("\nFLATTEN share por tercio calendario (RR=1.0, sesion real):")
    parts = {"T1": t.iloc[:n // 3], "T2": t.iloc[n // 3:2 * n // 3], "T3": t.iloc[2 * n // 3:], "ultimos_120": t.iloc[-120:]}
    for k, x in parts.items():
        tp, sl, fl = (x.result == "TP").sum(), (x.result == "SL").sum(), (x.result == "FLATTEN").sum()
        print(f"  {k:12s} {x.date.min().date()}..{x.date.max().date()} n={len(x)} TP={tp} SL={sl} FLAT={fl} ({fl/len(x):.1%}) WRcond={tp/(tp+sl):.3f} flat_mean_pnl=${x[x.result=='FLATTEN'].pnl.mean():,.0f} sd_pnl=${x.pnl.std():,.0f}")

    full = t.pnl.values
    print("\nDistribucion diaria real (RR=1.0): P(dia>=+$150)=%.3f, P(|pnl|<$150)=%.3f, P(dia<=-$2000)=%.3f" % (
        (full >= 150).mean(), (np.abs(full) < 150).mean(), (full <= -2000).mean()))
    bin_p = 0.5
    print("Publicado (binario): P(dia>=150)=0.500, P(|pnl|<150)=0.000, P(dia<=-2000)=0.500")

    rows = []
    def add(label, d): rows.append({"variante": label, **{k: d[k] for k in ("combine_pass","p10","p25","p50","p75","p90","xfa_p_ge1_payout","xfa_avg_days")}})
    # V0 publicado
    cp0 = combine_pool(DailyReturnDist(win_rate=.5, avg_win=364*NC-COMM*NC, avg_loss=364*NC+COMM*NC, name="pub"))
    per0 = np.array([win] * 500 + [loss] * 500)
    add("V0 publicado (binario WR=.50, dyn-nc)", summarize(cp0, xfa_dyn_emp(per0)))
    # V1 binario con WR condicional medido
    wrc = (t.result == "TP").sum() / ((t.result == "TP").sum() + (t.result == "SL").sum())
    k = int(round(wrc * 1000)); per1 = np.array([win] * k + [loss] * (1000 - k))
    cp1 = combine_pool(DailyReturnDist(win_rate=k/1000, avg_win=364*NC-COMM*NC, avg_loss=364*NC+COMM*NC, name="v1"))
    add(f"V1 binario, WR cond. medido {k/1000:.3f}, dyn-nc", summarize(cp1, xfa_dyn_emp(per1)))
    # V2 empirico completo con FLATTEN, dyn-nc (misma mecanica que el publicado)
    add("V2 empirico c/FLATTEN, dyn-nc, periodo completo", chain(full, "v2"))
    add("V2fix idem + fix balance>0", chain(full, "v2f", fix_neg=True))
    for k2, x in parts.items():
        add(f"V2 empirico c/FLATTEN, dyn-nc, solo {k2}", chain(x.pnl.values, k2))
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
    print("\n", out.round(3).to_string(index=False))
    out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flatten_check_results.csv"), index=False)
