"""Parte H, H3: P7 (tamaño por volatilidad, estadística) y prueba 8 (filtro / ATR / tamaño bajo WR 47.4, 48.5, 50, 52 %; cadena Combine → XFA con costo de saltar días). -> resultados_H3_dinero.md, h3_pvals_dinero.json
    GLITCH_MGC_PARQUET=... python h3_dinero.py"""
import json, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
from scaled_days import ScaledDays
SEED = 20261024; t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
dd = mgc_days(True); D = dd.D; mk = gold_mask(dd, True)
Rt = np.maximum(dd.hi.max(1), 0) - np.minimum(dd.lo.min(1), 0); lr = np.log(Rt)
F = np.full(D, np.nan)
for t in range(120, D):
    rows = list(range(20, t)); A = np.array([[1.0, math.log(Rt[s - 1]), np.log(Rt[s - 5:s]).mean(), np.log(Rt[s - 20:s]).mean()] for s in rows])
    beta = np.linalg.lstsq(A, lr[rows], rcond=None)[0]; F[t] = beta @ np.array([1.0, math.log(Rt[t - 1]), np.log(Rt[t - 5:t]).mean(), np.log(Rt[t - 20:t]).mean()])
sel = np.arange(D) >= 120; pool_base = sel & mk
op = np.exp(np.nan_to_num(F, nan=0)) >= 364.0
m20 = np.full(D, np.nan)
for t in range(20, D): m20[t] = Rt[t - 20:t].mean()
k = 364.0 / np.nanmedian(m20)
W_atr = np.where(np.isnan(m20), 364, np.clip(np.round(k * m20 / 50.0) * 50, 200, 800)).astype(int); nc_atr = np.clip(np.round(1092.0 / W_atr), 1, 6).astype(int)
med = np.median(np.exp(F[sel])); nc_size = np.clip(np.round(3 * med / np.exp(np.nan_to_num(F, nan=math.log(med)))), 1, 6).astype(int)
W364 = np.full(D, 364)
P("# resultados_H3 (dinero) — P7 y prueba 8\n")
P(f"Base de comparación: {int(pool_base.sum())} días (t ≥ 120 y sin la ventana de oro). Filtro: opera {int((pool_base & op).sum())} ({(pool_base & op).sum() / pool_base.sum() * 100:.0f} %). ATR: k = {k:.3f}. Tamaño: m = mediana del rango pronosticado = {med:.0f} ticks; nc_t ∈ [1, 6], distribución " + ", ".join(f"{n}: {int((nc_size[pool_base] == n).sum())}" for n in sorted(set(nc_size[pool_base]))) + ".\n")
mes = load_days(); cb = combine_bank(mes, 100000, "P0", (1.0, 3.0), (0.5, 0.5), seed=11)
def arm(name, wr, dm):
    if name in ("base", "filtro"):
        days = BarDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=(pool_base if name == "base" else pool_base & op), cush_max=9000.0, drift=dm, stop_frac=0.5)
        share = 1.0 if name == "base" else (pool_base & op).sum() / pool_base.sum()
    else:
        W, N = (W_atr, nc_atr) if name == "ATR" else (W364, nc_size)
        days = ScaledDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=pool_base, cush_max=9000.0, drift=dm, stop_frac=0.5, Wd=W, ncd=N); share = 1.0
    return days, share
def metrics(days, share, n, seed, chain=True):
    r = simulate_life(days, Rules(), pol_fixed(3, 364, 364), n=n, seed=seed, record_k=14)
    net = r["pay_net"].sum(1); pay = r["npay"] > 0; fp = r["first_pay_day"]
    m = dict(cob=net.mean(), p1=pay.mean(), t1=np.median(fp[pay]) / share if pay.any() else float("nan"))
    if chain:
        life = np.ceil(r["life"].astype(int) / share).astype(int); pday = np.where(r["pay_day"] >= 0, np.ceil(r["pay_day"] / share), r["pay_day"]).astype(int)
        m["net"] = float(run_chain(cb[0], cb[1], life, pday, r["pay_net"], n=30000, seed=5)["net"].mean())
    return m
rows = []
P("## Prueba 8. Tres usos del pronóstico bajo escenarios de WR_dec (ventaja por deriva en la XFA; Combine hoy P0 mezcla {1,3}; stop 0.5)\n")
P("| WR_dec | uso | cobrado por XFA | P(≥1 pago) | mediana de días de calendario al 1.er pago | neto $/año/cuenta | Δ neto vs base |\n|---|---|---|---|---|---|---|")
for wr in (0.474, 0.485, 0.50, 0.52):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(dd, mk, wr); base_net = None
    for nm in ("base", "filtro", "ATR", "tamaño"):
        days, share = arm(nm, wr, dm); m = metrics(days, share, 40000, 21)
        if nm == "base": base_net = m["net"]
        dlt = "" if nm == "base" else format(m["net"] - base_net, "+,.0f")
        P(f"| {wr * 100:.1f} % | {nm} | ${m['cob']:,.0f} | {m['p1'] * 100:.1f} % | {m['t1']:.0f} | ${m['net']:,.0f} | {dlt} |")
        print("  ", wr, nm, round(time.time() - t0), "s", flush=True)
P("\nRuido de nivel ±$100; las diferencias entre usos del pronóstico en un mismo WR comparten números aleatorios. Piso: +$500/año/cuenta.\n")
# P7: bootstrap pareado del cobrado (tamaño vs base) a WR 50 %
B = 100; rng = np.random.default_rng(SEED); pool_idx = np.nonzero(pool_base)[0]
db, ds = arm("base", 0.5, 0.0)[0], arm("tamaño", 0.5, 0.0)[0]; diffs = []
for b in range(B):
    st = rng.integers(0, len(pool_idx) - 4, size=math.ceil(len(pool_idx) / 5)); sub = pool_idx[(st[:, None] + np.arange(5)[None, :]).ravel()[:len(pool_idx)]]
    v = []
    for dz in (db, ds):
        dz.pool = sub; r = simulate_life(dz, Rules(), pol_fixed(3, 364, 364), n=8000, seed=100 + b, record_k=14); v.append(r["pay_net"].sum(1).mean())
    diffs.append(v[1] - v[0])
diffs = np.array(diffs); p7 = float((diffs <= 0).mean())
P(f"### P7 — tamaño por volatilidad en la XFA (WR 50 %): diferencia de cobrado por XFA (tamaño − fijo) media {diffs.mean():+,.0f}, IC95 [{np.percentile(diffs, 2.5):+,.0f}, {np.percentile(diffs, 97.5):+,.0f}]; p unilateral (> 0) = {p7:.3f} ({B} remuestras, bancos de 8,000).")
json.dump({"P7 tamaño": p7}, open(os.path.join(HERE, "h3_pvals_dinero.json"), "w"))
open(os.path.join(HERE, "resultados_H3_dinero.md"), "w", encoding="utf-8").write("\n".join(out))
