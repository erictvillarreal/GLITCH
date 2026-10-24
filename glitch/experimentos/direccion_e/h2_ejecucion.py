"""Parte H, H2: ruido por demora, estacionalidad intradía de rango/volumen/proxy de costo, plan de medición. Sin inventar datos de libro de órdenes. -> resultados_H2.md
    GLITCH_MGC_PARQUET=... python h2_ejecucion.py"""
import math, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
DC = os.path.dirname(os.environ["GLITCH_MGC_PARQUET"])
PR = {"MES": ("mes_5min_2y", 0.25, 1.25, 40, 9 * 60 + 35), "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 3, 7 * 60 + 15)}
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_H2 — ejecución ampliada: demoras, hora del día, salidas y plan de medición\n")
data = {}
for k, (stem, tick, tv, nc, e_m) in PR.items():
    d = pd.read_parquet(os.path.join(DC, stem + ".parquet")).tz_convert("America/Chicago"); d["date"] = d.index.date; d["m"] = d.index.hour * 60 + d.index.minute
    keep = []
    for dt_, x in d.groupby("date"):
        if "contract" in x.columns and x.contract.nunique() > 1: x = x[x.contract == x.groupby("contract")["volume"].sum().idxmax()]
        keep.append(x)
    d = pd.concat(keep); d["ret"] = d.groupby("date")["close"].diff() / tick; d["rng"] = (d["high"] - d["low"]) / tick
    h, l = d["high"], d["low"]; hp, lp = h.groupby(d["date"]).shift(1), l.groupby(d["date"]).shift(1)
    beta = np.log(h / l) ** 2 + np.log(hp / lp) ** 2; gam = np.log(np.maximum(h, hp) / np.minimum(l, lp)) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / (3 - 2 * math.sqrt(2)) - np.sqrt(gam / (3 - 2 * math.sqrt(2)))
    cs = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha)); d["cs"] = np.maximum(cs, 0) * d["close"] / tick            # proxy en ticks (estimador de Corwin-Schultz, NO es spread observado)
    data[k] = d
P("## 1. Ruido de precio durante una demora (media cero ⇒ no es costo esperado; sí es dispersión del fill respecto de la referencia)\n")
P("σ de un cambio de precio en τ segundos ≈ σ(5 min) × √(τ/300), con σ(5 min) = desvío de los cambios de cierre a cierre de barras de 5 min **en la franja de entrada** (supuesto de caminata aleatoria dentro de la barra; **no hay ticks**). En ticks y en dólares de la posición (MES: 40 contratos, $50/tick; MGC: 3 micros, $3/tick).\n")
P("| producto | franja | σ(5 min) ticks | τ = 1 s | 3 s | 10 s | 30 s | 60 s | 120 s (sondeo del Pi) |\n|---|---|---|---|---|---|---|---|---|")
for k, (stem, tick, tv, nc, e_m) in PR.items():
    d = data[k]; w = d[(d.m >= e_m) & (d.m < e_m + 30)]; s5 = float(w["ret"].std())
    P(f"| {k} | {e_m // 60}:{e_m % 60:02d}–{(e_m + 30) // 60}:{(e_m + 30) % 60:02d} CT | {s5:.1f} | " + " | ".join(f"{s5 * math.sqrt(t / 300):.1f} t (${s5 * math.sqrt(t / 300) * tv * nc:,.0f})" for t in (1, 3, 10, 30, 60, 120)) + " |")
