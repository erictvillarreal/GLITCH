"""
MLL en tiempo real dentro de la XFA (help.topstep.com/8284204: aplica igual que en el Combine; XFA se cierra permanentemente).
Cuantifica MGC_XFA (SL=TP=364 ticks, alternar, entrada 7:13 CT, flatten 14:30) con y sin liquidacion intradia por distancia al piso.
Tras cada payout el piso vuelve a $0 y el balance baja (payout 50%) -> la distancia al piso puede ser menor que el SL.
Sim path-dependiente sobre tablas de primer-toque de MGC real (5min). Mismo motor XFA que core/funded_account.py (Scaling Plan dyn-nc,
5 dias >= $150, payout 50% con tope por tamaño, split 90%, fix balance>0, politica every_payout).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from strategies.geometry_pure import trading_day_index, decide_side
from dd_wr.product_sweep import load_sessions
from core.funded_account import XFA_50K, XFA_100K, XFA_150K, dynamic_nc_for_balance

KMAX = 500; INF = 10**6


def tables(stem, tick, entry_m, flat_m, tmax=500):
    adv_b, tp_b, flat_t, dates = [], [], [], []
    for day, h, l, c, m in load_sessions(stem):
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); side = decide_side(trading_day_index(day), "alternate"); e = c[ep]
        jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        hh, ll, cc = h[ep + 1:jf + 1], l[ep + 1:jf + 1], c[ep + 1:jf + 1]
        fav = ((hh - e) if side == 1 else (e - ll)) / tick; adv = ((e - ll) if side == 1 else (hh - e)) / tick
        M, F = np.maximum.accumulate(adv), np.maximum.accumulate(fav)
        ai = np.searchsorted(M, np.arange(1, KMAX + 1)); ai = np.where(ai >= len(M), INF, ai)
        ti = np.searchsorted(F, np.arange(1, tmax + 1)); ti = np.where(ti >= len(F), INF, ti)
        adv_b.append(np.concatenate([[INF], ai])); tp_b.append(np.concatenate([[INF], ti])); flat_t.append((cc[-1] - e) * side / tick); dates.append(str(day))
    return np.array(adv_b), np.array(tp_b), np.array(flat_t)


def xfa(T, spec, nc_x, tp, sl, tv, comm, liquidate, lock, n=30000, max_days=756, seed=7):
    adv, tpt, flat = T; nd = len(adv); rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -spec.mll_distance); alive = np.ones(n, bool); wd = np.zeros(n, int)
    tot = np.zeros(n); npay = np.zeros(n, int); life = np.zeros(n, int); bind = 0; liq = 0; trades = 0
    for d in range(max_days):
        if not alive.any(): break
        idx = rng.integers(0, nd, n)
        nc = np.minimum(dynamic_nc_for_balance(b, spec.mll_distance, "MGC"), nc_x).astype(float)
        unit = nc * tv
        k = np.clip(np.minimum(sl, np.ceil((b - f) / unit - 1e-9)), 1, KMAX).astype(int) if liquidate else np.full(n, sl)
        ab = adv[idx, k]; tb = tpt[idx, tp]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, tp * unit, np.where(sl_hit, -k * unit, flat[idx] * unit)) - comm * nc
        pnl = np.where(alive, pnl, 0.0)
        trades += alive.sum(); bind += (alive & (k < sl)).sum(); liq += (alive & sl_hit & (k < sl)).sum()
        b += pnl; life += alive
        f = np.where(alive & (b - spec.mll_distance > f), np.minimum(b - spec.mll_distance, lock), f)
        blown = alive & (b <= f); alive &= ~blown
        wd = np.where(alive & (pnl >= spec.min_winning_day_usd), wd + 1, wd)
        elig = alive & (wd >= spec.winning_days_required) & (b > 0)
        if elig.any():
            g = np.minimum(b[elig] * spec.payout_pct_of_balance, spec.payout_cap_usd)
            b[elig] -= g; f[elig] = 0.0; wd[elig] = 0; npay[elig] += 1; tot[elig] += g * spec.profit_split_trader
    return dict(mean=tot.mean(), med=np.median(tot), p_any=(npay > 0).mean(), npay=npay.mean(), life=life.mean(), bind=bind / trades, liq=liq / trades, blown=(~alive).mean())


if __name__ == "__main__":
    T = tables("mgc_5min_2y_corrected_window", 0.10, 7 * 60 + 13, 14 * 60 + 30)
    print(f"MGC dias={len(T[0])}. Lifetime de 1 XFA (max 756 dias), 30,000 paths.")
    for name, spec, nc in (("150K nc=6", XFA_150K, 6), ("100K nc=4", XFA_100K, 4), ("50K nc=3", XFA_50K, 3)):
        print(f"\n== {name} SL=TP=364 ticks | SL$ inicial=${364*nc:,} vs MLL ${spec.mll_distance:,.0f}")
        for lbl, liquidate, lock in (("SIN liquidacion (modelo actual)", False, spec.mll_distance), ("CON liquidacion MLL real, lock del codigo (+MLL)", True, spec.mll_distance), ("CON liquidacion, lock oficial en $0", True, 0.0)):
            r = xfa(T, spec, nc, 364, 364, 1.0, 1.92, liquidate, lock)
            print(f"   {lbl}: payout medio=${r['mean']:,.0f} mediana=${r['med']:,.0f} P(>=1 payout)={r['p_any']:.3f} payouts/cuenta={r['npay']:.2f} dias vida={r['life']:.1f} | trades con liquidacion vinculante={r['bind']:.3f}, liquidados antes del SL={r['liq']:.3f}")
