"""PARTE B (2): comparacion apples-to-apples de G2 vs candidatos, salida parcial+breakeven, DLL, friccion, MC de intentos/costo/dias
(p50/p90/p99), proxies de conducta, y prueba out-of-sample (seleccion en H1 -> H2)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.partb_grid import PRODUCTS, MLL, TARGET, FEE, ACT, configs
from scripts.xfa_liquidation_check import tables, KMAX, INF
from strategies.geometry_pure import trading_day_index, decide_side
from dd_wr.product_sweep import load_sessions


def be_table(stem, tick, entry_m, flat_m, tp1s):
    out = []
    for day, h, l, c, m in load_sessions(stem):
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); side = decide_side(trading_day_index(day), "alternate"); e = c[ep]
        jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        hh, ll = h[ep + 1:jf + 1], l[ep + 1:jf + 1]
        fav = ((hh - e) if side == 1 else (e - ll)) / tick; adv = ((e - ll) if side == 1 else (hh - e)) / tick
        F = np.maximum.accumulate(fav); row = []
        for t1 in tp1s:
            j1 = int(np.searchsorted(F, t1))
            if j1 >= len(F): row.append(INF); continue
            nxt = np.nonzero(adv[j1 + 1:] >= 0)[0]
            row.append(j1 + 1 + int(nxt[0]) if len(nxt) else INF)
        out.append(row)
    return np.array(out)


def sim(T, days, nc, tp, sl, tv, comm, n=20000, max_days=40, seed=7, cons=0.55, dll=None, slip=0, partial=None, be=None, arrays=False):
    adv, tpt, flat = T; rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -MLL); alive = np.ones(n, bool); best = np.zeros(n)
    passed = np.zeros(n, bool); blown_ = np.zeros(n, bool); res = np.full(n, max_days); unit = nc * tv
    for d in range(1, max_days + 1):
        di = days[rng.integers(0, len(days), n)]
        dist = b - f
        if dll: dist = np.minimum(dist, dll)
        k = np.clip(np.minimum(sl, np.ceil(dist / unit - 1e-9)), 1, KMAX).astype(int)
        ab = adv[di, k]
        if partial is None:
            tb = tpt[di, tp]; tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
            pnl = np.where(tp_hit, tp * unit, np.where(sl_hit, -k * unit, flat[di] * unit))
        else:
            tp1, tp2, col = partial; half = nc // 2; rest = nc - half
            t1 = tpt[di, tp1]; tp1_hit = t1 < ab; sl_hit = ~tp1_hit & (ab < INF)
            bebar = be[di, col]; t2 = tpt[di, tp2]
            rest_p = np.where(t2 < bebar, tp2 * rest * tv, np.where(bebar < INF, 0.0, flat[di] * rest * tv))
            pnl = np.where(tp1_hit, tp1 * half * tv + rest_p, np.where(sl_hit, -k * unit, flat[di] * unit))
            tp_hit = tp1_hit
        pnl = pnl - comm * nc - slip * tv * nc * (1 + sl_hit)
        pnl = np.where(alive, pnl, 0.0); b += pnl
        f = np.where(alive & (b - MLL > f), np.minimum(b - MLL, 0.0), f)
        bl = alive & (b <= f); alive &= ~bl; blown_ |= bl; res = np.where(bl, d, res)
        best = np.where(alive & (pnl > best), pnl, best)
        ok = alive & (b >= np.maximum(TARGET, best / cons)) & (d >= 2)
        passed |= ok; res = np.where(ok, d, res); alive &= ~ok
    p = passed.mean(); fee = FEE * (1 + (res - 1) // 21)
    r = dict(p=p, days_res=res.mean(), days_per_pass=res.mean() / p if p else np.inf, cost_pass=fee.mean() / p + ACT if p else np.inf,
             hits100=100 * blown_.mean() / res.mean())
    if arrays: r["arr"] = (passed, res, fee)
    return r


def mc_attempts(arr, N=100000, seed=3):
    passed, res, fee = arr; rng = np.random.default_rng(seed); n = len(passed)
    att = np.zeros(N, int); days = np.zeros(N); cost = np.full(N, ACT, float); done = np.zeros(N, bool)
    while not done.all():
        i = rng.integers(0, n, N); act = ~done
        att += act; days += np.where(act, res[i], 0); cost += np.where(act, fee[i], 0); done |= passed[i]
    q = lambda x: np.percentile(x, [50, 90, 99])
    return q(att), q(days), q(cost)


if __name__ == "__main__":
    S = {}
    def get(name, em):
        if (name, em) not in S:
            stem, tick, tv, comm, ncmax, entries, flat = PRODUCTS[name]; S[(name, em)] = tables(stem, tick, em, flat)
        return S[(name, em)]
    print("== Comparacion (Combine 50K, reglas reales, DLL off, max 40 dias/intento, n=20000)")
    print("config | pass | dias/intento | dias por pase | costo por pase | hits MLL/100d | SL$ TP$ nc(%max) | intentos p50/p90/p99 | fees+act p50/p90/p99 | dias p50/p90/p99")
    rows = [("G2 actual MES 9:45 nc40 TP40 SL100", "MES", 585, 40, 40, 100),
            ("MES 8:43 nc16 TP75 SL25 (RR3)", "MES", 523, 16, 75, 25),
            ("MES 9:45 nc16 TP75 SL25 (RR3)", "MES", 585, 16, 75, 25),
            ("MES 8:43 nc10 TP75 SL25 (RR3)", "MES", 523, 10, 75, 25),
            ("MES 8:43 nc20 TP50 SL25 (RR2)", "MES", 523, 20, 50, 25),
            ("M2K 8:43 nc25 TP111 SL37 (RR3)", "M2K", 523, 25, 111, 37),
            ("MGC 7:13 nc8 TP177 SL59 (RR3) [bolsillo de EV de muestra]", "MGC", 433, 8, 177, 59)]
    for lbl, pr, em, nc, tp, sl in rows:
        T = get(pr, em); tv, comm = PRODUCTS[pr][2], PRODUCTS[pr][3]; days = np.arange(len(T[0]))
        r = sim(T, days, nc, tp, sl, tv, comm, arrays=True); a, dd, cc = mc_attempts(r["arr"])
        print(f"{lbl} | {r['p']:.3f} | {r['days_res']:.2f} | {r['days_per_pass']:.1f} | ${r['cost_pass']:.0f} | {r['hits100']:.1f} | ${nc*sl*tv:,.0f}/${nc*tp*tv:,.0f} {nc} ({nc/50:.0%}) | {a[0]:.0f}/{a[1]:.0f}/{a[2]:.0f} | ${cc[0]:.0f}/${cc[1]:.0f}/${cc[2]:.0f} | {dd[0]:.0f}/{dd[1]:.0f}/{dd[2]:.0f}")
    print("\n== Salida parcial (mitad en TP1, resto a TP2 o breakeven) vs salida unica RR3, MES 8:43")
    T = get("MES", 523); tv, comm = 1.25, 1.22; days = np.arange(len(T[0]))
    for nc, sl in ((16, 25), (10, 25), (20, 20)):
        tp1s = [int(sl * a) for a in (1, 1.5, 2)]; be = be_table("mes_5min_2y", 0.25, 523, 870, tp1s)
        base = sim(T, days, nc, 3 * sl, sl, tv, comm)
        print(f"  nc={nc} SL={sl}: unico TP={3*sl}: pass={base['p']:.3f} costo=${base['cost_pass']:.0f} dias/pase={base['days_per_pass']:.1f}")
        for col, t1 in enumerate(tp1s):
            for t2 in (3 * sl, 4 * sl):
                r = sim(T, days, nc, 0, sl, tv, comm, partial=(t1, t2, col), be=be)
                print(f"     parcial TP1={t1} TP2={t2}: pass={r['p']:.3f} costo=${r['cost_pass']:.0f} dias/pase={r['days_per_pass']:.1f} hits100={r['hits100']:.1f}")
    print("\n== DLL on ($1,000) y friccion (slip ticks) sobre MES 8:43 nc16 TP75 SL25 y sobre G2")
    for lbl, pr, em, nc, tp, sl in rows[:2]:
        T = get(pr, em); tv, comm = PRODUCTS[pr][2], PRODUCTS[pr][3]; days = np.arange(len(T[0]))
        out = []
        for kw in (dict(), dict(dll=1000.0), dict(slip=1), dict(slip=2), dict(slip=3)):
            r = sim(T, days, nc, tp, sl, tv, comm, **kw); out.append(f"{kw or 'base'}: pass={r['p']:.3f} costo=${r['cost_pass']:.0f}")
        print(f"  {lbl}: " + " | ".join(out))
    print("\n== Prueba out-of-sample sobre las 767 configs del grid: seleccion en H1 -> resultado en H2")
    import pandas as pd
    df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "partb_grid_results.csv")); df = df[(df.p > 0.05) & np.isfinite(df.H1) & np.isfinite(df.H2)]
    from scipy.stats import spearmanr
    print(f"  configs validas={len(df)} | Spearman(H1,H2 costo)={spearmanr(df.H1, df.H2)[0]:.2f}")
    for prod in [None, "MES"]:
        d = df if prod is None else df[df['prod'] == prod]
        top = d.sort_values("H1").head(5)
        print(f"  {'todos' if prod is None else prod}: top5 por H1 -> costo H1 {top.H1.mean():.0f} | costo H2 {top.H2.mean():.0f} | mediana H2 del grid {d.H2.median():.0f}")
