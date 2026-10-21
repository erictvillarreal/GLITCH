"""§4 del encargo E: valor de cada punto de WR (47-56 %). Motor de la Parte D (cadena Combine -> XFA -> Combine).
La ventaja se fija con una deriva A FAVOR del lado elegido, calibrada para que WR = TP/(TP+SL) entre decididos del bracket de MGC (3 micros, SL=TP=364, W2 limpio sin oro) sea el objetivo;
la MISMA deriva estandarizada (mu/sigma de la sesion) se aplica a MES en el Combine (una regla que acertara en MGC acertaria igual en MES). -> resultados_E_valor.md
    GLITCH_MGC_PARQUET=... python value_wr.py [--quick]"""
import argparse, math, os, sys, time
import numpy as np
from scipy.stats import binom
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
NB = 20000 if a.quick else 100000; NC = 5000 if a.quick else 40000
WRS = (0.47, 0.48, 0.49, 0.50, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56)
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
P(f"# resultados_E_valor (§4; {NC} trayectorias, bancos de {NB}; semilla fija; reglas verificadas; sin RTP)\n")
P(f"σ de la sesión (cierre − referencia): MGC {sig_m:.0f} ticks, MES {sig_s:.0f} ticks. Deriva del MGC por WR → deriva de MES con el mismo μ/σ.\n")
def pol_41():
    return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
cands = {"a plan 3×364": (pol_fixed(3, 364, 364), 364), "b 728×3": (pol_fixed(3, 728, 728), 728), "c 4→1 micros (cobro ≥ $1,500)": (pol_41(), 364)}
combs = [("P0", (1.0,), (1.0,), "slip 1"), ("P0", (1.0, 3.0), (0.5, 0.5), "mezcla"), ("P0", (3.0,), (1.0,), "slip 3"), ("P3", (1.0,), (1.0,), "slip 1"), ("P3", (1.0, 3.0), (0.5, 0.5), "mezcla"), ("P3", (3.0,), (1.0,), "slip 3")]
res = {}; paid_tab = {}; drifts = {}
for wr in WRS:
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr)
    z = dm / sig_m; ds = z * sig_s; drifts[wr] = (dm, ds)
    cbs = {(pol, lab): combine_bank(mes, NB, pol, sl, sp, seed=11, drift=ds) for pol, sl, sp, lab in combs}
    for frac in (0.0, 0.5):
        for cname, (pol, sl) in cands.items():
            days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=frac)
            life, pday, pnet = xfa_bank(days, Rules(), pol, NB, seed=21)
            paid_tab[(wr, frac, cname)] = pnet.sum(1).mean()
            for (cpol, clab), (ps, ds_) in cbs.items():
                r = run_chain(ps, ds_, life, pday, pnet, n=NC, seed=5)
                res[(wr, frac, cname, cpol, clab)] = (r["net"].mean(), float(np.std(r["net"]) / math.sqrt(NC)), float(np.mean(r["net"] < 0)))
    print(f"WR {wr:.2f} listo ({time.time() - t0:.0f}s)", flush=True)
P("## A. Deriva equivalente y cobrado por XFA (stop 0.5; ≤ 14 pagos por vida)\n")
P("| WR | deriva MGC (ticks/día) | μ/σ de la sesión | deriva MES (ticks/día) | a plan 3×364 | b 728×3 | c 4→1 micros |\n|---|---|---|---|---|---|---|")
for wr in WRS:
    dm, ds = drifts[wr]
    P(f"| {wr * 100:.0f} % | {dm:+.1f} | {dm / sig_m:+.3f} | {ds:+.1f} | " + " | ".join(f"${paid_tab[(wr, 0.5, c)]:,.0f}" for c in cands) + " |")
P("\n## B. Neto anual por cuenta (media; IC95 ≈ ±2×EE; P(neto<0) entre paréntesis)\n")
for frac in (0.5, 0.0):
    for cname in cands:
        P(f"\n### XFA {cname}, stop {frac}\n")
        P("| WR | " + " | ".join(f"{p} {l}" for p, _, _, l in combs) + " |\n|---|" + "---|" * len(combs))
        for wr in WRS:
            P(f"| {wr * 100:.0f} % | " + " | ".join(f"${res[(wr, frac, cname, p, l)][0]:,.0f} ({res[(wr, frac, cname, p, l)][2] * 100:.0f} %)" for p, _, _, l in combs) + " |")
P("\n## C. WR de equilibrio y valor de cada punto (interpolación lineal; stop 0.5)\n")
P("| XFA | Combine | WR de equilibrio (neto anual = 0) | neto en WR 50 % | valor de 50→51 | de 51→52 | de 52→53 |\n|---|---|---|---|---|---|---|")
for cname in cands:
    for p, _, _, l in combs:
        ys = np.array([res[(wr, 0.5, cname, p, l)][0] for wr in WRS]); xs = np.array(WRS) * 100
        eq = None
        for i in range(len(xs) - 1):
            if ys[i] < 0 <= ys[i + 1]: eq = xs[i] + (0 - ys[i]) / (ys[i + 1] - ys[i]) * (xs[i + 1] - xs[i])
        if ys[0] >= 0: eq = f"< {xs[0]:.0f}"
        i50 = list(WRS).index(0.50) if 0.50 in WRS else 3
        P(f"| {cname} | {p} {l} | {eq if isinstance(eq, str) else ('%.1f %%' % eq if eq is not None else '> 56 %')} | ${ys[3]:,.0f} | ${ys[4] - ys[3]:+,.0f} | ${ys[5] - ys[4]:+,.0f} | ${ys[6] - ys[5]:+,.0f} |")
P("\n## D. Tamaño de muestra para distinguir cada WR de 50 % (potencia 80 %, prueba binomial exacta de una cola al 5 %)\n")
def n_needed(p0, p1, alpha=0.05, power=0.80):
    for n in range(10, 60000):
        if p1 > p0:
            c = binom.ppf(1 - alpha, n, p0) + 1
            if 1 - binom.cdf(c - 1, n, p1) >= power: return n
        else:
            c = binom.ppf(alpha, n, p0) - 1
            if binom.cdf(c, n, p1) >= power: return n
P("| WR verdadero | trades decididos | sesiones MGC (÷ 0.44 decididas) | sesiones si el 72 % son decididas (régimen reciente) |\n|---|---|---|---|")
for wr in (0.47, 0.48, 0.49, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56):
    n = n_needed(0.50, wr); P(f"| {wr * 100:.0f} % | {n:,} | {math.ceil(n / 0.44):,} | {math.ceil(n / 0.72):,} |")
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_E_valor.md"), "w").write("\n".join(out))
