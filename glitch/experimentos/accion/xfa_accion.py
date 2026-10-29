"""ACCIÓN (28-oct-2026): la XFA 50K ya está fondeada. Motor exacto de la XFA (xfa_engine, reglas verificadas de la Parte D) con MES vs MGC (Cerebro 2), objetivo de CORTO PLAZO:
dinero cobrado en los primeros 10/20/30/60 días hábiles y tiempo al primer pago. -> resultados_ACCION.md
    cd glitch/experimentos/accion; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 xfa_accion.py [--quick]
MODELADO sobre días reales de 5 min (2 años). Plan elegido en el 60 % cronológico más viejo y reportado en el 40 % más reciente. Etiqueta de WR = deriva calibrada en el bracket nominal (½ del rango mediano)."""
import argparse, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "labs")); sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from labs_motor import calib_drift
from daydata import DayData, load_days
from worlds import mgc_days, gold_mask
from xfa_engine import BarDays, Policy, Rules, plan_cap, simulate_life
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); A = ap.parse_args()
N_SEL = 6000 if A.quick else 12000; N_REP = 12000 if A.quick else 40000; B = 8 if A.quick else 20
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
DC = os.path.join(HERE, "..", "..", "data_cache")
SPEC = {"MES": dict(tv=1.25, fee=1.22, hi=865, ref=575, fn="mes_5min_2y.parquet"), "MGC": dict(tv=1.00, fee=1.92, hi=865, ref=435, fn=None)}
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
dd_all, mask_all = {}, {}
dd_all["MES"] = load_days(os.path.join(DC, SPEC["MES"]["fn"]), SPEC["MES"]["ref"], SPEC["MES"]["hi"], 0.25, fill_gaps=True, dominant_contract=True); mask_all["MES"] = np.ones(dd_all["MES"].D, bool)
dd_all["MGC"] = mgc_days(True); mask_all["MGC"] = gold_mask(dd_all["MGC"], True)
def sub(dd, idx):
    return DayData([dd.dates[i] for i in idx], dd.ref[idx], dd.op[idx], dd.hi[idx], dd.lo[idx], dd.cl[idx], [])
TR, TE, RMED, HALF = {}, {}, {}, {}
for p, dd in dd_all.items():
    keep = np.nonzero(mask_all[p])[0]; dd = sub(dd, keep); k = int(dd.D * 0.6)
    TR[p], TE[p] = sub(dd, np.arange(k)), sub(dd, np.arange(k, dd.D))
    r = np.maximum(dd.hi.max(1), 0) - np.minimum(dd.lo.min(1), 0); RMED[p] = float(np.median(r)); HALF[p] = max(int(round(RMED[p] / 2)), 1)
WRS = (0.474, 0.50, 0.52); _dr = {}
def drift_of(p, wr):
    if (p, wr) not in _dr: _dr[(p, wr)] = calib_drift(TR[p], wr, HALF[p])
    return _dr[(p, wr)]
RULES = {"MES": Rules(scaling=False), "MGC": Rules(scaling=False)}
_cache = {}
def provider(p, dd, sl, tp, drift, slip, slipp):
    key = (p, id(dd), int(sl), int(tp), round(drift, 6), slip)
    if key not in _cache:
        d = BarDays(dd, SPEC[p]["tv"], SPEC[p]["fee"], int(sl), int(tp), slip=slip, slip_p=slipp, exit_slip=0.0, cush_max=6000.0, step=20.0, drift=drift, stop_frac=0.5); d._p0 = d.pool.copy(); _cache[key] = d
    d = _cache[key]; d.pool = d._p0.copy(); return d
def pay_fn(kind):
    if kind == "max": return "max"
    if kind == "min": return "min"
    if kind == "mitad": return lambda st, g: np.minimum(g, np.maximum(125.0, 0.25 * st.b))                  # pide la mitad de lo permitido (25 % del saldo)
    if kind == "espera2000": return lambda st, g: np.where(st.b >= 2000.0, g, 0.0)                         # no cobra hasta tener saldo ≥ $2,000
    raise ValueError(kind)
