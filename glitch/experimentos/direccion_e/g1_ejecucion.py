"""Parte G, G1c/G1d/G1e: valor de un tick de slippage, anclar al fill vs a la referencia, y estilos de entrada. Motor de las Partes A y D. -> resultados_G1.md
    GLITCH_MGC_PARQUET=... python g1_ejecucion.py"""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
NB, NC = 100000, 40000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk, cush_max=9000.0, drift=0.0, stop_frac=0.5)
life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), NB, seed=21)
cache = {}
def chain(pol, slips, probs, sl=100, tp=32, daysf=1.0):
    key = (pol, slips, probs, sl, tp)
    if key not in cache: cache[key] = combine_bank(mes, NB, pol, slips, probs, seed=11, sl_ticks=sl, tp_ticks=tp)
    ps, cd = cache[key]
    cd2 = np.maximum(1, np.round(np.asarray(cd) * daysf)).astype(cd.dtype) if daysf != 1.0 else cd
    r = run_chain(ps, cd2, life, pday, pnet, n=NC, seed=5)
    return float(np.mean(ps)), float(np.mean(cd)), float(r["net"].mean())
P("# resultados_G1 — ejecución: valor del tick, anclaje al fill y estilos de entrada (MES Combine nc 40; XFA 3×364 sin ventaja; Combine P0 con finish-line P3 donde se indica)\n")
P(f"Bancos de {NB}, {NC} trayectorias, semillas fijas. Sin ventaja direccional. **El nivel del neto anual tiene ruido de simulación de ±$100** (ver F1); las diferencias pareadas entre filas usan los mismos números aleatorios y son más estables (±$20–40).\n")
P("## G1e. Curva del slippage de entrada (0–4 ticks adversos, fijo en cada fila)\n")
P("M1 = el precio se movió antes del fill (ruido); M2 = costo de ejecución puro (ver `resultados_F3_slippage.md`). Hoy: TP/SL anclados a la **referencia**.\n")
P("| slip | M1 P(pasar) | M1 días a resolver | M1 neto $/año | M1 con finish-line P3 | M2 P(pasar) | M2 días | M2 neto $/año | M2 con P3 |\n|---|---|---|---|---|---|---|---|---|")
rows = {}
for s in (0, 1, 2, 3, 4):
    m1 = chain("P0", (0.0,), (1.0,), sl=100 + s, tp=32 - s); m1p = chain("P3", (0.0,), (1.0,), sl=100 + s, tp=32 - s)
    m2 = chain("P0", (float(s),), (1.0,)); m2p = chain("P3", (float(s),), (1.0,))
    rows[s] = (m1, m1p, m2, m2p)
    P(f"| {s} | {m1[0] * 100:.1f} % | {m1[1]:.1f} | ${m1[2]:,.0f} | ${m1p[2]:,.0f} | {m2[0] * 100:.1f} % | {m2[1]:.1f} | ${m2[2]:,.0f} | ${m2p[2]:,.0f} |"); print(f"  {time.time() - t0:.0f}s", flush=True)
P("\n**Valor de 1 tick de slippage sistemático (entre 1 y 3 ticks, por tick):** " +
  " · ".join(f"{lab}: P(pasar) {(rows[3][i][0] - rows[1][i][0]) / 2 * 100:+.1f} pp, neto {(rows[3][i][2] - rows[1][i][2]) / 2:+,.0f} $/año/cuenta" for lab, i in (("M1", 0), ("M2", 2))) +
  f". Entre 0 y 4: M2 {(rows[4][2][2] - rows[0][2][2]) / 4:+,.0f} $/año/cuenta por tick.")
