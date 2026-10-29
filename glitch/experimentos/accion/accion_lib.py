"""[Biblioteca compartida] ACCIÓN (28-oct-2026): la XFA 50K ya está fondeada. Motor exacto de la XFA (xfa_engine, reglas verificadas de la Parte D) con MES vs MGC (Cerebro 2), objetivo de CORTO PLAZO:
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
QUICK = "--quick" in sys.argv
N_SEL = 6000 if QUICK else 12000; N_REP = 12000 if QUICK else 40000; B = 8 if QUICK else 20
t0 = time.time()
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