def run(p, dd, plan, drift, n, seed, pool=None, slip=(1.0,), slipp=None, pay="max", rules=None):
    sl, tp, nc = plan
    days = provider(p, dd, sl, tp, drift, slip, slipp)
    if pool is not None: days.pool = pool
    fnc = lambda st: np.minimum(nc, plan_cap(st.b, p)).astype(int)
    r = simulate_life(days, rules or RULES[p], Policy("x", fnc, pay_fn(pay), int(sl), int(tp)), n=n, seed=seed, record_k=14)
    pd_, pn = r["pay_day"], r["pay_net"]
    cum = lambda T: float(np.where((pd_ >= 0) & (pd_ < T), pn, 0.0).sum(1).mean())
    fp = r["first_pay_day"]; dead = ~r["alive"]
    return dict(life_paid=float(r["paid"].mean()), cum10=cum(10), cum20=cum(20), cum30=cum(30), cum60=cum(60), p1=float((r["npay"] >= 1).mean()),
                f10=float(((fp >= 0) & (fp < 10)).mean()), f20=float(((fp >= 0) & (fp < 20)).mean()), f30=float(((fp >= 0) & (fp < 30)).mean()),
                med=float(np.median(fp[fp >= 0]) + 1) if (fp >= 0).any() else float("nan"), d3=float(((r["life"] <= 3) & dead).mean()), dead_np=float(((r["npay"] == 0) & dead).mean()), life=float(r["life"].mean()),
                nc=nc, sl=sl, tp=tp)
def blocks(npool, Bn, rng):
    nb = math.ceil(npool / 5); st = rng.integers(0, npool - 4, size=(Bn, nb)); return (st[:, :, None] + np.arange(5)).reshape(Bn, -1)[:, :npool]
GRID = {"MES": [(sl, max(int(round(rho * sl)), 1), nc) for sl in (40, 60, 80, 100, 130, 170) for rho in (0.5, 1.0, 2.0) for nc in (4, 8, 12, 20)],
        "MGC": [(sl, max(int(round(rho * sl)), 1), nc) for sl in (182, 273, 364, 546, 728) for rho in (0.5, 1.0, 2.0) for nc in (1, 2, 3, 4, 6, 8)]}
BASE = {"MES": None, "MGC": (364, 364, 3)}
P("# resultados_ACCION — XFA 50K ya fondeada: MES vs MGC (Cerebro 2) con el motor exacto, objetivo de corto plazo\n")
P("**Fuentes y estado.** MODELADO sobre días reales de 5 min (MES 496 días 9:35→14:25 CT; MGC 443 días sin la ventana de oro, 7:15→14:25 CT). Motor `xfa_engine` con las reglas verificadas de la Parte D (`RULEBOOK_XFA.md`): MLL $2,000 trailing que se fija en $0 al llegar a +$2,000 y tras el 1.er pago; día ganador ≥ $150 netos, 5 días; pago = 50 % del saldo (tope $2,000, mínimo $125); desde el 2.º pago hace falta ganancia desde el pago anterior; **escalado XFA 50K: MES 20 / 30 / 50 micros (saldo < $1,500 / < $2,000 / ≥ $2,000); MGC 12 / 18 / 31**. Comisión por contrato round-turn: MES $1.22, MGC $1.92. Plan elegido en el 60 % más viejo, reportado en el 40 % reciente. Etiqueta de WR (deriva calibrada en el bracket nominal ½ rango): 47.4 / 50 / 52 %. Slippage en la selección: 1 tick; en el reporte, la distribución empírica de 8 obs. de MES (8.ª inferida = 0, NO VERIFICADA).\n")
best = {}
for p in ("MES", "MGC"):
    sc = []
    for plan in GRID[p]:
        r = run(p, TR[p], plan, 0.0, N_SEL, 21); sc.append((r["cum30"] + 0.25 * r["life_paid"], plan, r))
    sc.sort(key=lambda x: -x[0]); best[p] = [s[1] for s in sc[:3]]
    print("  selección", p, round(time.time() - t0), "s", flush=True)