P("\nLectura (corregida tras ver la tabla): con σ(5 min) ≈ 24 ticks en la franja de entrada, **una demora de 1–3 s ya implica una dispersión de ±1.4–2.4 ticks (1σ) y 10 s ±4.4**; el sondeo de 120 s (±15 ticks) **no se paga en el slippage** porque la referencia se toma cuando el Pi actúa (solo desplaza la hora). Los +1 y +3 ticks observados son del orden de 1σ de una demora de 1–3 s: **son compatibles con ruido puro, sin costo sistemático**; la probabilidad de que dos fills salgan los dos adversos con media cero es 25 %. Con N = 2 no se separa ruido de costo (**sin potencia**), pero el orden de magnitud dice que **la dispersión por demora (≈ ±2 ticks) es mayor que el costo sistemático esperado (≈ 0.5 tick de medio spread: SUPUESTO)**: el slippage que mueve P(pasar) es, sobre todo, aleatorio.\n")
P("## 2. Hora del día (proxy; no hay libro de órdenes)\n")
P("Rango mediano de una barra de 5 min, volumen mediano por barra, proxy de costo de Corwin-Schultz (**estimado con H/L de barras de 5 min; sobreestima y es ruidoso: sirve para el perfil relativo en U, no para el nivel**) y qué parte de la barra serían nuestros contratos.\n")
for k, (stem, tick, tv, nc, e_m) in PR.items():
    d = data[k]; P(f"**{k}** ({nc} contratos)\n\n| franja CT | rango 5 min (ticks) | volumen por barra | proxy de costo CS (ticks) | nuestros contratos / volumen de la barra |\n|---|---|---|---|---|")
    for a in range(7 * 60 if k == "MGC" else 8 * 60 + 30, 15 * 60, 60):
        w = d[(d.m >= a) & (d.m < a + 60)]
        if len(w) > 200: P(f"| {a // 60}:{a % 60:02d}–{(a + 60) // 60}:{(a + 60) % 60:02d} | {w['rng'].median():.1f} | {w['volume'].median():,.0f} | {w['cs'].median():.2f} | {nc / w['volume'].median() * 100:.2f} % |")
    P("")
P("Lectura: el patrón en U se ve en volumen y rango (alto en la apertura, bajo al mediodía). El proxy de costo es mayor cuando el volumen es bajo. **Elegir otra hora de entrada no es una palanca de costo medible con estos datos** (la Parte A y P5/P6 de H3 tampoco encuentran efecto en P(pasar)).\n")
P("## 3. Salidas y liquidación (lo que se sabe y lo que no)\n")
P("- **SL (orden stop):** se convierte en orden de mercado al tocarse; el slippage de salida **no está medido** (SUPUESTO 3 ticks en las Partes A–G). En MES con nc 40 el SL de 100 ticks **nunca se alcanza**: la liquidación por MLL ocurre a 40 ticks (hecho de la simulación: SL 0.0 %, LIQ 43–49 % de los días, `resultados_H0.md`).\n- **TP (orden límite):** se llena si el precio lo toca; fills parciales o espera en cola: **DESCONOCIDO** (no hay un solo TP con detalle de fill en este repo). Modelo: llena al precio de la orden.\n- **FLATTEN 14:30 CT (`closeContract`, mercado):** MES casi no lo usa (0.2 % de los días); en MGC 56 %. Slippage de salida **no medido**; su media es ≈ costo de medio spread.\n- **Liquidación por MLL en tiempo real:** Topstep liquida con órdenes de mercado y «el slippage de salida no lo deshace» (`RULEBOOK_XFA.md` 1.3, hecho leído el 20-oct). El sobreimpulso (cuánto más allá del piso se cierra) **no cuesta efectivo**: la cuenta se cierra de todos modos (en el motor la pérdida es exactamente el colchón); solo importaría para una XFA con saldo sobre el piso. **Caso real del 19-oct: no tengo el precio de salida; DESCONOCIDO** — hace falta el historial de operaciones de TopstepX (precio y hora de la salida) para medir el sobreimpulso.\n- **Parche:** `c3_slippage_timing.patch` (actualizado en la Parte H) registra también `exec_exit` (precio de salida frente al disparador, en ticks adversos).\n")
P("## 5. ¿Cuánto vale anclar al fill si el slippage es sobre todo ruido? (M1: el precio se movió; media cero; σ de la tabla 1)\n")
sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC as MG, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
mes_ = load_days(); cl_ = mgc_days(True); mk_ = gold_mask(cl_, True)
life, pday, pnet = xfa_bank(BarDays(cl_, MG["tick_usd"], MG["fee"], 364, 364, slip=(0.0,), mask=mk_, cush_max=9000.0, stop_frac=0.5), Rules(), pol_fixed(3, 364, 364), 100000, seed=21)
grid = list(range(-8, 9)); res5 = {}
for pol in ("P0", "P3"):
    for s in grid:
        ps, cd = combine_bank(mes_, 100000, pol, (0.0,), (1.0,), seed=11, sl_ticks=100 - s, tp_ticks=32 - s)       # M1: TP a 32 − s del fill, la liquidación sigue a 40
        res5[(pol, s)] = (ps.mean(), run_chain(ps, cd, life, pday, pnet, n=30000, seed=5)["net"].mean())
