"""
Politica "audaz adaptativa" sobre barras REALES de MES (mismas tablas first-touch que g2_real_rules_scan.py).

Idea (viene de la cota de juego justo, scripts/pass_rate_ceiling_dp.py): sin edge, la mejor politica es apostar CADA dia solo lo
necesario para terminar (target restante R), con el stop = distancia al piso (liquidacion). nc se ajusta cada dia:
    G_hoy = min(R, g_cap)        (g_cap respeta la consistencia: ningun dia > cons * target)
    nc    = round(G_hoy / (tp_ticks * 1.25)) acotado a [1, nc_cap]
    TP    = ceil(G_hoy / (nc*1.25)) ticks (<=120, limite de la tabla);  SL = liquidacion (o DLL si aplica)
Esto NO es el G2 de nc fijo: es la unica familia de geometrias que el barrido anterior (nc/TP/SL fijos) no cubria.
Mismo motor, mismas reglas oficiales, misma historia de 515 dias -> mismas limitaciones (una historia, barras de 5 min,
SL primero en barras ambiguas, sin slippage de liquidacion).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.g2_real_rules_scan import build_tables, TV, COMM, KMAX, TMAX, INF


def simulate_bold(T, days_idx, mll, target, tp_ticks, g_cap, nc_cap, dll=None, cons=0.55, min_days=2, max_days=30,
                  n=20000, seed=7, comm=COMM, fixed_nc=None, tie_tp=False):
    adv_bar, tp_bar, flat_ticks = T
    rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -mll); alive = np.ones(n, bool); best = np.zeros(n)
    passed = np.zeros(n, bool); res_day = np.full(n, max_days)
    for d in range(1, max_days + 1):
        di = days_idx[rng.integers(0, len(days_idx), n)]
        need_tot = np.maximum(target, best / cons) if cons else np.full(n, target)
        R = np.maximum(need_tot - b, 1.0)
        G = np.minimum(R, g_cap)
        nc = np.clip(np.rint(G / (tp_ticks * TV)), 1, nc_cap).astype(int) if fixed_nc is None else np.full(n, fixed_nc)
        unit = nc * TV
        dist = b - f
        if dll: dist = np.minimum(dist, dll)
        k = np.clip(np.ceil(dist / unit - 1e-9), 1, KMAX).astype(int)
        tpk = np.clip(np.ceil((G + comm * nc) / unit - 1e-9), 1, TMAX).astype(int)   # bruto = neto + comision
        ab = adv_bar[di, k]; tb = tp_bar[di, tpk]
        tp_hit = (tb <= ab) & (tb < INF) if tie_tp else (tb < ab)
        sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, tpk * unit, np.where(sl_hit, -k * unit, flat_ticks[di] * unit)) - comm * nc
        pnl = np.where(alive, pnl, 0.0)
        b = b + pnl
        f = np.where(alive & (b - mll > f), np.minimum(b - mll, 0.0), f)
        blown = alive & (b <= f)
        alive &= ~blown; res_day = np.where(blown & (res_day == max_days), d, res_day)
        best = np.where(alive & (pnl > best), pnl, best)
        need = np.maximum(target, best / cons) if cons else np.full(n, target)
        ok = alive & (b >= need) & (d >= min_days)
        passed |= ok; res_day = np.where(ok, d, res_day); alive &= ~ok
    pr = passed.mean(); rd = res_day.mean()
    return dict(pass_rate=pr, days_res=rd, days_pass=res_day[passed].mean() if passed.any() else np.nan,
                passes_yr=pr * 252 / rd)


FIRMS = {  # mll, target, dll, cons, min_days, nc_cap  (50K; parametros verificados en el log del 30-sep; Topstep oficial 24-sep)
    "Topstep 50K": (2000.0, 3000.0, None, 0.55, 2, 40),
    "Tradeify 50K": (2000.0, 3000.0, 1250.0, None, 1, 40),
    "Bulenox 50K": (2500.0, 3000.0, 1100.0, None, 1, 40),
}

if __name__ == "__main__":
    T = build_tables(); nd = len(T[0]); allidx = np.arange(nd)
    h1, h2 = np.arange(nd // 2), np.arange(nd // 2, nd)
    for name, (mll, tgt, dll, cons, md, ncc) in FIRMS.items():
        rows = []
        for tpt in (20, 30, 40, 50, 60, 80, 100, 120):
            for fr in (0.3, 0.45, 0.55, 0.75, 1.0):
                cap = fr * tgt
                if cons and fr > cons: continue
                r = simulate_bold(T, allidx, mll, tgt, tpt, cap, ncc, dll=dll, cons=cons, min_days=md, n=8000)
                rows.append((r["pass_rate"], tpt, fr, r["days_res"]))
        rows.sort(reverse=True)
        print(f"\n== {name}: top-5 de barrido audaz (n=8000) ==")
        for pr, tpt, fr, dr in rows[:5]:
            a = simulate_bold(T, h1, mll, tgt, tpt, fr * tgt, ncc, dll=dll, cons=cons, min_days=md, n=20000)
            b_ = simulate_bold(T, h2, mll, tgt, tpt, fr * tgt, ncc, dll=dll, cons=cons, min_days=md, n=20000)
            f_ = simulate_bold(T, allidx, mll, tgt, tpt, fr * tgt, ncc, dll=dll, cons=cons, min_days=md, n=60000, seed=11)
            print(f"  tp_ticks={tpt:3d} g_cap={fr:.2f}T: pass(scan)={pr:.3f}  full(60k)={f_['pass_rate']:.3f}  H1={a['pass_rate']:.3f} H2={b_['pass_rate']:.3f} "
                  f"dias_res={f_['days_res']:.2f} pases/ano={f_['passes_yr']:.1f}")
