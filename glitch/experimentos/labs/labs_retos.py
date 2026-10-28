"""Topstep Labs (28-oct-2026): ¿vale la pena perseguir cada reto con la lógica de geometría convexa (pagas una cuota fija, el upside es tuyo)? -> resultados_LABS.md
    cd glitch/experimentos/labs; PYTHONPATH=../.. python3 labs_retos.py [--quick]
MODELADO sobre días reales de 5 min (2 años, ventana CT): se elige el plan en el 60 % cronológico más viejo y se REPORTA en el 40 % más reciente (sin reusar los días de selección).
Reglas de cada reto: pegadas por Eric (28-oct) + Topstep Labs Help (extracción automática, 28-oct); lo que la página no dice queda marcado SUPUESTO/DESCONOCIDO. Semillas fijas."""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from labs_motor import BarDays, DayData, Policy, Rules, calib_drift, chal_life, simulate_life
from daydata import load_days
from worlds import mgc_days

ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--emp8", action="store_true", help="slippage de entrada = distribución empírica de 8 obs. en vez de 1 tick fijo"); A = ap.parse_args()
SLIP, SLIPP = ((-1.0, 0.0, 1.0, 3.0), (1 / 8, 3 / 8, 2 / 8, 2 / 8)) if A.emp8 else ((1.0,), None)
OUTNAME = "resultados_LABS_emp8.md" if A.emp8 else "resultados_LABS.md"
NC_ = 6000 if A.quick else 20000; NX_ = 6000 if A.quick else 20000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
DC = os.path.join(HERE, "..", "..", "data_cache")
# producto: (parquet, tick, $/tick, comisión RT, última barra CT en minutos, referencia CT en minutos)
PRODS = {"MES": ("mes_5min_2y.parquet", 0.25, 1.25, 1.22, 865, 575), "MNQ": ("mnq_5min_2y.parquet", 0.25, 0.50, 1.22, 865, 575),
         "MCL": ("mcl_5min_2y.parquet", 0.01, 1.00, 1.72, 865, 575), "MGC": (None, 0.10, 1.00, 1.92, 865, 435)}
RESTRICTED = {"MGC", "MCL"}                                  # tope de 30 micros por el ajuste de riesgo de Topstep (13613539), válido en Combine/Express
dd_all = {}
for p, (fn, tick, tv, fee, last, ref) in PRODS.items():
    dd_all[p] = mgc_days(True) if p == "MGC" else load_days(os.path.join(DC, fn), ref, last, tick, fill_gaps=True, dominant_contract=True)
def split(dd, frac=0.6):
    k = int(dd.D * frac); sl_ = lambda a, lo, hi: a[lo:hi]
    mk = lambda lo, hi: DayData(dd.dates[lo:hi], dd.ref[lo:hi], dd.op[lo:hi], dd.hi[lo:hi], dd.lo[lo:hi], dd.cl[lo:hi], [])
    return mk(0, k), mk(k, dd.D)
TR, TE, RMED, HALF = {}, {}, {}, {}
for p, dd in dd_all.items():
    TR[p], TE[p] = split(dd)
    r = np.maximum(dd.hi.max(1), 0) - np.minimum(dd.lo.min(1), 0); RMED[p] = float(np.median(r)); HALF[p] = max(int(round(RMED[p] / 2)), 1)
WRS = (0.474, 0.50, 0.52)
_drift = {}
def drift_of(p, wr):
    if (p, wr) not in _drift: _drift[(p, wr)] = calib_drift(TR[p], wr, HALF[p])
    return _drift[(p, wr)]

