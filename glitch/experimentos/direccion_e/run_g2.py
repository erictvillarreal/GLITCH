"""Parte G, G2: T1, T2, T3, T5, T6 (T4 aparte: run_g2_t4.py) y prueba de dinero del filtro de T3, EXACTAMENTE como en PREREGISTRO_G2.md. -> resultados_G2.md, g2_pvals.json
    GLITCH_MGC_PARQUET=... python run_g2.py"""
import datetime as dt, json, math, os, sys, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from common_e import load_daily
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
SEED = 20261024
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
pv = {}

def block_idx(n, block, B, rng):
    nb = math.ceil(n / block); st = rng.integers(0, n - block + 1, size=(B, nb))
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]

def har_oos(y, extra=None, min_train=756):
    cols = ["l1", "m5", "m20"] + ([] if extra is None else ["ex"])
    X = pd.DataFrame({"l1": y.shift(1), "m5": y.shift(1).rolling(5).mean(), "m20": y.shift(1).rolling(20).mean()})
    if extra is not None: X["ex"] = extra.reindex(y.index)
    d = pd.concat([y.rename("y"), X], axis=1).dropna()
    se_m, se_b, yrs = [], [], {}
    for Y in sorted(set(d.index.year)):
        tr, te = d[d.index < f"{Y}-01-01"], d[d.index.year == Y]
        if len(tr) < min_train or len(te) == 0: continue
        A = np.c_[np.ones(len(tr)), tr[cols].values]; beta = np.linalg.lstsq(A, tr.y.values, rcond=None)[0]
        pr = (np.c_[np.ones(len(te)), te[cols].values] * beta).sum(1)    # sin '@': evita avisos espurios de Accelerate/numpy 2.0 en macOS
        em, eb = (te.y.values - pr) ** 2, (te.y.values - tr.y.mean()) ** 2
        se_m += list(em); se_b += list(eb); yrs[Y] = 1 - em.sum() / eb.sum()
    se_m, se_b = np.array(se_m), np.array(se_b)
    return 1 - se_m.sum() / se_b.sum(), yrs, se_b - se_m, beta, cols

def t_har(label, key, y, extra=None):
    r2, yrs, diff, beta, cols = har_oos(y, extra)
    rng = np.random.default_rng(SEED); ix = block_idx(len(diff), 20, 5000, rng); bm = diff[ix].mean(1)
    p = float((bm <= 0).mean()); pv[key] = p
    pos = np.mean([v > 0 for v in yrs.values()])
    P(f"\n### {key} — {label}\n- R²_OOS agrupado = **{r2 * 100:.2f} %** ({len(diff):,} días, {min(yrs)}–{max(yrs)}); años con R² > 0: **{pos * 100:.0f} %** ({sum(v > 0 for v in yrs.values())}/{len(yrs)}); p unilateral (bloques de 20 d) = {p:.4f}.")
    P("- Coeficientes del último ajuste (" + ", ".join(f"{c}={b:+.3f}" for c, b in zip(["const"] + cols, beta)) + ").")
    P("- R²_OOS por año: " + " · ".join(f"{k}: {v * 100:.0f} %" for k, v in yrs.items()))
    return r2, pos

P("# resultados_G2 — volatilidad en lugar de dirección (pre-registro `PREREGISTRO_G2.md`, commit 5ca5252, antes de estos resultados)\n")
gc = load_daily("GC=F"); gc = gc[(gc.Volume > 0) & (gc.High > gc.Low)]
gs = load_daily("^GSPC"); gs = gs[gs.High > gs.Low]
ygc = np.log(gc.High / gc.Low); ygs = np.log(gs.High / gs.Low)
gap = np.abs(np.log(gs.Open / gs.Close.shift(1))).dropna()
P(f"Datos: GC=F {len(gc):,} días con volumen (de {len(load_daily('GC=F')):,}); ^GSPC {len(gs):,} días.")
t_har("oro (GC=F), log-rango H/L diario, HAR de 3 términos", "T1 GC=F", ygc)
t_har("^GSPC RTH, log-rango H/L diario, HAR + |brecha|", "T2 ^GSPC", ygs, gap)

