"""Parte H, H1: descomposición del WR de equilibrio de la cadena completa por componente (uno a la vez), cascada y combinaciones. -> resultados_H1.md, cascada_H1.svg
Convención = Parte E §4 (la ventaja se impone en las DOS etapas con la misma deriva estandarizada). Equilibrio = WR_dec en que el neto anual por cuenta es 0, interpolando (o extrapolando linealmente)
entre WR = 48 % y 50 %. Las diferencias entre filas usan los mismos números aleatorios (ruido de nivel ≈ ±$100, de diferencia ≈ ±$30 ⇒ ≈ ±0.03 pp en el equilibrio).
    GLITCH_MGC_PARQUET=... python h1_equilibrio.py"""
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
def pol41(): return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
BASE = dict(pol="P0", slips=(1.0, 3.0), probs=(0.5, 0.5), cexit=3.0, cfee=1.22, reset=49.0, act=149.0, ops=714.0, xsl=364, plan="fixed", xfee=1.92, xslip=0.0, xexit=0.0, xstop=0.5, ctp=32, csl=100)
_drift = {}; _cb = {}; _xb = {}
def drift_of(wr):
    if wr not in _drift: _drift[wr] = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr)
    return _drift[wr]
def net_at(cfg, wr):
    dm = drift_of(wr); ds = dm / sig_m * sig_s
    kc = (cfg["pol"], cfg["slips"], cfg["probs"], cfg["cexit"], cfg["cfee"], cfg["ctp"], cfg["csl"], round(ds, 6))
    if kc not in _cb: _cb[kc] = combine_bank(mes, NB, cfg["pol"], cfg["slips"], cfg["probs"], seed=11, exit_slip=cfg["cexit"], drift=ds, fee=cfg["cfee"], tp_ticks=cfg["ctp"], sl_ticks=cfg["csl"])
    kx = (cfg["xsl"], cfg["plan"], cfg["xfee"], cfg["xslip"], cfg["xexit"], cfg["xstop"], round(dm, 6))
    if kx not in _xb:
        days = BarDays(clean, MGC["tick_usd"], cfg["xfee"], cfg["xsl"], cfg["xsl"], slip=(cfg["xslip"],), exit_slip=cfg["xexit"], mask=mk, cush_max=9000.0, drift=dm, stop_frac=cfg["xstop"])
        _xb[kx] = xfa_bank(days, Rules(), pol_fixed(3, cfg["xsl"], cfg["xsl"]) if cfg["plan"] == "fixed" else pol41(), NB, seed=21)
    ps, cd = _cb[kc]; life, pday, pnet = _xb[kx]
    return float(run_chain(ps, cd, life, pday, pnet, n=NC, seed=5, reset_fee=cfg["reset"], act_fee=cfg["act"], ops=cfg["ops"])["net"].mean())
def equilibrium(cfg):
    n48, n50 = net_at(cfg, 0.48), net_at(cfg, 0.50)
    slope = (n50 - n48) / 2.0                               # $/año por punto de WR
    return 0.48 + (-n48) / slope * 0.01 if slope > 0 else float("nan"), n48, n50, slope
b = equilibrium(BASE); E0, N48_0, N50_0, S0 = b
P("# resultados_H1 — descomposición del equilibrio de la cadena completa (WR_dec en que el neto anual por cuenta = 0)\n")
P("**Idea en tres líneas.** El equilibrio es el WR mínimo para no perder dinero después de todos los costos; cada costo que baja (o cada forma de la cadena que mejora) baja el listón, **no la puntería**. Como un volado con cuota del 3 % exige 51.5 % y con cuota del 1 % exige 50.5 %, aquí cada componente mueve el equilibrio tantos puntos como dólares/año valga dividido por lo que vale un punto de WR (≈ $1.1–1.4k/año/cuenta en esta cadena).\n")
P(f"Línea base: Combine P0 nc 40 con slip de entrada mezcla {{1,3}} 50/50 (SUPUESTO), salida del SL con 3 ticks de gap (SUPUESTO), comisión MES $1.22 y MGC $1.92, reset/mensualidad $49 por intento, activación $149, costos operativos $714/año compartidos, XFA 3×364 con stop 0.5, slip MGC 0. **Equilibrio base = {E0 * 100:.2f} %**; neto anual a 48 % = ${N48_0:,.0f}, a 50 % = ${N50_0:,.0f}; **valor de un punto de WR ≈ ${S0:,.0f}/año/cuenta** (pendiente local 48–50 %).\n")
rows = []
def comp(label, group, **kw):
    cfg = dict(BASE); cfg.update(kw); e, n48, n50, sl = equilibrium(cfg)
    rows.append((group, label, e, n50, n48, sl, (e - E0) * 100, (n50 - N50_0))); print("  ", label, round(time.time() - t0), "s", flush=True)