# ───────── retos ─────────
LOTS_250K = ((1500.0, 30), (3000.0, 50), (4500.0, 100), (8000.0, 150), (1e18, 250))     # micros por saldo; SUPUESTO (la página solo da 3 lotes < $1,500 y 25 lotes > $8,000)
RETOS = {
    "$25K Static (#001)": dict(fee=75.0, act=0.0, target=2000.0, mll=1000.0, trailing=False, dll=500.0, consist=0.55, cap_c=20, cap_x=20, min_days=2,
                               xfa=dict(mll=1000.0, dll=500.0, cap=4000.0, win_usd=150.0, win_days=5, lock=-1000.0), kind="combine", scal=None),
    "$50K Static (#006)": dict(fee=149.0, act=0.0, target=4000.0, mll=2000.0, trailing=False, dll=1000.0, consist=0.55, cap_c=40, cap_x=20, min_days=2,
                               xfa=dict(mll=2000.0, dll=1000.0, cap=8000.0, win_usd=150.0, win_days=5, lock=-2000.0), kind="combine", scal=None),
    "$250K Freedom (#002)": dict(fee=499.0, act=0.0, target=15000.0, mll=10000.0, trailing=True, dll=5000.0, consist=0.55, cap_c=250, cap_x=250, min_days=2,
                                 xfa=dict(mll=10000.0, dll=None, cap=25000.0, win_usd=1000.0, win_days=5, lock=-10000.0), kind="combine", scal=LOTS_250K),
    "$1.5K Powered Up (#007)": dict(fee=99.0, act=0.0, target=1500.0, mll=500.0, trailing=False, dll=None, consist=None, cap_c=20, cap_x=0, min_days=1, kind="challenge", payout=1500.0, scal=None, cap_r={"MGC": 12, "MCL": 12}),
    # ── referencia: el camino actual (Combine estándar de $49 por intento + activación de $149), mismo método ──
    "REF: 50K estándar ($49/intento + $149 activación)": dict(fee=49.0, act=149.0, target=3000.0, mll=2000.0, trailing=True, dll=None, consist=0.55, cap_c=50, cap_x=30, min_days=2,
                               xfa=dict(mll=2000.0, dll=None, cap=2000.0, win_usd=150.0, win_days=5, lock=0.0), kind="combine", scal=None),
    "REF-prod: 50K estándar con el plan de producción (MES nc 40 TP 32 / SL 100 + MGC 3×364)": dict(fee=49.0, act=149.0, target=3000.0, mll=2000.0, trailing=True, dll=None, consist=0.55, cap_c=50, cap_x=30, min_days=2,
                               xfa=dict(mll=2000.0, dll=None, cap=2000.0, win_usd=150.0, win_days=5, lock=0.0), kind="combine", scal=None, fixed=dict(c=("MES", 100, 32, 40), x=("MGC", 364, 364, 3))),
    # ── sensibilidad de los supuestos de la XFA del $250K (la página no los fija) ──
    "(sens) $250K: XFA con DLL de $5,000": dict(fee=499.0, act=0.0, target=15000.0, mll=10000.0, trailing=True, dll=5000.0, consist=0.55, cap_c=250, cap_x=250, min_days=2,
                                 xfa=dict(mll=10000.0, dll=5000.0, cap=25000.0, win_usd=1000.0, win_days=5, lock=-10000.0), kind="combine", scal=LOTS_250K),
    "(sens) $250K: XFA siempre 30 micros (3 lotes)": dict(fee=499.0, act=0.0, target=15000.0, mll=10000.0, trailing=True, dll=5000.0, consist=0.55, cap_c=250, cap_x=250, min_days=2,
                                 xfa=dict(mll=10000.0, dll=None, cap=25000.0, win_usd=1000.0, win_days=5, lock=-10000.0), kind="combine", scal=((1e18, 30),) * 5),
    "(sens) $250K: pago = 25 % del saldo (en vez de 50 %)": dict(fee=499.0, act=0.0, target=15000.0, mll=10000.0, trailing=True, dll=5000.0, consist=0.55, cap_c=250, cap_x=250, min_days=2,
                                 xfa=dict(mll=10000.0, dll=None, cap=25000.0, win_usd=1000.0, win_days=5, lock=-10000.0, pct=0.25), kind="combine", scal=LOTS_250K),
    # ── no pedidos: otros retos de Labs con la misma maquinaria (reglas de la página de Labs, extracción automática) ──
    "(extra) $1.5K original ($39, 2 micros)": dict(fee=39.0, act=0.0, target=1500.0, mll=500.0, trailing=False, dll=None, consist=None, cap_c=2, cap_x=0, min_days=1, kind="challenge", payout=1500.0, scal=None, cap_r={"MGC": 1, "MCL": 1}),
    "(extra) $3K (#003, $49, 10 micros)": dict(fee=49.0, act=0.0, target=3000.0, mll=1000.0, trailing=False, dll=None, consist=None, cap_c=10, cap_x=0, min_days=1, kind="challenge", payout=3000.0, scal=None, cap_r={"MGC": 6, "MCL": 6}),
    "(extra) $6K (#005, $149, 10 micros)": dict(fee=149.0, act=0.0, target=6000.0, mll=2000.0, trailing=False, dll=None, consist=None, cap_c=10, cap_x=0, min_days=1, kind="challenge", payout=6000.0, scal=None, cap_r={"MGC": 6, "MCL": 6}),
    "(extra) $3K Undead (#008, $199, 50 micros)": dict(fee=199.0, act=0.0, target=3000.0, mll=1000.0, trailing=False, dll=None, consist=None, cap_c=50, cap_x=0, min_days=1, kind="challenge", payout=3000.0, scal=None, cap_r={"MGC": 31, "MCL": 31}),
    "(extra) $3K Slasher (#009, $65, 20 micros)": dict(fee=65.0, act=0.0, target=3000.0, mll=500.0, trailing=False, dll=None, consist=None, cap_c=20, cap_x=0, min_days=1, kind="challenge", payout=3000.0, scal=None, cap_r={"MGC": 12, "MCL": 12}),
}
def cap_for(prod, cap, R=None):
    if R is not None and R.get("cap_r") and prod in R["cap_r"]: return min(cap, R["cap_r"][prod])
    return min(cap, 30) if prod in RESTRICTED else cap