cand = {"MGC 3×364 (Cerebro 2 hoy)": ("MGC", BASE["MGC"]), "MGC mejor del grid": ("MGC", best["MGC"][0]), "MES mejor del grid": ("MES", best["MES"][0]), "MES 2.º": ("MES", best["MES"][1]), "MES 3.º": ("MES", best["MES"][2])}
rng = np.random.default_rng(20261028); pools = {p: blocks(TE[p].D, B, rng) for p in ("MES", "MGC")}
res = {}
for nm, (p, plan) in cand.items():
    for wr in WRS:
        d = drift_of(p, wr); pt = run(p, TE[p], plan, d, N_REP, 22, slip=EMP8, slipp=EMP8_P)
        bs = [run(p, TE[p], plan, d, 4000, 22, pool=pools[p][b], slip=EMP8, slipp=EMP8_P) for b in range(B)]
        res[(nm, wr)] = (pt, bs)
    print("  reporte", nm, round(time.time() - t0), "s", flush=True)
def ci(bs, k): v = np.array([x[k] for x in bs]); return np.percentile(v, 2.5), np.percentile(v, 97.5)
P("## 1. Tabla principal (tramo reciente; EMP8; IC95 = bloques de 5 días)\n")
for wr in WRS:
    P(f"\n### WR {wr * 100:.1f} %\n")
    P("| plan | cobrado a 10 d | a 20 d | **a 30 d** [IC95] | a 60 d | vida entera [IC95] | P(1.er pago ≤ 10 d / 20 d / 30 d) | mediana días al 1.er pago | P(muerte ≤ 3 d) | P(muerte sin cobrar nada) | tamaño / tope |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for nm, (p, plan) in cand.items():
        pt, bs = res[(nm, wr)]; c30 = ci(bs, "cum30"); cl = ci(bs, "life_paid")
        P(f"| {nm}: {p} SL {plan[0]} / TP {plan[1]} / {plan[2]} micros | ${pt['cum10']:,.0f} | ${pt['cum20']:,.0f} | **${pt['cum30']:,.0f}** [{c30[0]:,.0f}, {c30[1]:,.0f}] | ${pt['cum60']:,.0f} | ${pt['life_paid']:,.0f} [{cl[0]:,.0f}, {cl[1]:,.0f}] | {pt['f10'] * 100:.0f} / {pt['f20'] * 100:.0f} / {pt['f30'] * 100:.0f} % | {pt['med']:.0f} | {pt['d3'] * 100:.0f} % | {pt['dead_np'] * 100:.0f} % | {plan[2]} de {'20' if p == 'MES' else '12'} (tope inicial) |")
# diferencias pareadas MES-mejor vs MGC 3x364
P("\n## 2. Diferencia pareada (misma remuestra de días del tramo reciente no es posible entre productos distintos: se comparan intervalos independientes)\n")
for wr in WRS:
    a = res[("MES mejor del grid", wr)]; b = res[("MGC 3×364 (Cerebro 2 hoy)", wr)]
    da = np.array([x["cum30"] for x in a[1]]); db = np.array([x["cum30"] for x in b[1]])
    P(f"- WR {wr * 100:.1f} %: cobrado a 30 días MES − MGC 3×364 = **${a[0]['cum30'] - b[0]['cum30']:+,.0f}** (IC95 de la diferencia de medias por remuestras independientes: [{np.percentile(da[:, None] - db[None, :], 2.5):+,.0f}, {np.percentile(da[:, None] - db[None, :], 97.5):+,.0f}]).")
# políticas de cobro para el mejor MES y MGC 3x364 (WR 50)
P("\n## 3. Política de cobro (WR 50 %, tramo reciente): ¿cobrar todo lo permitido o menos?\n")
P("| plan | política | cobrado a 30 d | vida entera | P(1.er pago ≤ 20 d) | vida (días) |\n|---|---|---|---|---|---|")
for nm in ("MGC 3×364 (Cerebro 2 hoy)", "MES mejor del grid"):
    p, plan = cand[nm]
    for pol in ("max", "mitad", "min", "espera2000"):
        r = run(p, TE[p], plan, drift_of(p, 0.50), N_REP, 22, slip=EMP8, slipp=EMP8_P, pay=pol)
        P(f"| {nm} | {pol} | ${r['cum30']:,.0f} | ${r['life_paid']:,.0f} | {r['f20'] * 100:.0f} % | {r['life']:.1f} |")
open(os.path.join(HERE, "resultados_ACCION.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