# Combine
comp("comisión MES $1.22 → $0 (límite inferior teórico)", "Combine", cfee=0.0); comp("comisión MES $1.22 → $2.44 (duplicada)", "Combine", cfee=2.44)
for s in (0, 1, 2, 3, 4): comp(f"slip de entrada del Combine = {s} ticks fijos (base: mezcla 1/3)", "Combine", slips=(float(s),), probs=(1.0,))
comp("slip de salida del SL/liquidación 3 → 0 ticks", "Combine", cexit=0.0); comp("slip de salida 3 → 6 ticks", "Combine", cexit=6.0)
comp("finish-line (P3) en lugar de 40 fijos", "Combine", pol="P3")
comp("reset/mensualidad $49 → $0 (límite teórico)", "Combine", reset=0.0); comp("reset/mensualidad $49 → $98", "Combine", reset=98.0)
comp("activación $149 → $0", "Combine", act=0.0); comp("costos operativos $714 → $0", "Combine", ops=0.0); comp("costos operativos $714 → $1,428", "Combine", ops=1428.0)
# XFA
comp("comisión MGC $1.92 → $0", "XFA", xfee=0.0); comp("comisión MGC $1.92 → $3.84", "XFA", xfee=3.84)
for s in (1, 2, 3, 4): comp(f"slip de entrada MGC = {s} ticks (base: 0)", "XFA", xslip=float(s))
comp("slip de salida MGC (SL/FLATTEN) 0 → 3 ticks", "XFA", xexit=3.0); comp("slip de salida MGC 0 → 6 ticks", "XFA", xexit=6.0)
comp("stop exacto (convención optimista) en lugar de 0.5", "XFA", xstop=0.0)
comp("tamaño 728×3 (SL = TP = 728)", "XFA", xsl=728); comp("tamaño 4→1 micros (cobro ≥ $1,500)", "XFA", plan="41")
# combinaciones acumuladas de palancas verificables
steps = [("hoy", {}), ("+ finish-line (P3)", dict(pol="P3")), ("+ 728×3", dict(pol="P3", xsl=728)), ("+ costos operativos $714 → $0 (pausar servicios sobrantes)", dict(pol="P3", xsl=728, ops=0.0)),
         ("+ slip de entrada del Combine ≤ 1 tick (si el anclaje/límite lo logra)", dict(pol="P3", xsl=728, ops=0.0, slips=(1.0,), probs=(1.0,)))]
cum = []
for lab, kw in steps:
    cfg = dict(BASE); cfg.update(kw); e, n48, n50, sl = equilibrium(cfg); cum.append((lab, e, n50, sl)); print("  cum", lab, round(time.time() - t0), "s", flush=True)
P("## 1. Cada componente por separado (los demás en la línea base)\n")
P("| grupo | componente | equilibrio | Δ equilibrio (pp) | neto/año a WR 50 % | Δ $/año/cuenta a WR 50 % | neto/año a 47.4 % (extrapolado) | estado |\n|---|---|---|---|---|---|---|---|")
for g, lab, e, n50, n48, sl, de, dn in sorted(rows, key=lambda r: -abs(r[6])):
    n474 = n48 + (0.474 - 0.48) * 100 * sl
    st = "MEDIDO (tarifa oficial)" if ("comisión" in lab and "→ $0" not in lab and "duplicada" not in lab) or "reset" in lab or "activación" in lab else ("MODELADO; el valor del parámetro es SUPUESTO" if "slip" in lab else "MODELADO")
    P(f"| {g} | {lab} | {e * 100:.2f} % | {de:+.2f} | ${n50:,.0f} | {dn:+,.0f} | ${n474:,.0f} | {st} |")