_CACHE = {}
def make_days(prod, dd, sl, tp, mll, target, drift, fee, tv, big):
    key = ("c", prod, id(dd), int(sl), int(tp), round(drift, 6), mll, target)
    if key in _CACHE:
        d = _CACHE[key]; d.pool = d._pool0.copy(); return d
    d = _make_days(prod, dd, sl, tp, mll, target, drift, fee, tv, big); d._pool0 = d.pool.copy(); _CACHE[key] = d; return d
def _make_days(prod, dd, sl, tp, mll, target, drift, fee, tv, big):
    cm = float(big * mll + target); step = max(cm / 400.0, 2.0)
    return BarDays(dd, tv, fee, int(sl), int(tp), slip=SLIP, slip_p=SLIPP, exit_slip=0.0, cush_max=cm, step=step, drift=drift, stop_frac=0.5)
def nc_size(f, mll, sl, tv, fee, cap):
    return int(max(1, min(cap, np.floor(f * mll / (sl * tv + fee)))))

def eval_combine(prod, dd, plan, R, drift, n, seed, pool=None):
    fn, tick, tv, fee, last, ref = PRODS[prod]
    if "abs" in plan: sl, tp, nc = plan["abs"]
    else:
        sl = max(int(round(plan["k"] * RMED[prod])), 1); tp = max(int(round(plan["rho"] * sl)), 1)
        cap = cap_for(prod, R["cap_c"], R); nc = nc_size(plan["f"], R["mll"], sl, tv, fee, cap)
    days = make_days(prod, dd, sl, tp, R["mll"], R["target"], drift, fee, tv, 1.5)
    if pool is not None: days.pool = pool
    r = chal_life(days, n, seed, R["target"], R["mll"], tv, fee, sl, lambda b, f_, nd: np.full(b.shape, nc), trailing=R["trailing"], dll=R["dll"], consist=R["consist"], min_days=R["min_days"])
    return dict(p=float(r["passed"].mean()), days=float(r["days"][r["passed"]].mean()) if r["passed"].any() else float("nan"), liq=float(r["fail_liq"].mean()), sl=sl, tp=tp, nc=nc)

def eval_xfa(prod, dd, plan, R, drift, n, seed, pool=None):
    X = R["xfa"]; fn, tick, tv, fee, last, ref = PRODS[prod]
    cap = cap_for(prod, R["cap_x"], R)
    if "abs" in plan: sl, tp, base = plan["abs"]
    else:
        sl = max(int(round(plan["k"] * RMED[prod])), 1); tp = max(int(round(plan["rho"] * sl)), 1); base = nc_size(plan["f"], X["mll"], sl, tv, fee, cap)
    key = ("x", prod, id(dd), sl, tp, round(drift, 6), X["mll"])
    if key not in _CACHE:
        d = BarDays(dd, tv, fee, sl, tp, slip=SLIP, slip_p=SLIPP, exit_slip=0.0, cush_max=float(8 * X["mll"]), step=max(8 * X["mll"] / 400.0, 2.0), drift=drift, stop_frac=0.5); d._pool0 = d.pool.copy(); _CACHE[key] = d
    days = _CACHE[key]; days.pool = days._pool0.copy()
    if pool is not None: days.pool = pool
    if R["scal"]:
        sc = R["scal"]; capf = lambda b: np.select([b < sc[0][0], b < sc[1][0], b < sc[2][0], b < sc[3][0]], [sc[0][1], sc[1][1], sc[2][1], sc[3][1]], default=sc[4][1])
        fnc = lambda st: np.minimum(base, np.minimum(cap, capf(st.b))).astype(int)
    else:
        fnc = lambda st: np.full(st.b.shape, base)
    rules = Rules(mll=X["mll"], lock=X.get("lock", -X["mll"]), win_usd=X["win_usd"], win_days=X["win_days"], pct=X.get("pct", 0.5), cap=X["cap"], minpay=125.0, split=0.9, first100=0.0, profit_rule=True, path="std",
                  dll=X["dll"], scaling=False, idle_close_days=30)
    r = simulate_life(days, rules, Policy("x", fnc, "max", sl, tp), n=n, seed=seed)
    return dict(paid=float(r["paid"].mean()), p1=float((r["npay"] >= 1).mean()), life=float(r["life"].mean()), sl=sl, tp=tp, nc=base)

