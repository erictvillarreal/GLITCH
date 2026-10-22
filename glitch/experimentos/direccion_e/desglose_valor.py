"""Reconciliacion del punto de equilibrio y desglose del valor de una ventaja por etapa (respuesta a la auditoria del 21-oct). -> resultados_E_desglose.md
    GLITCH_MGC_PARQUET=... python desglose_valor.py"""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
NB, NC = 200000, 40000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
MIX = ("P0", (1.0, 3.0), (0.5, 0.5))
def xfa(dm, slip=0.0):
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(slip,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
    return xfa_bank(days, Rules(), pol_fixed(3, 364, 364), NB, seed=21)
def chain(ds_mes, bank):
    ps, cd = combine_bank(mes, NB, *MIX, seed=11, drift=ds_mes)
    life, pday, pnet = bank
    r = run_chain(ps, cd, life, pday, pnet, n=NC, seed=5)
    return float(r["net"].mean()), float(np.mean(ps)), float(pnet.sum(1).mean())
P("# resultados_E_desglose — reconciliación del equilibrio y desglose por etapa (plan 3×364, stop 0.5, Combine hoy P0 con mezcla de slip {1,3})\n")
P(f"σ de la sesión: MGC {sig_m:.0f} ticks, MES {sig_s:.0f} ticks. Bancos de {NB}, {NC} trayectorias, semillas fijas.\n")
P("## 1. Neto anual vs WR según DÓNDE se aplica la ventaja\n")
P("(a) solo en la XFA (convención de la Parte D, `resultados_D9.md`: el Combine queda sin deriva); (b) en las dos etapas (convención de §4 de la Parte E); (c) = (a) con slippage de entrada de MGC de 3 ticks (no medido; los demás cuadros lo suponen 0).\n")
P("| WR | cobrado por XFA | (a) ventaja solo en XFA | (b) ventaja en Combine y XFA | (c) = (a) con slip MGC 3 |\n|---|---|---|---|---|")
rows = {}
for wr in (0.45, 0.46, 0.47, 0.474, 0.48, 0.49, 0.50, 0.51):
    dm = 0.0 if wr == 0.50 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    b0 = xfa(dm); b3 = xfa(dm, 3.0)
    a, _, paid = chain(0.0, b0); b, _, _ = chain(ds, b0); c, _, paid3 = chain(0.0, b3)
    rows[wr] = (paid, a, b, c)
    P(f"| {wr * 100:.1f} % | ${paid:,.0f} | ${a:,.0f} | ${b:,.0f} | ${c:,.0f} |"); print(f"  WR {wr} {time.time() - t0:.0f}s", flush=True)
def be(col):
    ks = sorted(rows)
    for i in range(len(ks) - 1):
        y0, y1 = rows[ks[i]][col], rows[ks[i + 1]][col]
        if y0 < 0 <= y1: return ks[i] + (ks[i + 1] - ks[i]) * (-y0) / (y1 - y0)
    return float("nan")
ks = sorted(rows)
pb = next((ks[i] + (ks[i + 1] - ks[i]) * ((365 - rows[ks[i]][0]) / (rows[ks[i + 1]][0] - rows[ks[i]][0])) for i in range(len(ks) - 1) if rows[ks[i]][0] < 365 <= rows[ks[i + 1]][0]), float("nan"))
P(f"\n**Puntos de equilibrio (interpolación lineal en la malla de arriba):** por XFA (cobrado = $365, punto medio de $317–$446 de `EVIDENCIA_CEREBRO2.md` §4): **{pb * 100:.1f} %** · anual con la ventaja solo en la XFA (a): **{be(1) * 100:.1f} %** · en las dos etapas (b): **{be(2) * 100:.1f} %** · (a) con slip MGC 3: **{be(3) * 100:.1f} %**.")
P("\n## 2. Desglose por etapa de una ventaja estandarizada z = μ/σ (misma z en MES y MGC cuando aplica)\n")
P("| z | ≈ WR (tabla A) | solo Combine de MES | solo XFA de MGC | ambas | pasa el Combine (solo Combine) |\n|---|---|---|---|---|---|")
base, p0, _ = chain(0.0, xfa(0.0)); b_none = xfa(0.0)
for z, wr in ((0.020, "51 %"), (0.024, "≈51 %"), (0.049, "52 %"), (0.081, "53 %")):
    dm = z * sig_m; ds = z * sig_s; bz = xfa(dm)
    c_only, pc, _ = chain(ds, b_none); x_only, _, _ = chain(0.0, bz); both, _, _ = chain(ds, bz)
    P(f"| {z:.3f} | {wr} | {c_only - base:+,.0f} | {x_only - base:+,.0f} | {both - base:+,.0f} | {pc * 100:.1f} % (base {p0 * 100:.1f} %) |"); print(f"  z {z} {time.time() - t0:.0f}s", flush=True)
P(f"\nBase (sin ventaja): ${base:,.0f}/año por cuenta. Las columnas son la diferencia contra la base.")
P("\n## 3. La cuenta de ‘siempre LARGO’ en el Combine de MES, paso a paso\n")
d0 = sim_day(mes, 1, 40, 2000.0, slip=1.0, exit_slip=3.0, sl=100, tp=32, fee=1.22, tick_usd=1.25)
z = 0.024; ds = z * sig_s
d1 = sim_day(mes, 1, 40, 2000.0, slip=1.0, exit_slip=3.0, sl=100, tp=32, fee=1.22, tick_usd=1.25, drift=ds)
P(f"- μ/σ de ^GSPC apertura→cierre (1990–2026) = +0.024 (media +2.46 pb/día, σ 1.04 %). Sesión de MES: σ = {sig_s:.0f} ticks ⇒ deriva = 0.024 × {sig_s:.0f} = **{ds:.1f} ticks/día** a favor del lado LARGO.")
P(f"- Bruto si cobrara toda la deriva: {ds:.1f} ticks × $1.25 × 40 contratos = **${ds * 1.25 * 40:,.0f}/día de operación**.")
P(f"- Con el bracket real (TP 32 / piso $2,000, slip 1, salida 3): P&L medio por día de LARGO **${d0[1].mean():+,.0f}** sin deriva → **${d1[1].mean():+,.0f}** con ella (**{d1[1].mean() - d0[1].mean():+,.0f} $/día**); TP {np.mean(d0[0] == 0) * 100:.1f} % → {np.mean(d1[0] == 0) * 100:.1f} %, liquidación/SL {np.mean((d0[0] == 1) | (d0[0] == 2)) * 100:.1f} % → {np.mean((d1[0] == 1) | (d1[0] == 2)) * 100:.1f} %.")
P("- Esa ganancia por día solo existe mientras el Combine está abierto (≈ 10–20 días por intento); el valor anual sale de que cambie P(pasar) y por tanto cuántas XFA se obtienen (tabla 2, columna «solo Combine»).")
open(os.path.join(HERE, "resultados_E_desglose.md"), "w").write("\n".join(out))