P("| σ del slippage aleatorio (ticks) | política | E[P(pasar)] hoy (anclado a la referencia) | E[P(pasar)] anclado al fill (= slip 0) | E[neto $/año] hoy | E[neto $/año] anclado | **valor del anclaje $/año/cuenta** |\n|---|---|---|---|---|---|---|")
for sg in (1.4, 2.4, 4.4):
    w = np.array([math.exp(-0.5 * ((s) / sg) ** 2) for s in grid]); w /= w.sum()
    for pol in ("P0", "P3"):
        ep = sum(wi * res5[(pol, s)][0] for wi, s in zip(w, grid)); en = sum(wi * res5[(pol, s)][1] for wi, s in zip(w, grid))
        P(f"| {sg} | {pol} | {ep * 100:.1f} % | {res5[(pol, 0)][0] * 100:.1f} % | ${en:,.0f} | ${res5[(pol, 0)][1]:,.0f} | **{res5[(pol, 0)][1] - en:+,.0f}** |")
P("\n(σ = 1.4 ≈ demora de 1 s; 2.4 ≈ 3 s; 4.4 ≈ 10 s.) **Estado: MODELADO con σ derivada de volatilidad de 5 min, no de fills; SUPUESTO de media cero.** Si el slippage es sobre todo ruido de media cero, anclar al fill (envío del TP/SL tras conocer el fill, o brackets nativos con ticks desde el fill) vale **$55–$657/año/cuenta según σ y política**: cruza el piso de $500 solo con σ ≥ 2.4 ticks y sin finish-line; con finish-line vale $55–$304. **Corrige a la baja** el +$1.5k de G1c, que suponía slippage adverso FIJO de 2–3 ticks (sistemático); el valor real depende de cuánto del slippage sea sistemático (C3 lo mide). Hace falta C3 para confirmar la σ real.\n")
P("## 6. Plan de medición (qué registrar y cuántos fills)\n")
P("| objetivo | qué registrar | σ supuesta (ticks) | fills para IC95 de ±0.5 tick en la media | estado |\n|---|---|---|---|---|")
for sg in (1.0, 2.0, 3.0): P(f"| media del slippage de entrada | `ref_price`, `fill_price`, `slip_ticks`, `t_ref_bar`, `t_send`, `t_fill`, `nc` | {sg:g} | {math.ceil((1.96 * sg / 0.5) ** 2)} | σ es SUPUESTO (N = 2) |")
P("| separar sistemático de aleatorio | lo anterior en **tamaños distintos** (nc 10 vs 40) y la dispersión vs `lat_ref_to_send_ms` | — | ≥ 30 por tamaño (≈ 60 sesiones en total) | sin datos de nc 10 en mano (Eric los tiene en TopstepX) |")
P("| slippage de salida (SL/FLATTEN/liquidación) | `exec_exit` (precio de salida, disparador, tipo) | 2–4 (supuesto) | 60–250 por tipo (los SL y las liquidaciones son raros: ≈ 1 de cada 2 días en MES) | `exec_exit` es nuevo en el parche |")
P("\nA ≈ 1 entrada por día hábil, 62 fills son ≈ 3 meses de calendario (4 meses con el calendario de feriados); 138 fills ≈ 6–7 meses. **La fuente más rápida es el historial de TopstepX que Eric exporte (MES nc 10 y 40, MEStest, MGC desde el 5-oct) cruzado con los `[OPEN]` de Telegram.**")
open(os.path.join(HERE, "resultados_H2.md"), "w", encoding="utf-8").write("\n".join(out))
