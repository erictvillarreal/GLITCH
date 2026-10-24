"""Parte H (rehecho, 24-oct): H1 con el slippage de entrada del Combine tomado de la distribución EMPÍRICA de 7 observaciones (0, +1, 0, +3, −1, +1, +3 ticks; dato de Eric, NO verificado contra CSV de TopstepX)
y la mezcla {1, 3} como sensibilidad; costos operativos como tres escenarios (A = $240, B = $827, C = pendiente de facturas) y SIN el paso «costos operativos → $0» en la cascada.
Los netos se calculan con ops = 0 y se restan los costos después (el neto es lineal en ellos). -> resultados_H1b.md, cascada_H1b.svg
    GLITCH_MGC_PARQUET=... python h1b_rehacer.py"""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
NB, NC = 100000, 30000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
OBS = (0.0, 1.0, 0.0, 3.0, -1.0, 1.0, 3.0)                                   # dato de Eric (chat): 7 slippage de entrada, ticks, + = adverso
EMP_S = tuple(sorted(set(OBS))); EMP_P = tuple(OBS.count(s) / len(OBS) for s in EMP_S)
CAP1_S, CAP1_P = (-1.0, 0.0, 1.0), (1 / 7, 2 / 7, 4 / 7)                      # hipotético: los +3 se convierten en +1 (tolerancia / anclaje que acota el adverso a 1 tick)
MIX_S, MIX_P = (1.0, 3.0), (0.5, 0.5)
OPS = {"A": 240.0, "B": 827.0}
def pol41(): return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
BASE = dict(pol="P0", slips=EMP_S, probs=EMP_P, cexit=3.0, cfee=1.22, reset=49.0, act=149.0, xsl=364, plan="fixed", xfee=1.92, xslip=0.0, xexit=0.0, xstop=0.5)
_drift = {}; _cb = {}; _xb = {}
def drift_of(wr):
    if wr not in _drift: _drift[wr] = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr)      # calibrada en el bracket NOMINAL 364/364 sin MLL (xfa/worlds.py::drift_for_wr)
    return _drift[wr]
def net0_at(cfg, wr):
    dm = drift_of(wr); ds = dm / sig_m * sig_s
    kc = (cfg["pol"], cfg["slips"], cfg["probs"], cfg["cexit"], cfg["cfee"], round(ds, 6))
    if kc not in _cb: _cb[kc] = combine_bank(mes, NB, cfg["pol"], cfg["slips"], cfg["probs"], seed=11, exit_slip=cfg["cexit"], drift=ds, fee=cfg["cfee"])
    kx = (cfg["xsl"], cfg["plan"], cfg["xfee"], cfg["xslip"], cfg["xexit"], cfg["xstop"], round(dm, 6))
    if kx not in _xb:
        days = BarDays(clean, MGC["tick_usd"], cfg["xfee"], cfg["xsl"], cfg["xsl"], slip=(cfg["xslip"],), exit_slip=cfg["xexit"], mask=mk, cush_max=9000.0, drift=dm, stop_frac=cfg["xstop"])
        _xb[kx] = xfa_bank(days, Rules(), pol_fixed(3, cfg["xsl"], cfg["xsl"]) if cfg["plan"] == "fixed" else pol41(), NB, seed=21)
    ps, cd = _cb[kc]; life, pday, pnet = _xb[kx]
    r = run_chain(ps, cd, life, pday, pnet, n=NC, seed=5, reset_fee=cfg["reset"], act_fee=cfg["act"], ops=0.0)
    return float(r["net"].mean()), float(np.mean(ps))
def eq_for(cfg, ops):
    (n48, p48), (n50, p50) = net0_at(cfg, 0.48), net0_at(cfg, 0.50); slope = (n50 - n48) / 2.0
    return 0.48 + (ops - n48) / slope * 0.01, n50 - ops, slope, p50
def z_of_label(wr):                                   # deriva estandarizada por sesión del bracket nominal 364 (la «etiqueta» de WR)
    return drift_of(wr) / sig_m
P("# resultados_H1b — H1 rehecho: slippage empírico (7 obs.), costos operativos A/B/C y cascada sin «costos → $0»\n")
P("**Fuentes y estado.** Slippage de entrada: 7 valores (0, +1, 0, +3, −1, +1, +3 ticks) **entregados por Eric en el chat**; no los puedo rastrear a un CSV de TopstepX (faltan fecha, lado, tamaño nc 10/40 y hora): **NO VERIFICADOS**. Media +1.00 tick, desvío 1.53, IC95 de la media (t de Student, 6 gl) [−0.41, +2.41]; P(adverso ≥ 2) = 2/7 = 29 % [IC exacto 4 %–71 %]. **N = 7: sin potencia para distinguir una media de 0, 1 o 2 ticks.** Costos operativos: A = $240 ($174 de API por cuenta + ≈ $65 de Railway), B = $827 (A + la mensualidad del Combine de $49 × 12 aparte), C = lo que Eric confirme con facturas; el $714 anterior sale del encargo de la Parte D (`xfa/REPORTE_D.md:24`, `xfa/chain.py:18`), no de una factura. Convención de slippage: M2 (costo; `slip` de `OutcomeTable`), una realización por día del Combine con la distribución indicada.\n")
P(f"Distribución empírica usada: " + ", ".join(f"{s:+.0f}: {p * 100:.0f} %" for s, p in zip(EMP_S, EMP_P)) + ". Sensibilidad: mezcla {1, 3} 50/50 (la de H1 original). Hipótesis de tolerancia (solo en la cascada): los +3 pasan a +1.\n")
res = {}
for lab, (sl, pr) in (("empírica-7", (EMP_S, EMP_P)), ("mezcla {1,3}", (MIX_S, MIX_P))):
    b = dict(BASE); b["slips"], b["probs"] = sl, pr
    for ops_lab, ops in OPS.items():
        e, n50, slope, p50 = eq_for(b, ops); res[(lab, ops_lab)] = (e, n50, slope, p50)