P("\nLectura: los componentes de la tabla marcados «→ $0» o «duplicada» son **cotas teóricas**, no palancas disponibles (la comisión y la tarifa las fija Topstep/CME). Las palancas controlables son: **finish-line, tamaño/política de la XFA, slippage (por cómo se ejecuta y se ancla) y costos operativos**.\n")
P("## 2. Cascada acumulada de palancas controlables (cada paso suma al anterior; el equilibrio se recalcula con la cadena completa, no se suma)\n")
P("| paso | equilibrio | Δ vs paso anterior (pp) | neto/año a WR 50 % | valor de 1 pp aquí |\n|---|---|---|---|---|")
prev = E0
for i, (lab, e, n50, sl) in enumerate(cum):
    P(f"| {lab} | {e * 100:.2f} % | {'' if i == 0 else f'{(e - prev) * 100:+.2f}'} | ${n50:,.0f} | ${sl:,.0f} |"); prev = e
below = lambda thr: next((c[0] for c in cum if c[1] < thr), "ninguna")
P(f"\n**Primera combinación (en este orden) que baja el equilibrio de la cadena por debajo de 47.4 %:** {below(0.474)}. **Por debajo de 46.5 %:** {below(0.465)}.")
P("Evidencia de cada paso: finish-line y 728×3 son **MODELADOS** con el motor de las Partes A/D sobre días reales (no medidos en vivo); 728×3 y 4→1 tocan los criterios de RTP/«conducta prohibida» (preguntas pendientes para Topstep); «costos operativos → $0» es una **decisión** (qué servicios se pausan), no un hecho de mercado; «slip ≤ 1 tick» es un **SUPUESTO** hasta tener C3 (hoy N = 2).")
# SVG cascada
W, Hh = 900, 90 + 34 * (len(cum) + 1); x0, x1 = 330, 860
vals = [E0 * 100] + [c[1] * 100 for c in cum[1:]]; lo, hi = min(vals + [46.0, 47.4]) - 0.3, max(vals) + 0.3
sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" font-family="sans-serif" font-size="12"><rect width="100%" height="100%" fill="white"/>',
       '<text x="10" y="22" font-size="15" font-weight="bold">Cascada del WR de equilibrio de la cadena completa (menor = mejor)</text>']
for tx, col, lb in ((47.4, "#c0392b", "WR medido 47.4 %"), (46.5, "#27ae60", "46.5 % (margen)")):
    svg.append(f'<line x1="{sx(tx)}" y1="40" x2="{sx(tx)}" y2="{Hh - 30}" stroke="{col}" stroke-dasharray="4 3"/><text x="{sx(tx) - 40}" y="{Hh - 14}" fill="{col}">{lb}</text>')
y = 56; prev = E0 * 100
for i, (lab, e, n50, sl) in enumerate(cum):
    v = e * 100; a, bb = sorted((prev, v)); a_x, b_x = sx(a), sx(bb) if i else sx(v)
    if i == 0: svg.append(f'<rect x="{x0}" y="{y}" width="{sx(v) - x0}" height="18" fill="#7f8c8d"/>')
    else: svg.append(f'<rect x="{sx(a)}" y="{y}" width="{max(sx(bb) - sx(a), 1)}" height="18" fill="#2980b9"/>')
    svg.append(f'<text x="8" y="{y + 13}">{lab[:52]}</text><text x="{(sx(v) if i == 0 else sx(bb)) + 6}" y="{y + 13}">{v:.2f} %</text>')
    prev = v; y += 34
svg.append("</svg>")
open(os.path.join(HERE, "cascada_H1.svg"), "w", encoding="utf-8").write("\n".join(svg))
open(os.path.join(HERE, "resultados_H1.md"), "w", encoding="utf-8").write("\n".join(out))
