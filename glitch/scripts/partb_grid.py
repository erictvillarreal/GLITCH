"""
PARTE B: geometria Camino B (sin edge, alternar) con las reglas reales como restriccion DURA de diseño:
  - liquidacion MLL en tiempo real (distancia al piso trailing), consistencia 55%, minimo 2 dias, Combine 50K, DLL off
  - SL en $ <= 40% del MLL ($800) [tambien 15% y 25%], nc <= 25 micros (50% del maximo) o <= 2 minis (ZN/ZC)
  - productos MES/MGC/M2K/MCL/M6E/ZN/ZC, 3 horas de entrada, ancho de SL relativo al rango diario (c x R), RR 0.5..3
Metricas: pass, dias por intento, COSTO ESPERADO POR PASE (fees por intento / p, renovacion cada 21 dias, + $149 activacion),
dias esperados por pase, y PROXIES de conducta (no hay umbrales numericos oficiales): nc/maximo, SL$/TP$ y toques de MLL por 100 dias.
"""
import os, sys, itertools, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.xfa_liquidation_check import tables, KMAX, INF

MLL, TARGET, FEE, ACT = 2000.0, 3000.0, 49.0, 149.0
# nombre: (parquet, tick, tv, comm, nc_max, entradas CT (min), flatten (min))
PRODUCTS = {
    "MES": ("mes_5min_2y", 0.25, 1.25, 1.22, 25, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 14 * 60 + 30),
    "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 1.92, 25, [7 * 60 + 13, 8 * 60 + 43, 9 * 60 + 45], 14 * 60 + 30),
    "M2K": ("m2k_5min_2y", 0.10, 0.50, 1.22, 25, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 14 * 60 + 30),
    "MCL": ("mcl_5min_2y", 0.01, 1.00, 1.52, 25, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 14 * 60 + 30),
    "M6E": ("m6e_5min_2y", 0.0001, 1.25, 1.00, 25, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 14 * 60 + 30),
    "ZN": ("zn_5min_2y", 0.015625, 15.625, 2.62, 2, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 14 * 60 + 30),
    "ZC": ("zc_5min_2y", 0.25, 12.50, 5.28, 2, [8 * 60 + 43, 9 * 60 + 45, 10 * 60 + 45], 12 * 60 + 45),
}


def simulate(T, days, nc, tp, sl, tv, comm, n=12000, max_days=40, seed=7, cons=0.55, dll=None, slip=0):
    adv, tpt, flat = T
    rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -MLL); alive = np.ones(n, bool); best = np.zeros(n)
    passed = np.zeros(n, bool); blown_ = np.zeros(n, bool); res = np.full(n, max_days); unit = nc * tv
    for d in range(1, max_days + 1):
        di = days[rng.integers(0, len(days), n)]
        dist = b - f
        if dll: dist = np.minimum(dist, dll)
        k = np.clip(np.minimum(sl, np.ceil(dist / unit - 1e-9)), 1, KMAX).astype(int)
        ab = adv[di, k]; tb = tpt[di, tp]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, tp * unit, np.where(sl_hit, -k * unit, flat[di] * unit)) - (comm + slip * tv * 2 * 0) * nc - slip * tv * nc * (1 + sl_hit)
        pnl = np.where(alive, pnl, 0.0)
        b += pnl
        f = np.where(alive & (b - MLL > f), np.minimum(b - MLL, 0.0), f)
        bl = alive & (b <= f); alive &= ~bl; blown_ |= bl; res = np.where(bl, d, res)
        best = np.where(alive & (pnl > best), pnl, best)
        ok = alive & (b >= np.maximum(TARGET, best / cons)) & (d >= 2)
        passed |= ok; res = np.where(ok, d, res); alive &= ~ok
    p = passed.mean()
    fee_att = (FEE * (1 + (res - 1) // 21)).mean()
    return dict(p=p, blow=blown_.mean(), days_pass=res[passed].mean() if p > 0 else np.nan, days_res=res.mean(),
                cost_pass=(fee_att / p + ACT) if p > 0 else np.inf, days_per_pass=(res.mean() / p) if p > 0 else np.inf,
                hits100=100 * blown_.mean() / res.mean())


def configs(R, tv, nc_max):
    seen = set()
    for c, sld, rr in itertools.product([0.04, 0.07, 0.10, 0.15, 0.20, 0.30], [300, 500, 800], [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
        sl = max(1, int(round(c * R))); nc = int(np.clip(round(sld / (sl * tv)), 1, nc_max))
        if nc * sl * tv > 880: continue
        tp = max(1, int(round(rr * sl)))
        if tp > 490 or sl > 490: continue
        if (nc, tp, sl) in seen: continue
        seen.add((nc, tp, sl)); yield nc, tp, sl, rr


if __name__ == "__main__":
    t0 = time.time(); rows = []
    for name, (stem, tick, tv, comm, ncmax, entries, flat) in PRODUCTS.items():
        for em in entries:
            T = tables(stem, tick, em, flat); nd = len(T[0])
            # rango mediano entrada->flatten en ticks (aprox. via primer toque del nivel adverso mediano no disponible) -> usar fav/adv tables:
            R = float(np.median([np.searchsorted(np.arange(KMAX + 1), 0) or 0 for _ in range(1)]))  # placeholder, se recalcula abajo
            adv_ok = np.where(T[0] < INF, 1, 0)                     # niveles adversos alcanzados por dia
            R = float(np.median(adv_ok[:, 1:].sum(axis=1)))         # = adversidad maxima mediana en ticks (<= KMAX)
            idx = np.arange(nd); h1, h2 = idx[: nd // 2], idx[nd // 2:]
            for nc, tp, sl, rr in configs(max(R, 10), tv, ncmax):
                r = simulate(T, idx, nc, tp, sl, tv, comm)
                rows.append(dict(prod=name, entry=em, nc=nc, tp=tp, sl=sl, rr=rr, sl_usd=nc * sl * tv, tp_usd=nc * tp * tv, frac_max=nc / (2 if ncmax == 2 else 50) if ncmax != 2 else nc / 5, **r,
                                 H1=simulate(T, h1, nc, tp, sl, tv, comm, n=6000)["cost_pass"], H2=simulate(T, h2, nc, tp, sl, tv, comm, n=6000)["cost_pass"]))
        print(f"[{name}] listo, {len(rows)} configs acumuladas, {time.time()-t0:.0f}s", flush=True)
    import pandas as pd
    df = pd.DataFrame(rows); df.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "partb_grid_results.csv"), index=False)
    print(f"\nTotal {len(df)} configs")
    good = df[(df.p > 0.05)].sort_values("cost_pass")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    cols = ["prod", "entry", "nc", "tp", "sl", "rr", "sl_usd", "tp_usd", "frac_max", "p", "days_pass", "days_per_pass", "cost_pass", "hits100", "H1", "H2"]
    print("TOP 20 por costo esperado por pase (SL$<=880, nc<=25):"); print(good[cols].head(20).round(3).to_string(index=False))
    print("\nTOP 10 con RR>=1 (perdida <= ganancia):"); print(good[good.rr >= 1.0][cols].head(10).round(3).to_string(index=False))
    print("\nMejor por producto:"); print(good.groupby("prod").head(1)[cols].round(3).to_string(index=False))