P("## 1. Línea base (Combine P0 nc 40, XFA 3×364, stop 0.5; el resto como en H1)\n")
P("| slippage del Combine | costos operativos | equilibrio de la cadena | neto/año a WR 50 % | valor de 1 pp (48→50 %) | P(pasar) cuenta nueva (WR 50 %) |\n|---|---|---|---|---|---|")
for (lab, ol), (e, n50, slope, p50) in res.items(): P(f"| {lab} | {ol} (${OPS[ol]:,.0f}) | **{e * 100:.2f} %** | ${n50:,.0f} | ${slope:,.0f} | {p50 * 100:.1f} % |")
sl_c = res[("empírica-7", "A")][2]
P(f"\n**Escenario C (facturas de Eric):** el neto es lineal en los costos: cada **$100/año** de costos operativos mueve el equilibrio **+{100 / sl_c:.2f} pp** y el neto −$100 (pendiente local ${sl_c:,.0f}/pp). Equilibrio(C) = equilibrio(A) + (C − 240) / ${sl_c:,.0f} pp; ejemplos: C = $500 → {res[('empírica-7', 'A')][0] * 100 + (500 - 240) / sl_c:.2f} %, C = $1,000 → {res[('empírica-7', 'A')][0] * 100 + (1000 - 240) / sl_c:.2f} %.\n")
def comp(label, group, **kw):
    out_ = {}
    for lab, (sl, pr) in (("empírica-7", (EMP_S, EMP_P)), ("mezcla {1,3}", (MIX_S, MIX_P))):
        b = dict(BASE); b["slips"], b["probs"] = sl, pr; b.update(kw)
        if "slips" in kw and lab == "mezcla {1,3}": continue
        out_[lab] = (eq_for(b, OPS["A"]), eq_for(b, OPS["B"]))
    return out_
rows = []
def add(label, group, **kw):
    r = comp(label, group, **kw); rows.append((group, label, r)); print("  ", label, round(time.time() - t0), "s", flush=True)
add("comisión MES $1.22 → $0 (cota teórica)", "Combine", cfee=0.0); add("comisión MES $1.22 → $2.44", "Combine", cfee=2.44)
for s in (0, 1, 2, 3, 4): add(f"slip de entrada del Combine = {s} ticks fijos", "Combine", slips=(float(s),), probs=(1.0,))
add("slip adverso acotado a ≤ 1 tick (los +3 pasan a +1; hipotético)", "Combine", slips=CAP1_S, probs=CAP1_P)
add("slip de salida del SL/liquidación 3 → 6 ticks", "Combine", cexit=6.0)
add("finish-line (P3) en lugar de 40 fijos", "Combine", pol="P3")
add("reset $49 → $0 (cota teórica)", "Combine", reset=0.0); add("reset $49 → $98", "Combine", reset=98.0); add("activación $149 → $0", "Combine", act=0.0)
add("comisión MGC $1.92 → $0", "XFA", xfee=0.0); add("comisión MGC $1.92 → $3.84", "XFA", xfee=3.84)
for s in (1, 2, 3, 4): add(f"slip de entrada MGC = {s} ticks (base 0)", "XFA", xslip=float(s))
add("slip de salida MGC 0 → 3 ticks", "XFA", xexit=3.0); add("stop exacto en lugar de 0.5", "XFA", xstop=0.0)
add("tamaño 728×3 (SL = TP = 728)", "XFA", xsl=728); add("tamaño 4→1 micros (cobro ≥ $1,500)", "XFA", plan="41")
P("## 2. Cada componente por separado (los demás en la línea base). Equilibrio bajo costos A y B; Δ vs la línea base con A\n")
E0 = {l: res[(l, "A")][0] for l in ("empírica-7", "mezcla {1,3}")}; N0 = {l: res[(l, "A")][1] for l in ("empírica-7", "mezcla {1,3}")}
P("| grupo | componente | equilibrio (A) empírica-7 | Δ pp | Δ $/año a WR 50 % | equilibrio (B) | equilibrio (A), mezcla {1,3} | Δ pp (mezcla) |\n|---|---|---|---|---|---|---|---|")
for g, lab, r in sorted(rows, key=lambda x: -abs(x[2]["empírica-7"][0][0] - E0["empírica-7"])):
    (eA, nA, _, _), (eB, _, _, _) = r["empírica-7"]
    mz = r.get("mezcla {1,3}")
    mz_s = f"{mz[0][0] * 100:.2f} % | {(mz[0][0] - E0['mezcla {1,3}']) * 100:+.2f}" if mz else "— | —"
    P(f"| {g} | {lab} | {eA * 100:.2f} % | {(eA - E0['empírica-7']) * 100:+.2f} | {nA - N0['empírica-7']:+,.0f} | {eB * 100:.2f} % | {mz_s} |")
