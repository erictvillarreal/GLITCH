"""
Tradeify Growth/Select 50K y Bulenox Opcion 2 50K con los parametros VERIFICADOS en la fuente propia de cada firma (05-oct-2026,
ver GLITCH_RESEARCH_LOG.md), sobre las mismas tablas first-touch de MES (515 dias) y la politica "TP dimensionado al target restante".

Diferencias respecto a pass_rate_bold_real.py:
  * piso EOD con lock en +$100 (Tradeify: "locks its floor at $50,100 once its end-of-day balance reaches $52,100"; Bulenox: el lock +$100 esta
    documentado solo para Master; se SUPONE igual en Qualification, no verificado);
  * comision por firma (Tradeify MES $1.82 round-turn; Bulenox $1.22 round-turn, Bulenox-Rates.pdf);
  * Bulenox Opcion 2: tope de contratos escalado por Cash on Hand 50K: <=$1,500: 2 minis (20 micros); $1,501-4,000: 4 (40); >=$4,001: 7 (70);
  * DLL suave: el stop propio se coloca a floor((DLL - comision)/unit) ticks, NUNCA se depende del DLL como stop (Tradeify: "NEVER use the DLL as a
    stop loss ... losses may exceed the limit");
  * devuelve arrays por trayectoria para calcular costo esperado por pase con reinicios y la ventana de 30 dias de Bulenox.
Una sola historia de 515 dias, barras de 5 min, SL primero en barras ambiguas, in-sample.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.g2_real_rules_scan import build_tables, TV, KMAX, TMAX, INF


def bulenox50_cap(b):
    return np.where(b <= 1500, 20, np.where(b <= 4000, 40, 70))


def simulate(T, days_idx, mll, target, tp_ticks, g_cap, nc_cap, comm, lock=100.0, dll=None, cons=None, min_days=1, max_days=30,
             n=20000, seed=7, fixed_nc=None, tie_tp=False):
    adv_bar, tp_bar, flat_ticks = T
    rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -mll); alive = np.ones(n, bool); best = np.zeros(n)
    passed = np.zeros(n, bool); res_day = np.full(n, max_days)
    for d in range(1, max_days + 1):
        di = days_idx[rng.integers(0, len(days_idx), n)]
        need_tot = np.maximum(target, best / cons) if cons else np.full(n, target)
        R = np.maximum(need_tot - b, 1.0)
        G = np.minimum(R, g_cap)
        cap = nc_cap(b) if callable(nc_cap) else np.full(n, nc_cap)
        if fixed_nc is None:
            nc = np.clip(np.rint(G / (tp_ticks * TV)), 1, cap).astype(int)
        else:
            nc = np.minimum(fixed_nc, cap).astype(int)
        unit = nc * TV
        dist = b - f
        k = np.clip(np.ceil(dist / unit - 1e-9), 1, KMAX)
        if dll:
            k_dll = np.maximum(np.floor((dll - comm * nc) / unit), 1)   # stop propio bajo el DLL (incluye comision)
            k = np.where(dist > dll, np.minimum(k, k_dll), k)
        k = k.astype(int)
        tpk = np.clip(np.ceil((G + comm * nc) / unit - 1e-9), 1, TMAX).astype(int)
        ab = adv_bar[di, k]; tb = tp_bar[di, tpk]
        tp_hit = ((tb <= ab) & (tb < INF)) if tie_tp else (tb < ab)
        sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, tpk * unit, np.where(sl_hit, -k * unit, flat_ticks[di] * unit)) - comm * nc
        pnl = np.where(alive, pnl, 0.0)
        b = b + pnl
        f = np.where(alive & (b - mll > f), np.minimum(b - mll, lock), f)
        blown = alive & (b <= f)
        alive &= ~blown; res_day = np.where(blown & (res_day == max_days), d, res_day)
        best = np.where(alive & (pnl > best), pnl, best)
        need = np.maximum(target, best / cons) if cons else np.full(n, target)
        ok = alive & (b >= need) & (d >= min_days)
        passed |= ok; res_day = np.where(ok, d, res_day); alive &= ~ok
    return dict(pass_rate=passed.mean(), days_res=res_day.mean(), passed=passed, res_day=res_day)


def cost_per_pass(r, fee, reset, window_days=None, n_seq=20000, seed=3):
    """Costo esperado y dias esperados hasta el primer pase, con reinicios; window_days = ventana de acceso (Bulenox: 21 dias de trading ~ 30 calendario)."""
    rng = np.random.default_rng(seed); P, D = r["passed"], r["res_day"]; m = len(P)
    costs = np.zeros(n_seq); days = np.zeros(n_seq)
    for s in range(n_seq):
        c = fee; t = 0.0; tot = 0.0
        for _ in range(200):
            j = rng.integers(0, m); d = D[j]
            if window_days and t + d > window_days:
                c += fee; t = 0.0
            t += d; tot += d
            if P[j]: break
            c += reset
        costs[s] = c; days[s] = tot
    return costs.mean(), days.mean()


FIRMS = {  # mll, target, lock, dll, cons, min_days, nc_cap, comm, fee, reset, window
    "Tradeify Growth 50K": dict(mll=2000.0, target=3000.0, lock=100.0, dll=1250.0, cons=None, min_days=1, nc_cap=40, comm=1.82, fee=145, reset=95, window=None),
    "Tradeify Growth 50K (SI hubiera 35% de consistencia en eval)": dict(mll=2000.0, target=3000.0, lock=100.0, dll=1250.0, cons=0.35, min_days=3, nc_cap=40, comm=1.82, fee=145, reset=95, window=None),
    "Tradeify Select 50K (40% cons, min 3d, sin DLL)": dict(mll=2000.0, target=3000.0, lock=100.0, dll=None, cons=0.40, min_days=3, nc_cap=40, comm=1.82, fee=165, reset=109, window=None),
    "Bulenox Opcion 2 50K (escalado 20/40/70 micros)": dict(mll=2500.0, target=3000.0, lock=100.0, dll=1100.0, cons=None, min_days=1, nc_cap=bulenox50_cap, comm=1.22, fee=175, reset=78, window=21),
    "Topstep 50K (control, comision $1.22, lock 0)": dict(mll=2000.0, target=3000.0, lock=0.0, dll=None, cons=0.55, min_days=2, nc_cap=40, comm=1.22, fee=None, reset=None, window=None),
}

if __name__ == "__main__":
    T = build_tables(); nd = len(T[0]); allidx = np.arange(nd); h1, h2 = np.arange(nd // 2), np.arange(nd // 2, nd)
    for name, p in FIRMS.items():
        kw = {k: p[k] for k in ("mll", "target", "lock", "dll", "cons", "min_days", "nc_cap", "comm")}
        rows = []
        for tpt in (20, 30, 40, 50, 60, 80, 100, 120):
            for fr in (0.3, 0.45, 0.55, 0.75, 1.0):
                if p["cons"] and fr > p["cons"] + 1e-9: continue
                r = simulate(T, allidx, tp_ticks=tpt, g_cap=fr * p["target"], n=8000, **kw)
                rows.append((r["pass_rate"], tpt, fr))
        rows.sort(reverse=True)
        print(f"\n== {name} ==")
        for pr, tpt, fr in rows[:3]:
            f_ = simulate(T, allidx, tp_ticks=tpt, g_cap=fr * p["target"], n=60000, seed=11, **kw)
            a = simulate(T, h1, tp_ticks=tpt, g_cap=fr * p["target"], n=20000, **kw)
            b_ = simulate(T, h2, tp_ticks=tpt, g_cap=fr * p["target"], n=20000, **kw)
            t_ = simulate(T, allidx, tp_ticks=tpt, g_cap=fr * p["target"], n=60000, seed=11, tie_tp=True, **kw)
            line = (f"  tp_ticks={tpt:3d} g_cap={fr:.2f}T: pass={f_['pass_rate']:.3f} H1={a['pass_rate']:.3f} H2={b_['pass_rate']:.3f} "
                    f"(TP-primero en barras ambiguas={t_['pass_rate']:.3f}) dias/intento={f_['days_res']:.2f}")
            if p["fee"]:
                c, dd = cost_per_pass(f_, p["fee"], p["reset"], p["window"])
                line += f" | costo/pase=${c:,.0f} dias de trading hasta pase={dd:.1f}"
            print(line)
