"""Parte F, F1: equilibrio por componente. (a) Combine de MES nc 40 solo (XFA sin ventaja), (b) XFA 3×364 solo, (c) XFA 728×3 solo y 4→1 micros solo (Combine sin ventaja). -> resultados_F1_equilibrio.md
    GLITCH_MGC_PARQUET=... python f1_equilibrio_por_etapa.py"""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
NB, NC = 150000, 40000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
MIX = ("P0", (1.0, 3.0), (0.5, 0.5))
def pol41(): return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
PLANS = {"3×364 (hoy)": (lambda: pol_fixed(3, 364, 364), 364), "728×3": (lambda: pol_fixed(3, 728, 728), 728), "4→1 micros": (pol41, 364)}
def bank(dm, sl, polf): 
    d = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
    return xfa_bank(d, Rules(), polf(), NB, seed=21)
cb0 = combine_bank(mes, NB, *MIX, seed=11, drift=0.0)
b0 = {k: bank(0.0, sl, pf) for k, (pf, sl) in PLANS.items()}
base = {k: run_chain(cb0[0], cb0[1], *v, n=NC, seed=5)["net"].mean() for k, v in b0.items()}
P("# resultados_F1_equilibrio — equilibrio por componente (stop 0.5, Combine hoy P0 con mezcla de slip {1,3}; bancos de %d)\n" % NB)
P("Base sin ventaja (WR = 50 % en ambas etapas): " + " · ".join(f"{k}: ${v:,.0f}/año" for k, v in base.items()) + ".\n")
P("## (a) Ventaja solo en el Combine de MES (nc 40, TP 32, piso $2,000); XFA 3×364 sin ventaja\n")
P("| z = μ/σ (≈ WR en MGC) | P(pasar el Combine) | neto anual | Δ vs base |\n|---|---|---|---|")
rows = []
for z, lab in ((-0.081, "47 %"), (-0.049, "48 %"), (-0.020, "49 %"), (0.0, "50 %"), (0.020, "51 %"), (0.049, "52 %"), (0.081, "53 %")):
    ps, cd = combine_bank(mes, NB, *MIX, seed=11, drift=z * sig_s)
    n = run_chain(ps, cd, *b0["3×364 (hoy)"], n=NC, seed=5)["net"].mean(); rows.append((z, n))
    P(f"| {z:+.3f} ({lab}) | {ps.mean() * 100:.1f} % | ${n:,.0f} | {n - base['3×364 (hoy)']:+,.0f} |"); print(f"  {time.time() - t0:.0f}s", flush=True)
zs = np.array([r[0] for r in rows]); ns = np.array([r[1] for r in rows]); slope = np.polyfit(zs, ns, 1)
P(f"\nPendiente ≈ ${slope[0]:,.0f} por unidad de z (≈ ${slope[0] * 0.02:,.0f} por 1 pp de WR). Neto = 0 requeriría z = {-slope[1] / slope[0]:+.2f}: **fuera de todo rango plausible; el Combine solo, aun con una desventaja del tamaño de 47 % de WR, no vuelve negativo el negocio.**")
P("\n## (b)(c) Ventaja solo en la XFA de MGC (Combine sin ventaja)\n")
P("| WR | cobrado 3×364 | neto 3×364 | cobrado 728×3 | neto 728×3 | cobrado 4→1 | neto 4→1 |\n|---|---|---|---|---|---|---|")
res = {k: [] for k in PLANS}
for wr in (0.45, 0.46, 0.47, 0.48, 0.49, 0.50):
    dm = 0.0 if wr == 0.50 else drift_for_wr(clean, mk, wr); cells = [f"{wr * 100:.0f} %"]
    for k, (pf, sl) in PLANS.items():
        life, pday, pnet = bank(dm, sl, pf); n = run_chain(cb0[0], cb0[1], life, pday, pnet, n=NC, seed=5)["net"].mean()
        res[k].append((wr, n)); cells += [f"${pnet.sum(1).mean():,.0f}", f"${n:,.0f}"]
    P("| " + " | ".join(cells) + " |"); print(f"  wr {wr} {time.time() - t0:.0f}s", flush=True)
def be(rs):
    for (w0, n0), (w1, n1) in zip(rs, rs[1:]):
        if n0 < 0 <= n1: return w0 + (w1 - w0) * (-n0) / (n1 - n0)
    return float("nan")
P("\n**WR de equilibrio (neto anual = 0), ventaja solo en la XFA:** " + " · ".join(f"{k}: {be(v) * 100:.1f} %" for k, v in res.items()) + ".")
open(os.path.join(HERE, "resultados_F1_equilibrio.md"), "w").write("\n".join(out))