CPLANS = [dict(k=k, rho=rho, f=f) for k in (0.25, 0.5, 1.0) for rho in (0.33, 0.5, 1, 2) for f in (0.5, 1.0, 2.0, 3.0)]
XPLANS = [dict(k=k, rho=rho, f=f) for k in (0.5, 1.0) for rho in (0.5, 1, 2) for f in (0.25, 0.5, 1.0)]
P("# resultados_LABS — ¿vale la pena perseguir los retos de Topstep Labs con geometría convexa?\n")
P("Miércoles 28-oct-2026 · MODELADO RÁPIDO (no auditado). Cada reto se modela por separado, con su propio producto, bracket y tamaño. Plan elegido en el 60 % cronológico más viejo de los días reales (2 años, MES/MNQ/MGC/MCL) y **reportado en el 40 % más reciente** (≈ 200 días). Reglas: texto pegado por Eric y página de Topstep Labs (extracción automática); lo que la página no dice, SUPUESTO/DESCONOCIDO. Slippage de entrada " + ("= distribución empírica de 8 observaciones de MES {−1, 0, +1, +3}" if A.emp8 else "1 tick fijo (≈ la media de 8 observaciones de MES, 0.9)") + " (la 8.ª observación inferida = 0, NO VERIFICADA); comisión por producto de la página de Topstep; stop llenado a 0.5.\n")
res = {}
pl = lambda q: 'plan fijo de producción' if 'abs' in q else f"k = {q['k']}, ρ = {q['rho']}, f = {q['f']}"
for rn, R in RETOS.items():
    ts = time.time(); best_c = {}; best_x = {}
    if R.get('fixed'):
        fc, fx = R['fixed']['c'], R['fixed']['x']; pr_c = fc[0]; best_c[pr_c] = dict(abs=fc[1:]); pr_x = fx[0]; best_x[pr_x] = dict(abs=fx[1:])
        rows = {}
        for wr in WRS:
            c = eval_combine(pr_c, TE[pr_c], best_c[pr_c], R, drift_of(pr_c, wr), NC_ * 2, 12); x = eval_xfa(pr_x, TE[pr_x], best_x[pr_x], R, drift_of(pr_x, wr), NX_ * 2, 22)
            ev = c['p'] * (x['paid'] - R['act']) - R['fee']; api = 14.3 * (c['days'] if c['days'] == c['days'] else 0) / 21.0 + 14.3 * c['p'] * x['life'] / 21.0
            rows[wr] = dict(c=c, x=x, ev=ev, ev_api=ev - api, roi=ev / R['fee'], cost_per_xfa=R['fee'] / max(c['p'], 1e-9))
        res[rn] = dict(R=R, pr_c=pr_c, best_c=best_c[pr_c], pr_x=pr_x, best_x=best_x[pr_x], rows=rows); print('  ', rn, 'fijo', flush=True); continue
    # etapa A: Combine/Challenge (P(pasar) a deriva 0 en el tramo de entrenamiento)
    for prod in PRODS:
        sc = [(eval_combine(prod, TR[prod], pl, R, 0.0, NC_, 11)["p"], i) for i, pl in enumerate(CPLANS)]
        sc.sort(reverse=True); best_c[prod] = CPLANS[sc[0][1]]
    pr_c = max(PRODS, key=lambda q: eval_combine(q, TR[q], best_c[q], R, 0.0, NC_, 11)["p"])
    if R["kind"] == "combine":
        for prod in PRODS:
            sx = [(eval_xfa(prod, TR[prod], pl, R, 0.0, NX_, 21)["paid"], i) for i, pl in enumerate(XPLANS)]
            sx.sort(reverse=True); best_x[prod] = XPLANS[sx[0][1]]
        pr_x = max(PRODS, key=lambda q: eval_xfa(q, TR[q], best_x[q], R, 0.0, NX_, 21)["paid"])
    # reporte en el tramo reciente, 3 escenarios de WR
    rows = {}
    for wr in WRS:
        c = eval_combine(pr_c, TE[pr_c], best_c[pr_c], R, drift_of(pr_c, wr), NC_ * 2, 12)
        if R["kind"] == "combine":
            x = eval_xfa(pr_x, TE[pr_x], best_x[pr_x], R, drift_of(pr_x, wr), NX_ * 2, 22)
            ev = c["p"] * (x["paid"] - R["act"]) - R["fee"]
            api = 14.3 * (c["days"] if c["days"] == c["days"] else 0) / 21.0 + 14.3 * c["p"] * x["life"] / 21.0
            rows[wr] = dict(c=c, x=x, ev=ev, ev_api=ev - api, roi=ev / R["fee"], cost_per_xfa=R["fee"] / max(c["p"], 1e-9))
        else:
            pw = c["p"] ** 2; ev = pw * R["payout"] - R["fee"]
            rows[wr] = dict(c=c, p_win=pw, ev=ev, ev_api=ev, roi=ev / R["fee"])
    res[rn] = dict(R=R, pr_c=pr_c, best_c=best_c[pr_c], pr_x=(pr_x if R["kind"] == "combine" else None), best_x=(best_x[pr_x] if R["kind"] == "combine" else None), rows=rows)
    print("  ", rn, round(time.time() - ts), "s", flush=True)

