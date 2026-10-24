"""Parte G4 (rehecho, 24-oct): escala con costos operativos separados en COMPARTIDOS (Railway ≈ $66/año, una vez) y POR CUENTA (API $174/año; en B, además la mensualidad del Combine $49×12 ≈ $587).
Marginal de una cuenta con slippage de entrada EMPÍRICO (7 obs., dato de Eric) y ops = 0; los costos se restan después. Dependencia entre cuentas: cópula gaussiana (ρ SUPUESTO).
-> resultados_G4b.md.   GLITCH_MGC_PARQUET=... python g4_ops_por_cuenta.py"""
import os, sys, time
import numpy as np
from scipy.stats import norm
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
NB, NC, M = 150000, 40000, 40000
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
OBS = (0.0, 1.0, 0.0, 3.0, -1.0, 1.0, 3.0); ES = tuple(sorted(set(OBS))); EP = tuple(OBS.count(s) / 7 for s in ES)
SHARED, PER = 66.0, {"A": 174.0, "B": 174.0 + 587.0}                              # A = 66 + 174 = $240; B = 66 + 174 + 587 = $827
def bank(sl):
    d = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=0.0, stop_frac=0.5)
    return xfa_bank(d, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
b364, b728 = bank(364), bank(728)
CFG = {"hoy (P0, 3×364)": ("P0", b364), "+ finish-line (P3, 3×364)": ("P3", b364), "+ finish-line + 728×3": ("P3", b728)}
marg = {}
for slab, (sl, pr) in (("empírica-7", (ES, EP)), ("mezcla {1,3}", ((1.0, 3.0), (0.5, 0.5)))):
    cbs = {p: combine_bank(mes, NB, p, sl, pr, seed=11) for p in ("P0", "P3")}
    for nm, (pol, bk) in CFG.items():
        r = run_chain(cbs[pol][0], cbs[pol][1], *bk, n=NC, seed=5, ops=0.0); o = np.argsort(r["net"]); marg[(slab, nm)] = (r["net"][o], r["cash"][o], r["fees"][o])
P("# resultados_G4b — escala con costos operativos por cuenta (API) y compartidos (Railway)\n")
P("**Fuentes y estado.** Los montos (API $174 por cuenta y año, Railway ≈ $65, mensualidad del Combine $49) los dio Eric en el chat: **SUPUESTO / NO VERIFICADO con facturas** (escenario C pendiente). Escenario A: costos = $66 compartidos + $174 × N. Escenario B: $66 + ($174 + $587) × N (la mensualidad del Combine por cuenta, aparte del reset de $49 por intento que ya está en el modelo; **si el reset ya incluye la mensualidad, B cuenta doble**: pregunta para Eric). Para N = 1 dan $240 y $827. **Escenario C:** el ingreso total baja exactamente $1 por cada $1 de costos: con costos por cuenta c y compartidos s, ingreso(N) = ingreso_A(N) − [(c − 174)·N + (s − 66)].\n")
P("Marginal de una cuenta (ops = 0) con slippage de entrada **empírico de 7 observaciones**; la sensibilidad con la mezcla {1,3} está al final de cada bloque. Dependencia entre cuentas: ρ = 1 (mismos trades), 0.5 (**supuesto ilustrativo**), 0 (independientes; el ρ de retornos MES–MGC medido es 0.17, no el de resultados). La dependencia **no se simuló día a día**.\n")
rng = np.random.default_rng(20261024)
def totals(key, N, rho, sc):
    net0, cash, fees = marg[key]; z0 = rng.standard_normal(M); tn = np.zeros(M); allneg = np.ones(M, bool)
    for i in range(N):
        z = np.sqrt(rho) * z0 + np.sqrt(1 - rho) * rng.standard_normal(M); ix = np.minimum((norm.cdf(z) * len(net0)).astype(int), len(net0) - 1)
        ni = net0[ix] - PER[sc] - SHARED / N; tn += ni; allneg &= ni < 0
    return tn, allneg
for sc in ("A", "B"):
    for nm in CFG:
        n1 = marg[("empírica-7", nm)][0]
        P(f"\n## Escenario {sc} — {nm}: una cuenta sin costos operativos ${n1.mean():,.0f}/año; con costos {'$240' if sc == 'A' else '$827'}: ${n1.mean() - PER[sc] - SHARED:,.0f}\n")
        P("| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |\n|---|---|---|---|---|---|---|---|---|")
        for N in (1, 2, 3, 4, 5):
            for rho in ((1.0,) if N == 1 else (1.0, 0.5, 0.0)):
                tn, an = totals(("empírica-7", nm), N, rho, sc); tm, _ = totals(("mezcla {1,3}", nm), N, rho, sc)
                P(f"| {N} | {'—' if N == 1 else rho} | ${tn.mean():,.0f} | ${np.percentile(tn, 10):,.0f} | {np.mean(tn < 0) * 100:.0f} % | {an.mean() * 100:.0f} % | {np.mean(tn >= 3000) * 100:.0f} % | ${SHARED + PER[sc] * N:,.0f} | ${tm.mean():,.0f} |")
P("\n**Lectura.** (1) Con la API por cuenta el ingreso sigue siendo lineal en N pero cada cuenta cuesta $174 (A) o $761 (B) al año en lugar de absorber una cuota compartida: a N = 5 los costos operativos son $936 (A) o $3,871 (B), no $714. (2) El slippage empírico (media +1.0, con −1 y 0 en 3 de 7 casos) da una cuenta mejor que la mezcla {1,3} en +$0.76k/año (hoy, 40 fijos), +$0.29k (con finish-line) y +$0.36k (finish-line + 728×3) — comparación de la fila N = 1, costos A; ambos slippage son **N = 7 / supuesto**. (3) Todas las probabilidades de riesgo dependen de ρ, que no se estimó; mismos trades en todas las cuentas es además el patrón que Topstep cita como motivo de RTP.")
open(os.path.join(HERE, "resultados_G4b.md"), "w", encoding="utf-8").write("\n".join(out))