# ── T5 / T6: FOMC ──
fomc = [dt.date.fromisoformat(l.strip()) for l in open(os.path.join(HERE, "fomc_dates.txt")) if l[0] != "#" and l.strip()]
def t_fomc(label, key, y):
    y = y[y.index >= "2021-01-01"]; flag = np.array([d.date() in set(fomc) for d in y.index]); v = y.values
    n = len(v); diff0 = v[flag].mean() - v[~flag].mean()
    rng = np.random.default_rng(SEED); ix = block_idx(n, 5, 10000, rng); f = flag[ix]; w = v[ix]
    a = (w * f).sum(1) / np.maximum(f.sum(1), 1); b = (w * ~f).sum(1) / np.maximum((~f).sum(1), 1); d = a - b
    p = float((d <= 0).mean()); pv[key] = p
    P(f"\n### {key} — {label}\n- {int(flag.sum())} días FOMC de {n}; log-rango medio {v[flag].mean():.4f} vs {v[~flag].mean():.4f}: diferencia **{diff0:+.4f}** (cociente de rangos medios ≈ ×{v[flag].mean() / v[~flag].mean():.2f}); IC95 [{np.percentile(d, 2.5):+.4f}, {np.percentile(d, 97.5):+.4f}]; p unilateral = {p:.4f}.")
t_fomc("^GSPC (RTH), días de anuncio 2021–2026", "T5 FOMC ^GSPC", ygs)
t_fomc("oro (GC=F), días de anuncio 2021–2026", "T6 FOMC GC=F", ygc)

# ── T3: filtro por rango pronosticado en MGC ──
dd = mgc_days(True); D = dd.D
Rt = np.maximum(dd.hi.max(1), 0) - np.minimum(dd.lo.min(1), 0)           # rango de la ventana en ticks (la referencia es el precio 0)
lr = np.log(Rt)
F = np.full(D, np.nan)
for t in range(120, D):
    idx = np.arange(21, t) if t > 21 else np.arange(0)
    rows = [s for s in range(20, t)]                                          # filas de entrenamiento: dias s con 20 previos y s < t
    A = np.array([[1.0, math.log(Rt[s - 1]), np.log(Rt[s - 5:s]).mean(), np.log(Rt[s - 20:s]).mean()] for s in rows]); yv = lr[rows]
    beta = np.linalg.lstsq(A, yv, rcond=None)[0]
    F[t] = beta @ np.array([1.0, math.log(Rt[t - 1]), np.log(Rt[t - 5:t]).mean(), np.log(Rt[t - 20:t]).mean()])