# ── IC por remuestreo de bloques de 5 días del tramo reciente (16 remuestras) para los retos pedidos y la referencia ──
BOOT = {}
rng = np.random.default_rng(20261028); B = 8 if A.quick else 16
def blocks(npool, Bn):
    nb = int(np.ceil(npool / 5)); st = rng.integers(0, npool - 4, size=(Bn, nb)); return (st[:, :, None] + np.arange(5)).reshape(Bn, -1)[:, :npool]
for rn, v in res.items():
    if rn.startswith(("(extra)", "(sens)")): continue
    R = v["R"]; BOOT[rn] = {}
    pc = blocks(TE[v["pr_c"]].D, B); px = blocks(TE[v["pr_x"]].D, B) if R["kind"] == "combine" else None
    for wr in WRS:
        evs = []
        for b in range(B):
            c = eval_combine(v["pr_c"], TE[v["pr_c"]], v["best_c"], R, drift_of(v["pr_c"], wr), 5000, 12, pool=pc[b])
            if R["kind"] == "combine":
                x = eval_xfa(v["pr_x"], TE[v["pr_x"]], v["best_x"], R, drift_of(v["pr_x"], wr), 5000, 22, pool=px[b]); evs.append(c["p"] * (x["paid"] - R["act"]) - R["fee"])
            else:
                evs.append(c["p"] ** 2 * R["payout"] - R["fee"])
        BOOT[rn][wr] = (float(np.percentile(evs, 2.5)), float(np.percentile(evs, 97.5)), float(np.mean(np.array(evs) > 0)))
    print("  boot", rn, flush=True)
P("## Resumen\n")
P("| reto | cuota | P(pasar) / P(cobrar) a WR 47.4 / 50 / 52 % | EV por compra a WR 47.4 / 50 / 52 % | IC95 del EV a WR 50 % (días remuestreados) | P(EV > 0) a 47.4 / 50 / 52 % | ROI sobre la cuota (WR 50 %) | cota teórica sin ventaja |\n|---|---|---|---|---|---|---|---|")
for rn, v in res.items():
    R = v["R"]; rw = v["rows"]
    if R["kind"] == "combine":
        pp = " / ".join(f"{rw[w]['c']['p'] * 100:.0f} %" for w in WRS); ev = " / ".join(f"${rw[w]['ev']:+,.0f}" for w in WRS)
        bound = R["mll"] / (R["target"] + R["mll"])
        bt = BOOT.get(rn); ic = f"[{bt[0.50][0]:+,.0f}, {bt[0.50][1]:+,.0f}]" if bt else "—"; pg = " / ".join(f"{bt[w][2] * 100:.0f} %" for w in WRS) if bt else "—"
        P(f"| **{rn}** | ${R['fee']:,.0f} | {pp} | {ev} | {ic} | {pg} | {rw[0.50]['roi'] * 100:+.0f} % | P(pasar) ≤ {bound * 100:.0f} % |")
    else:
        pp = " / ".join(f"{rw[w]['p_win'] * 100:.1f} %" for w in WRS); ev = " / ".join(f"${rw[w]['ev']:+,.0f}" for w in WRS)
        bound = (R["mll"] / (R["target"] + R["mll"])) ** 2
        bt = BOOT.get(rn); ic = f"[{bt[0.50][0]:+,.0f}, {bt[0.50][1]:+,.0f}]" if bt else "—"; pg = " / ".join(f"{bt[w][2] * 100:.0f} %" for w in WRS) if bt else "—"
        P(f"| **{rn}** | ${R['fee']:,.0f} | {pp} | {ev} | {ic} | {pg} | {rw[0.50]['roi'] * 100:+.0f} % | P(cobrar) ≤ {bound * 100:.2f} % (dos rondas) |")