P("\nLas filas «→ $0», «$0» y «duplicada» son cotas teóricas, no palancas (las tarifas las fijan Topstep/CME). Los costos operativos **ya no aparecen como palanca**: son un escenario (sección 1).\n")
steps = [("hoy (P0, 3×364, slip empírico)", {}), ("+ finish-line", dict(pol="P3")), ("+ 728×3", dict(pol="P3", xsl=728)), ("+ slip adverso acotado a ≤ 1 tick (hipotético)", dict(pol="P3", xsl=728, slips=CAP1_S, probs=CAP1_P))]
P("## 3. Cascada acumulada (sin «costos operativos → $0»; el equilibrio se recalcula con la cadena completa)\n")
P("| paso | equilibrio con costos A | con costos B | Δ pp (A) | neto/año a WR 50 % (A) | valor de 1 pp aquí |\n|---|---|---|---|---|---|")
cum = []
for lab, kw in steps:
    b = dict(BASE); b.update(kw); eA, nA, sA, _ = eq_for(b, OPS["A"]); eB = eq_for(b, OPS["B"])[0]; cum.append((lab, eA, eB, nA, sA))
prev = None
for lab, eA, eB, nA, sA in cum:
    P(f"| {lab} | {eA * 100:.2f} % | {eB * 100:.2f} % | {'' if prev is None else f'{(eA - prev) * 100:+.2f}'} | ${nA:,.0f} | ${sA:,.0f} |"); prev = eA
fa = lambda thr, ix: next((c[0] for c in cum if c[ix] < thr), "ninguna")
P(f"\nPrimer paso (acumulado) que baja el equilibrio por debajo de **47.4 %**: con costos A → {fa(0.474, 1)}; con costos B → {fa(0.474, 2)}. Por debajo de **46.5 %**: con A → {fa(0.465, 1)}; con B → {fa(0.465, 2)}.")
# sensibilidad de la cascada a la mezcla
steps_m = [(l, dict(kw, **({"slips": MIX_S, "probs": MIX_P} if "slips" not in kw else {}))) for l, kw in steps[:3]]
P("\nSensibilidad (mezcla {1,3} en lugar de la empírica; costos A): " + " → ".join(f"{l.split('(')[0].strip()} {eq_for(dict(BASE, **kw), OPS['A'])[0] * 100:.2f} %" for l, kw in steps_m) + ".")
# SVG
W, Hh = 900, 100 + 34 * len(cum); x0, x1 = 360, 860
vals = [c[1] * 100 for c in cum] + [c[2] * 100 for c in cum] + [46.5, 47.4]; lo, hi = min(vals) - 0.3, max(vals) + 0.3
sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" font-family="sans-serif" font-size="12"><rect width="100%" height="100%" fill="white"/>', '<text x="10" y="22" font-size="15" font-weight="bold">Cascada del equilibrio (slip empírico de 7 obs.; azul = costos A $240, gris = costos B $827)</text>']
for tx, col, lb in ((47.4, "#c0392b", "WR medido 47.4 %"), (46.5, "#27ae60", "46.5 %")): svg.append(f'<line x1="{sx(tx)}" y1="40" x2="{sx(tx)}" y2="{Hh - 30}" stroke="{col}" stroke-dasharray="4 3"/><text x="{sx(tx) - 40}" y="{Hh - 14}" fill="{col}">{lb}</text>')
y = 52
for lab, eA, eB, nA, sA in cum:
    svg.append(f'<text x="8" y="{y + 13}">{lab[:55]}</text><rect x="{x0}" y="{y}" width="{sx(eA * 100) - x0:.1f}" height="11" fill="#2980b9"/><rect x="{x0}" y="{y + 12}" width="{sx(eB * 100) - x0:.1f}" height="9" fill="#95a5a6"/><text x="{max(sx(eA * 100), sx(eB * 100)) + 6:.1f}" y="{y + 12}">{eA * 100:.2f} / {eB * 100:.2f} %</text>'); y += 34
svg.append("</svg>"); open(os.path.join(HERE, "cascada_H1b.svg"), "w", encoding="utf-8").write("\n".join(svg))
open(os.path.join(HERE, "resultados_H1b.md"), "w", encoding="utf-8").write("\n".join(out))
