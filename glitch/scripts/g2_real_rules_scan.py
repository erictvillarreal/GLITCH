"""
Combine 50K con las reglas OFICIALES reales (help.topstep.com, 24-sep-2026), sobre MES 5min real (bar-walk, 1 trade/dia alternando,
entrada 9:45 CT, flatten 14:30 CT, comision $1.22/contrato):
  * Consistency Target 55%: mejor dia <= 55% del profit total; si se excede, target = max($3,000, mejor_dia/0.55); el mejor dia
    NO se resetea con perdidas; recalculado con cada nuevo mejor dia. Minimo 2 dias.
  * MLL $2,000 trailing (piso sube con el balance EOD, tope en 0), monitoreado EN TIEMPO REAL con P&L no realizado: al tocarlo la
    cuenta se liquida (Combine perdido).
  * DLL $1,000 OPCIONAL: al tocarlo se liquida y se bloquea la sesion (no es falla).
Distancia de liquidacion de cada dia = distancia al piso (o al DLL); el SL efectivo es min(SL, distancia/(nc*tick_value)).
Tablas por dia precomputadas (primer toque de cada nivel adverso/favorable) -> simulacion path-dependiente exacta a nivel de barra 5min.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, itertools
from strategies.geometry_pure import trading_day_index, decide_side
from dd_wr.product_sweep import load_sessions

TICK, TV, COMM = 0.25, 1.25, 1.22
ENTRY_M, FLAT_M = 9 * 60 + 45, 14 * 60 + 30
MLL, TARGET, DLL_USD = 2000.0, 3000.0, 1000.0
KMAX, TMAX, INF = 400, 120, 10**6


def build_tables(with_dates=False):
    adv_bar, tp_bar, flat_ticks, dates = [], [], [], []
    for day, h, l, c, m in load_sessions("mes_5min_2y"):
        a = np.nonzero(m >= ENTRY_M)[0]
        if len(a) == 0: continue
        ep = int(a[0]); side = decide_side(trading_day_index(day), "alternate"); e = c[ep]
        jf = next((j for j in range(ep + 1, len(c)) if m[j] >= FLAT_M), len(c) - 1)
        if jf <= ep: continue
        hh, ll, cc = h[ep + 1:jf + 1], l[ep + 1:jf + 1], c[ep + 1:jf + 1]
        fav = ((hh - e) if side == 1 else (e - ll)) / TICK
        adv = ((e - ll) if side == 1 else (hh - e)) / TICK
        M, F = np.maximum.accumulate(adv), np.maximum.accumulate(fav)
        ai = np.searchsorted(M, np.arange(1, KMAX + 1), side="left"); ai = np.where(ai >= len(M), INF, ai)
        ti = np.searchsorted(F, np.arange(1, TMAX + 1), side="left"); ti = np.where(ti >= len(F), INF, ti)
        adv_bar.append(np.concatenate([[INF], ai])); tp_bar.append(np.concatenate([[INF], ti]))
        flat_ticks.append((cc[-1] - e) * side / TICK); dates.append(str(day))
    out = (np.array(adv_bar), np.array(tp_bar), np.array(flat_ticks))
    return (out, dates) if with_dates else out


def simulate(T, days_idx, nc, tp, sl, dll=False, cons=0.55, n=20000, max_days=15, seed=7, min_days=2, liquidate=True):
    adv_bar, tp_bar, flat_ticks = T
    rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -MLL); alive = np.ones(n, bool); best = np.zeros(n)
    passed = np.zeros(n, bool); res_day = np.full(n, max_days)
    unit = nc * TV
    for d in range(1, max_days + 1):
        di = days_idx[rng.integers(0, len(days_idx), n)]
        dist = (b - f) if liquidate else np.full(n, 1e12)
        if dll: dist = np.minimum(dist, DLL_USD)
        k = np.clip(np.minimum(sl, np.ceil(dist / unit - 1e-9)), 1, KMAX).astype(int)
        ab = adv_bar[di, k]; tb = tp_bar[di, tp]
        tp_hit = tb < ab
        sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, tp * unit, np.where(sl_hit, -k * unit, flat_ticks[di] * unit)) - COMM * nc
        pnl = np.where(alive, pnl, 0.0)
        b = b + pnl
        f = np.where(alive & (b - MLL > f), np.minimum(b - MLL, 0.0), f)
        blown = alive & (b <= f)
        alive &= ~blown; res_day = np.where(blown & (res_day == max_days), d, res_day)
        best = np.where(alive & (pnl > best), pnl, best)
        need = np.maximum(TARGET, best / cons) if cons else TARGET
        ok = alive & (b >= need) & (d >= min_days)
        passed |= ok; res_day = np.where(ok, d, res_day); alive &= ~ok
    pr = passed.mean(); rd = res_day.mean(); pd_ = res_day[passed].mean() if passed.any() else np.nan
    return dict(pass_rate=pr, blow=(~passed & ~alive).mean(), days_pass=pd_, days_res=rd, passes_yr=pr * 252 / rd)


if __name__ == "__main__":
    T = build_tables(); nd = len(T[0]); allidx = np.arange(nd)
    print(f"dias MES: {nd}. MOTOR: bar-walk 5min con liquidacion MLL/DLL en tiempo real + consistencia oficial 55%.\n")
    print("== G2 (nc=40, TP 40, SL 100) bajo cada regla (pass, dias a pase, pases/año = pass*252/dias_resolucion)")
    for lbl, kw in (("SIN consistencia, SIN liquidacion intradia (= contabilidad del paper: SL 100 se ejecuta completo, quiebre EOD)", dict(dll=False, cons=None, liquidate=False)),
                    ("consistencia 55%, SIN liquidacion intradia", dict(dll=False, cons=0.55, liquidate=False)),
                    ("consistencia 55% + liquidacion MLL real, DLL off (regla real por defecto)", dict(dll=False, cons=0.55)),
                    ("consistencia 55% + liquidacion MLL real, DLL on (-$1,000)", dict(dll=True, cons=0.55)),
                    ("consistencia OFF + liquidacion MLL real, DLL off (aisla la liquidacion)", dict(dll=False, cons=None)),
                    ("consistencia 50% + liquidacion MLL real, DLL off", dict(dll=False, cons=0.50))):
        r = simulate(T, allidx, 40, 40, 100, **kw)
        print(f"   {lbl}: pass={r['pass_rate']:.3f} blow={r['blow']:.3f} dias_pase={r['days_pass']:.2f} dias_res={r['days_res']:.2f} pases/ano={r['passes_yr']:.1f}")