P("\n(La cota sin ventaja sale del teorema de parada opcional: con deriva cero ningún plan puede pasar con más de L/(T+L); aquí se cumple en los resultados.)\n")
for rn, v in res.items():
    R = v["R"]; rw = v["rows"]
    P(f"## {rn}\n")
    P(f"**Reglas usadas.** cuota ${R['fee']:,.0f} única (sin resets); meta ${R['target']:,.0f}; MLL ${R['mll']:,.0f} {'de cierre (trailing EOD)' if R['trailing'] else 'estático'}; DLL " + (f"${R['dll']:,.0f}" if R['dll'] else "ninguno") + f"; consistencia " + (f"{R['consist'] * 100:.0f} %" if R['consist'] else "ninguna") + f"; tope {R['cap_c']} micros; vence a los 90 días (≈ 63 hábiles).")
    c = rw[0.50]["c"]
    P(f"**Plan elegido ({'Combine' if R['kind'] == 'combine' else 'cada ronda'}):** {v['pr_c']}, SL {c['sl']} ticks, TP {c['tp']} ticks, {c['nc']} contratos ({pl(v['best_c'])}). A WR 50 %: P(pasar) {c['p'] * 100:.1f} %, días hasta pasar {c['days']:.1f}, liquidada {c['liq'] * 100:.0f} %.")
    if R["kind"] == "combine":
        X = R["xfa"]; x = rw[0.50]["x"]
        P(f"**XFA (supuestos donde la página calla):** MLL ${X['mll']:,.0f} estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL " + (f"${X['dll']:,.0f}" if X['dll'] else "no indicado (se modela sin DLL)") + f", camino Standard: 5 días ≥ ${X['win_usd']:,.0f} netos, tope por pago ${X['cap']:,.0f}, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)" + ("; escalado por saldo 30/50/100/150/250 micros (SUPUESTO)" if R["scal"] else f"; tamaño ≤ {R['cap_x']} micros (la XFA 50K trae un escalado «2/3/4» sin explicar: se asume el primer escalón)." if rn.startswith("$50K") else "") )
        P(f"**Plan XFA elegido:** {v['pr_x']}, SL {x['sl']}, TP {x['tp']}, {x['nc']} contratos base ({pl(v['best_x'])}). A WR 50 %: cobrado esperado ${x['paid']:,.0f}, P(≥ 1 pago) {x['p1'] * 100:.0f} %, vida {x['life']:.1f} días.\n")
        P("| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |\n|---|---|---|---|---|---|")
        for w in WRS:
            r = rw[w]; P(f"| {w * 100:.1f} % | {r['c']['p'] * 100:.1f} % | ${r['x']['paid']:,.0f} | **${r['ev']:+,.0f}** | ${r['ev_api']:+,.0f} | ${r['cost_per_xfa']:,.0f} |")
    else:
        P(f"**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar ${R['target']:,.0f} en la ronda del reto y **otra vez** ${R['target']:,.0f} en la ronda de pago, ambas con MLL estático de ${R['mll']:,.0f}; el pago fijo de ${R['payout']:,.0f} se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².\n")
        P("| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |\n|---|---|---|---|")
        for w in WRS:
            r = rw[w]; P(f"| {w * 100:.1f} % | {r['c']['p'] * 100:.1f} % | {r['p_win'] * 100:.2f} % | **${r['ev']:+,.0f}** |")
    P("")
open(os.path.join(HERE, OUTNAME), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
