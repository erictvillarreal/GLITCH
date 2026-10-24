"""Parte G, G4: N = 1..5 cuentas. Marginales de UNA cuenta con el motor de las Partes A y D; la dependencia entre cuentas se modela con una cópula gaussiana de correlación rho
(SUPUESTO, no estimado: ver abajo) sobre el neto anual. -> resultados_G4.md.   GLITCH_MGC_PARQUET=... python g4_escala.py"""
import os, sys, time
import numpy as np
from math import erf, sqrt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
from scipy.stats import norm
NB, NC, M = 150000, 40000, 40000
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
def bank(sl):
    d = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=0.0, stop_frac=0.5)
    return xfa_bank(d, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
b364, b728 = bank(364), bank(728)
cbs = {"P0": combine_bank(mes, NB, "P0", (1.0, 3.0), (0.5, 0.5), seed=11), "P3": combine_bank(mes, NB, "P3", (1.0, 3.0), (0.5, 0.5), seed=11)}
CFG = {"hoy (P0, 3×364)": ("P0", b364), "+ finish-line (P3, 3×364)": ("P3", b364), "+ finish-line + 728×3": ("P3", b728)}
marg = {}
for nm, (pol, bk) in CFG.items():
    r = run_chain(cbs[pol][0], cbs[pol][1], *bk, n=NC, seed=5); o = np.argsort(r["net"])
    marg[nm] = (r["net"][o], r["cash"][o], r["fees"][o])
P("# resultados_G4 — escala: N cuentas (ingreso anual, riesgo de un año malo, costos)\n")
P(f"Marginal de UNA cuenta = cadena Combine → XFA → Combine de las Partes A y D (reglas verificadas, sin RTP, sin ventaja direccional, stop 0.5, Combine con mezcla de slip {{1,3}}), {NC} trayectorias. **La dependencia entre cuentas NO se simuló día a día**: se impone con una cópula gaussiana de correlación ρ sobre el neto anual (**ρ es un supuesto**, no se estimó). Casos: (a) mismo producto y mismos trades ⇒ ρ = 1 (si todas empiezan el mismo día los intentos son idénticos); (b) dos productos distintos ⇒ ρ = 0 (**supuesto**: no hay marginal de un segundo producto; se reutiliza la de MES/MGC); (c) inicios escalonados con el mismo producto ⇒ ρ = 0.5 (**supuesto ilustrativo**: cada día de mercado es común a todas las cuentas, el escalonamiento solo desfasa en qué etapa está cada una).\n")
rng = np.random.default_rng(20261024)
def totals(nm, N, rho):
    net, cash, fees = marg[nm]; z0 = rng.standard_normal(M); tn = np.zeros(M); tc = np.zeros(M); tf = np.zeros(M); allneg = np.ones(M, bool); zero_cash = np.ones(M, bool)
    for i in range(N):
        z = np.sqrt(rho) * z0 + np.sqrt(1 - rho) * rng.standard_normal(M)
        ix = np.minimum((norm.cdf(z) * len(net)).astype(int), len(net) - 1)
        tn += net[ix]; tc += cash[ix]; tf += fees[ix]; allneg &= net[ix] < 0; zero_cash &= cash[ix] <= 0
    tn = tn + (N - 1) * 714.0          # los $714/año de costos operativos (OPS de chain.py) son COMPARTIDOS: se cuentan una sola vez, no una por cuenta
    return tn, tc, tf, allneg, zero_cash
for nm in CFG:
    P(f"\n## {nm} — una cuenta: media ${marg[nm][0].mean():,.0f}/año, P(neto < 0) {np.mean(marg[nm][0] < 0) * 100:.0f} %, P(sin ningún pago) {np.mean(marg[nm][1] <= 0) * 100:.0f} %\n")
    P("| N | caso | ingreso anual esperado | p10 | P(total < 0) | P(sin ningún pago en ninguna cuenta) | P(todas pierden) | P(total ≥ $3k) | costos medios (mensualidades+activaciones+resets) |\n|---|---|---|---|---|---|---|---|---|")
    for N in (1, 2, 3, 4, 5):
        for lab, rho in (("(a) ρ = 1", 1.0), ("(c) ρ = 0.5", 0.5), ("(b) ρ = 0", 0.0)):
            if N == 1 and rho != 1.0: continue
            tn, tc, tf, an, zc = totals(nm, N, rho)
            P(f"| {N} | {lab if N > 1 else '—'} | ${tn.mean():,.0f} | ${np.percentile(tn, 10):,.0f} | {np.mean(tn < 0) * 100:.0f} % | {zc.mean() * 100:.0f} % | {an.mean() * 100:.0f} % | {np.mean(tn >= 3000) * 100:.0f} % | ${tf.mean():,.0f} |")
P("\n## Reglas que limitan o penalizan la escala (RULEBOOK_XFA.md; hechos del Help Center leído el 20-oct salvo lo marcado)\n- Hasta **5 XFA activas** a la vez (1.2). Número máximo de Combines simultáneos: **no está en lo que leí (NO VERIFICADO; pregunta para Topstep)**.\n- **«Varias cuentas tocando el MLL el mismo día»** es un motivo público de RTP (6.1) y las **compras excesivas de Combines/Resets** son conducta prohibida (6.3, umbral sin publicar). El caso (a) (mismos trades en todas las cuentas) **produce exactamente ese patrón**: aunque cada cuenta sea legítima, N cuentas con el mismo trade pierden juntas el mismo día. Hoy una cuenta compra ≈ 44–53 Combines/año; N cuentas multiplican ese número. Se reporta como **riesgo de reglas**, no como palanca.\n- Explícitamente fuera de alcance: lados opuestos entre cuentas para «asegurar» un pase (apilamiento/cobertura entre cuentas; viola los términos).\n- Si copiar la misma estrategia en cuentas propias en paralelo está permitido: **NO VERIFICADO (pregunta para Topstep)**; restricciones de noticias del Combine: **NO VERIFICADO**.")
open(os.path.join(HERE, "resultados_G4.md"), "w").write("\n".join(out))
