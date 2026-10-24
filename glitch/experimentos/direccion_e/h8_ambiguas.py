"""Parte H, H8: barras ambiguas (TP y barrera adversa tocadas en la misma barra de 5 min) y reproducibilidad de las cifras. -> resultados_H8.md
    GLITCH_MGC_PARQUET=... python h8_ambiguas.py"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
P("# resultados_H8 — barras ambiguas y reproducibilidad\n")
P("## 1. ¿Sigue el defecto de `label_triple_barrier()`?\n")
P("- **Hecho (código de `main` a387a70):** `simulation/triple_barrier.py` comprueba el **SL primero** en largos y cortos (comentario «BUGFIX 25-ago-2026», metodología de López de Prado: en barra ambigua se asume la pérdida). **El defecto del handoff v8 está corregido en `main`** (commit 286bc8d y merge 99497ec).\n- `scripts/quantify_ambiguous_bars.py` existe; el log (`GLITCH_RESEARCH_LOG.md` ~l.165) dice que el bug fue «confirmado y corregido» y `scripts/revalidate_geometry_table.py` volvió a validar con la corrección (WR empírico de RR = 0.33: 71.7 % vs 75 % del video).\n- **Los motores que producen las cifras de las Partes A–G no pasan por esa función:** `preservacion/daydata.py::sim_day` (orden `adverse`: gana la pérdida en empate), `dd_cash/engine_real*.py`/`lever_engine.py` (`tp_hit = tb < ab`: empate ⇒ adverso) y `dd_wr/product_sweep.py` (SL primero). **Todas son conservadoras en el empate.**\n")
P("## 2. Cuánto pesa el empate: cota conservadora ↔ cota optimista (TP gana el empate)\n")
alt = np.array([decide_side(trading_day_index(d), "alternate") for d in clean.dates])
def kinds(dd, side, nc, cush, sl, tp, fee, tv, order, slip=0.0, exit_slip=0.0, stop_frac=0.0):
    return sim_day(dd, side, nc, cush, slip=slip, exit_slip=exit_slip, sl=sl, tp=tp, order=order, fee=fee, tick_usd=tv, stop_frac=stop_frac)[0]
P("| caso | días con empate que decide | TP % conservador | TP % optimista | WR_dec conservador | WR_dec optimista |\n|---|---|---|---|---|---|")
for nm, dd, nc, cush, sl, tp, fee, tv, sf, sides in (("MGC 3×364 `alternate` (limpio)", clean, 3, 9000.0, 364, 364, MGC["fee"], MGC["tick_usd"], 0.5, alt),
                                                    ("MES nc 40 TP 32 / liquidación 40 — LARGO", mes, 40, 2000.0, 100, 32, 1.22, 1.25, 0.0, np.ones(mes.D, int)),
                                                    ("MES nc 40 TP 32 / liquidación 40 — CORTO", mes, 40, 2000.0, 100, 32, 1.22, 1.25, 0.0, -np.ones(mes.D, int))):
    res = {}
    for o in ("adverse", "favorable"):
        k1, k2 = kinds(dd, 1, nc, cush, sl, tp, fee, tv, o, stop_frac=sf), kinds(dd, -1, nc, cush, sl, tp, fee, tv, o, stop_frac=sf)
        res[o] = np.where(sides == 1, k1, k2)
    chg = (res["adverse"] != res["favorable"]).sum()
    f = lambda k: (np.mean(k == 0), np.sum(k == 0) / max(np.sum((k == 0) | (k == 1) | (k == 2)), 1))
    (a_tp, a_wr), (b_tp, b_wr) = f(res["adverse"]), f(res["favorable"])
    P(f"| {nm} | {chg} de {dd.D} ({chg / dd.D * 100:.1f} %) | {a_tp * 100:.1f} | {b_tp * 100:.1f} | {a_wr * 100:.1f} % | {b_wr * 100:.1f} % |")
P("\nLectura: en MGC con barreras de 364 ticks una barra de 5 min casi nunca toca ambas: el 47.4 % **no** depende de la regla de empate. En MES (TP 32, liquidación a 40 ticks ⇒ 72 ticks entre barreras) algunos días de apertura sí: la columna optimista es una **cota superior**, no un resultado.\n")
P("## 3. Cifras clave bajo las dos reglas (Combine MES, slip 1/3 mezcla; XFA 3×364 W2, WR 50 %)\n")
rows = []
for o in ("adverse", "favorable"):
    ps, cd = combine_bank(mes, 100000, "P0", (1.0, 3.0), (0.5, 0.5), seed=11, order=o); rows.append((o, ps.mean(), cd.mean()))
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk, cush_max=9000.0, stop_frac=0.5, order=o)
    life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), 100000, seed=21)
    r = run_chain(ps, cd, life, pday, pnet, n=30000, seed=5)
    P(f"- orden **{o}**: P(pasar, P0 mezcla 1/3) = {ps.mean() * 100:.1f} % · cobrado medio por XFA = ${pnet.sum(1).mean():,.0f} · P(≥1 pago) = {(pnet.sum(1) > 0).mean() * 100:.1f} % · neto anual por cuenta = ${r['net'].mean():,.0f}")
P("\n## 4. El «81.44 % teórico» que el scheduler muestra cada día — SÍ se reproduce, y es un artefacto del límite diario de pérdida (DLL)\n")
P("`THEORETICAL_PASS_RATE = 0.8144` (`scheduler/geometry_scheduler.py:145`) sale de `scripts/camino_b_grid.py` + `simulation/monte_carlo.py::TopstepMonteCarloSimulator` (SL 100 / TP 40, nc 40, `wr` de la medición de brackets, n_paths 8000, seed 42). **Reproducción con el código actual:**")
import dataclasses
sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import camino_b_grid as cbg
from simulation.monte_carlo import TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_50K
mesraw = __import__("pandas").read_parquet(os.path.join(os.path.dirname(os.environ["GLITCH_MGC_PARQUET"]), "mes_5min_2y.parquet"))
wb = cbg.measure_wr_bracket(mesraw, 100, 40, 100)
wr_mid = (wb["wr_all_opt"] + wb["wr_all_cons"]) / 2
P(f"- WR del bracket SL 100 / TP 40 con entrada en **cualquier barra** (no solo 9:35): optimista {wb['wr_all_opt']:.4f}, conservador {wb['wr_all_cons']:.4f} (la regla de empate no importa); `wr_mid` = {wr_mid:.4f}.")
d = cbg.ExactDayDist(wr_mid, 40 * 1.25 * 40, 100 * 1.25 * 40, 1.22 * 40, 1)
for lab, spec in (("con el DLL de $1,000 que aplica el simulador (`day_pnl < −DLL ⇒ −DLL`)", TOPSTEP_50K), ("sin DLL (la cuenta real no lo tiene: NO VERIFICADO en TopstepX)", dataclasses.replace(TOPSTEP_50K, daily_loss_limit=10 ** 9))):
    r = TopstepMonteCarloSimulator(d, spec, n_paths=8000, max_days=15, seed=42).run()
    P(f"- Simulador legado {lab}: **P(pasar) = {r.pass_rate * 100:.2f} %**, quiebra {r.n_blown / r.n_paths * 100:.1f} %.")
for o in ("adverse", "favorable"):
    ps, cd = combine_bank(mes, 100000, "P0", (0.0,), (1.0,), seed=11, maxdays=15, tp_ticks=40, sl_ticks=100, order=o)
    P(f"- **Motor actual** (MLL en tiempo real, liquidación a 40 ticks, 1 operación por día a las 9:35, slip 0, 15 días, orden {o}): **P(pasar) = {ps.mean() * 100:.1f} %** (con TP 32: ver §3).")
P("\n**Conclusión (hecho + inferencia marcada):** (1) el 81.44 % se reproduce **solo** con el DLL de $1,000 que recorta cada día perdedor de −$5,048 a −$1,000; sin él el simulador da ≈ 34 %. (2) El simulador además evalúa el piso al **cierre del día**, así que no ve la liquidación **intradía** a 40 ticks, y usa un `wr` ≈ 70 % de entradas en cualquier barra con SL de 100 ticks (que en tiempo real nunca se alcanza: la cuenta se liquida a −$2,000 = 40 ticks, y P(TP antes que liquidación) es ≈ 50 %, no 70 %). (3) Con las reglas reales el motor da **≈ 24 %** (TP 40) y **≈ 30 %** (TP 32). **El mensaje diario «Pass rate empírico vs 81.4 % teórico» compara contra un número inalcanzable: engañoso; no usarlo como criterio de graduación.** (Inferencia: la cuenta no tiene DLL; si Topstep lo impusiera —p. ej. bajo RTP— el cálculo cambiaría.)\n")
P("## 5. Reproducibilidad de `economia_historial_cifras_24oct2026.md`\n")
P("**No tengo ese documento (vive en el Project; no es legible desde aquí): no pude marcar fila por fila. REQUIERE HUMANO: pegarlo o subirlo.** Lo que sí puedo decir de las cifras que yo produje (todas reproducibles con un comando de `experimentos/`, semillas fijas): 47.4 % [41.0, 54.1] y TP/SL/FLATTEN (`f2_datos_limpios.py`), P(pasar) por slip (`g1_ejecucion.py`, `h0_mapa.py`), pagos por XFA y equilibrios (`value_wr.py`, `desglose_valor.py`, `h1_equilibrio.py`), +$1.0–1.5k de palancas (`xfa/run_partD*.py`). **Las cifras de motores anteriores a la Parte A (TP 32 «+7.1 pp», 17–29 %, 81.44 %) las dejo de usar salvo que se reproduzcan.** El «+7.1 pp» del TP 32 sale de `REPORT_TP32_COSTS_2ACCOUNTS_2026-10-09.md` (rama `research/firm-map-and-labs`, motor `dd_cash`: empate ⇒ adverso, conservador); no lo recalculé aquí.")
open(os.path.join(HERE, "resultados_H8.md"), "w", encoding="utf-8").write("\n".join(out))