P("\n## G1c. Anclar TP/SL a la referencia (hoy) vs al fill\n")
P("(ii) y (iii) producen la misma geometría: TP a +32 y SL a −100 ticks **del fill** (en (ii) el Pi confirma el fill y entonces envía TP/SL; en (iii) la API los pone como brackets nativos). Bajo **M1** el fill es el origen del camino ⇒ equivale a slip 0 de la tabla anterior (el slippage por movimiento de precio deja de importar). Bajo **M2** el camino real no cambia, el TP queda a 32 + s ticks de la referencia y paga 32 ticks.\n")
P("| s | (i) hoy M1 | (i) hoy M2 | (ii)/(iii) M1 = slip 0 | (ii)/(iii) M2: P(pasar) / neto |\n|---|---|---|---|---|")
for s in (1, 2, 3):
    m2a = chain("P0", (float(s),), (1.0,), sl=100 + s, tp=32 + s)
    P(f"| {s} | {rows[s][0][0] * 100:.1f} % / ${rows[s][0][2]:,.0f} | {rows[s][2][0] * 100:.1f} % / ${rows[s][2][2]:,.0f} | {rows[0][0][0] * 100:.1f} % / ${rows[0][0][2]:,.0f} | {m2a[0] * 100:.1f} % / ${m2a[2]:,.0f} |")
P("\n**Con finish-line (P3) ya adoptado** el acantilado ya está mitigado, así que anclar al fill vale menos:\n")
P("| s | (i) hoy M1 / M2 (P3) | (ii)/(iii) M1 (P3) | (ii)/(iii) M2 (P3) |\n|---|---|---|---|")
for s_ in (1, 2, 3):
    a3 = chain("P3", (float(s_),), (1.0,), sl=100 + s_, tp=32 + s_)
    P(f"| {s_} | ${rows[s_][1][2]:,.0f} / ${rows[s_][3][2]:,.0f} | ${rows[0][1][2]:,.0f} | ${a3[2]:,.0f} |")
P("\nLectura: anclar al fill elimina el acantilado 2→3 TP (cada TP paga 32 ticks sin importar el slippage). No elimina el costo sistemático (bajo M2 el neto sigue cayendo con s, porque el camino real no se mueve a tu favor), pero evita que ese costo además cambie la forma del pago.")
P("\n## G1d. Estilos de entrada (supuestos explícitos; NO hay distribución medida de slippage, N = 2)\n")
P("**Supuesto, no medido:** el slippage por día es `s = 0.5 (sistemático, medio spread) + ruido`, con ruido normal de σ ∈ {1, 2} ticks, redondeado al tick. Solo sirve para comparar *políticas*; los niveles dependen del supuesto.\n")
P("| σ del ruido | política | % de días sin entrar | P(pasar) por intento | neto $/año (días ajustados por 1/(1−f)) |\n|---|---|---|---|---|")
for sg in (1.0, 2.0):
    grid = np.arange(-4, 9); pr = np.exp(-0.5 * ((grid - 0.5) / sg) ** 2); pr /= pr.sum()
    for nm, cap in (("mercado (hoy)", None), ("límite marketable, tope 1 tick", 1), ("límite marketable, tope 2 ticks", 2)):
        keep = np.ones(len(grid), bool) if cap is None else grid <= cap
        f = 1 - pr[keep].sum(); w = tuple(pr[keep] / pr[keep].sum()); sl_ = tuple(float(x) for x in grid[keep])
        r = chain("P0", sl_, w, daysf=1.0 / (1 - f))
        P(f"| {sg:g} | {nm} | {f * 100:.0f} % | {r[0] * 100:.1f} % | ${r[2]:,.0f} |")
print("fin", time.time() - t0)
P("\n**(a) Partir las 40 en bloques:** el libro de MES tiene miles de contratos al inicio de la sesión; 40 micros no mueven el precio de forma medible (impacto ≈ 0 respecto del medio spread, **supuesto sin medir**), y partirlos añade latencia (el precio se mueve mientras se envían los bloques) y TP/SL por bloque. **No recomendado.**")
P("**(c) Polling de 5–10 s en 9:34–9:40 CT:** acorta la espera del Pi de U(0, 120 s) (media 60 s) a ≈ 3–5 s. **No cambia el slippage** (la orden de mercado y la referencia se toman cuando el Pi actúa, no cuando Railway escribe), sí acerca la entrada a 9:35:00 (fidelidad con el paper, que entra ≈ 9:40) y acorta la ventana del plan B. Costo: ≈ 72 lecturas del Gist en la ventana de 6 min (cuota REST de GitHub autenticada: 5,000 por hora, hecho conocido; NO verificado en esta sesión). Complejidad baja. **Efecto en dólares: no medible (la Parte A no encontró efecto de la hora de entrada); se justifica por fiabilidad, no por costo.**")
open(os.path.join(HERE, "resultados_G1.md"), "w").write("\n".join(out))