op = np.exp(F) >= 364.0
alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
k = np.where(alt == 1, sim_day(dd, 1, 3, 9000.0, slip=0.0, exit_slip=0.0, sl=364, tp=364, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5)[0], sim_day(dd, -1, 3, 9000.0, slip=0.0, exit_slip=0.0, sl=364, tp=364, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5)[0])
dec = (k != 3).astype(float); fl = 1 - dec
sel = np.arange(D) >= 120
o, n_ = op & sel, (~op) & sel
d0 = dec[o].mean() - dec[n_].mean()
rng = np.random.default_rng(SEED); m = sel.sum(); ix = block_idx(m, 5, 10000, rng)
decs, ops = dec[sel][ix], op[sel][ix]
a = (decs * ops).sum(1) / np.maximum(ops.sum(1), 1); b = (decs * ~ops).sum(1) / np.maximum((~ops).sum(1), 1); dd_ = a - b
pv["T3 MGC filtro"] = float((dd_ <= 0).mean())
corr = np.corrcoef(F[sel], lr[sel])[0, 1]; r2f = 1 - ((lr[sel] - F[sel]) ** 2).sum() / ((lr[sel] - lr[:120].mean()) ** 2).sum()
exp_mean = np.array([lr[:t].mean() for t in range(D)]); r2e = 1 - ((lr[sel] - F[sel]) ** 2).sum() / ((lr[sel] - exp_mean[sel]) ** 2).sum()
P(f"\n### T3 — V2 en MGC intradía (filtro: operar si exp(F_t) ≥ 364)\n- Días de prueba (t ≥ 120): {sel.sum()}; **operados {o.sum()} ({o.sum() / sel.sum() * 100:.0f} %)**, saltados {n_.sum()}. Correlación (ln R pronosticado, ln R real) = {corr:.2f}; R² fuera de muestra vs media fija de los primeros 120 días = {r2f * 100:.1f} % (inflado por el cambio de régimen de volatilidad) y **vs media expansiva = {r2e * 100:.1f} %** (la comparación justa).")
P(f"- Fracción decidida (TP o SL): **operados {dec[o].mean() * 100:.1f} %** vs saltados {dec[n_].mean() * 100:.1f} % vs todos {dec[sel].mean() * 100:.1f} %. Diferencia = **{d0 * 100:+.1f} pp** [IC95 {np.percentile(dd_, 2.5) * 100:+.1f}, {np.percentile(dd_, 97.5) * 100:+.1f}]; p unilateral = {pv['T3 MGC filtro']:.4f}. FLATTEN: operados {fl[o].mean() * 100:.1f} % vs todos {fl[sel].mean() * 100:.1f} %.")
by_blk = [dec[o & (np.arange(D) >= a_) & (np.arange(D) < b_)].mean() if (o & (np.arange(D) >= a_) & (np.arange(D) < b_)).any() else float('nan') for a_, b_ in ((120, 220), (220, 320), (320, 420), (420, D))]
P("- Fracción decidida entre operados por bloque cronológico (4): " + " · ".join(f"{x * 100:.0f} %" for x in by_blk) + ".")
# ── prueba de dinero del filtro ──
t0 = time.time(); mes = load_days(); mk = gold_mask(dd, True)
NB, NC = 100000, 40000
cb = combine_bank(mes, NB, "P0", (1.0, 3.0), (0.5, 0.5), seed=11)
def money(mask, share):
    days = BarDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mask, cush_max=9000.0, stop_frac=0.5)
    life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), NB, seed=21)
    life_s = np.ceil(life / share).astype(int); pday_s = np.where(pday >= 0, np.ceil(pday / share), pday).astype(int)
    r = run_chain(cb[0], cb[1], life_s, pday_s, pnet, n=NC, seed=5)
    first = np.where((pday >= 0).any(1), np.where(pday >= 0, pday, 10 ** 6).min(1), -1)
    return dict(cobrado=float(pnet.sum(1).mean()), p1=float((pnet.sum(1) > 0).mean()), t1=float(np.median(first[first >= 0] / share)) if (first >= 0).any() else float("nan"), net=float(r["net"].mean()), life=float(life_s.mean()))
base_mask = sel & mk; filt_mask = o & mk
sh = filt_mask.sum() / base_mask.sum()
rb, rf = money(base_mask, 1.0), money(filt_mask, sh)
P(f"\n### Prueba de dinero de T3 (W2: sin la ventana de oro; {base_mask.sum()} días base, {filt_mask.sum()} operados = {sh * 100:.0f} %; duraciones reescaladas por 1/{sh:.2f})")
P("| | cobrado por XFA | P(≥1 pago) | mediana de días de calendario al 1.er pago | vida media (días cal.) | neto $/año/cuenta |\n|---|---|---|---|---|---|")
P(f"| sin filtro | ${rb['cobrado']:,.0f} | {rb['p1'] * 100:.1f} % | {rb['t1']:.0f} | {rb['life']:.1f} | ${rb['net']:,.0f} |")
P(f"| con filtro | ${rf['cobrado']:,.0f} | {rf['p1'] * 100:.1f} % | {rf['t1']:.0f} | {rf['life']:.1f} | ${rf['net']:,.0f} |")
P(f"\nDiferencia en $/año/cuenta: **{rf['net'] - rb['net']:+,.0f}** (piso: +$500). Ruido de nivel ±$100; pruebas pareadas por bootstrap de días no corridas aquí (la muestra de operados es pequeña: IC ancho).")
json.dump(pv, open(os.path.join(HERE, "g2_pvals.json"), "w"))
open(os.path.join(HERE, "resultados_G2.md"), "w").write("\n".join(out))
