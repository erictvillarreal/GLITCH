"""Parte F, F3: economía del slippage de ENTRADA en el Combine de MES (nc 40, TP 32, SL 100, piso $2,000) con TP/SL anclados a la referencia. -> resultados_F3_slippage.md
    python f3_slippage.py"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank
from daydata import load_days, sim_day
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); NC, TV, FEE = 40, 1.25, 1.22; TP, CUSH = 32, 2000.0; LIQ = CUSH / (NC * TV)     # ticks de liquidacion desde el FILL = 40
P("# resultados_F3_slippage — slippage de entrada en MES (nc 40, TP 32 desde la REFERENCIA, SL 100, liquidación a 40 ticks del fill por el MLL de $2,000)\n")
P(f"{mes.D} días reales (ventana 9:30 → 14:30 CT). Convención: slip > 0 = fill peor que la referencia (adverso); slip < 0 = fill mejor (a favor). Salida del SL con 3 ticks de gap (convención de las partes A–D). Cada tick por contrato vale ${TV}; con 40 contratos, **1 tick = $50**.\n")
P("## 1. Aritmética exacta (sin simulación)\n")
P("| slip (ticks) | TP medido desde el fill | $ neto por TP (40 ctr.) | ¿2 TP alcanzan $3,000? | P(TP antes que liquidación) si el precio fuera martingala desde el fill = 40/(40 + TP) |\n|---|---|---|---|---|")
for s in (-2, -1, 0, 1, 2, 3, 4):
    u = TP - s; net = u * TV * NC - FEE * NC
    P(f"| {s:+d} | {u} | ${net:,.2f} | {'sí' if 2 * net >= 3000 else 'no'} (2 TP = ${2 * net:,.1f}) | {LIQ / (LIQ + u) * 100:.1f} % |")
P("\nLectura: el slippage adverso **acorta** la distancia al TP (más probable tocarlo) y **reduce** lo que paga; con la liquidación a 40 ticks del fill, la probabilidad de TP sube ≈ +0.8 pp por tick, y el dólar por TP baja $50 por tick. Con ≥ 2 ticks adversos, dos TP ya no suman $3,000 (acantilado: hacen falta tres).\n")
P("## 2. Días reales, dos modelos del slippage (motor de las Partes A–D)\n")
P("**M1 — el precio SE MOVIÓ antes del fill (ruido de precio, media cero):** el camino real sigue desde el fill; el TP queda a 32 − s ticks del fill, la liquidación a 40. **M2 — costo de ejecución puro:** el camino real no cambia (empieza en la referencia), el fill es s ticks peor: el TP sigue a 32 desde la referencia pero paga 32 − s, y la liquidación queda a 40 − s de la referencia.\n")
P("| slip | M1: TP % | M1: P&L/día (L / C) | M1: P(pasar) | M2: TP % | M2: P&L/día (L / C) | M2: P(pasar) |\n|---|---|---|---|---|---|---|")
rows = {}
for s in (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0):
    m1 = [sim_day(mes, sd, NC, CUSH, slip=0.0, exit_slip=3.0, sl=int(100 + s), tp=int(TP - s), fee=FEE, tick_usd=TV) for sd in (1, -1)]
    m2 = [sim_day(mes, sd, NC, CUSH, slip=s, exit_slip=3.0, sl=100, tp=TP, fee=FEE, tick_usd=TV) for sd in (1, -1)]
    pw1 = combine_bank(mes, 100000, "P0", (0.0,), (1.0,), seed=11, sl_ticks=int(100 + s), tp_ticks=int(TP - s))[0].mean()
    pw2 = combine_bank(mes, 100000, "P0", (s,), (1.0,), seed=11)[0].mean()
    f = lambda m: (np.mean(np.r_[m[0][0], m[1][0]] == 0), m[0][1].mean(), m[1][1].mean())
    (t1, l1, c1), (t2, l2, c2) = f(m1), f(m2); rows[s] = (t1, (l1 + c1) / 2, pw1, t2, (l2 + c2) / 2, pw2)
    P(f"| {s:+.0f} | {t1 * 100:.1f} | ${l1:+,.0f} / ${c1:+,.0f} | {pw1 * 100:.1f} % | {t2 * 100:.1f} | ${l2:+,.0f} / ${c2:+,.0f} | {pw2 * 100:.1f} % |")
r0, r3 = rows[0.0], rows[3.0]
P(f"\nEntre 0 y 3 ticks adversos, por tick: **M1** P(TP) {(r3[0] - r0[0]) / 3 * 100:+.2f} pp, P&L medio/día {(r3[1] - r0[1]) / 3:+,.1f} $, P(pasar) {(r3[2] - r0[2]) / 3 * 100:+.1f} pp · **M2** P(TP) {(r3[3] - r0[3]) / 3 * 100:+.2f} pp, P&L medio/día {(r3[4] - r0[4]) / 3:+,.1f} $, P(pasar) {(r3[5] - r0[5]) / 3 * 100:+.1f} pp.")
P("\n## 3. Cómo se interpreta (hechos vs supuestos)\n")
P("- **Hecho (resultado):** los **dólares por TP bajan $50 por tick adverso en ambos modelos** (parte de tu hipótesis, confirmada). **P(TP) sube con el slippage adverso solo en M1** (el precio se movió y el TP quedó más cerca del fill) y **baja en M2** (costo puro: la liquidación queda más cerca y el camino no cambia). Así que ‘sube P(TP)’ es cierto para el slippage que es movimiento de precio y falso para el que es costo de ejecución. Para el lado favorable es simétrico.")
P("- **Qué es el slippage observado (3 ticks el martes 20-oct, ≈ 1 el lunes 19):** el Pi toma como referencia el cierre de la última barra de ProjectX de los últimos 15 min (`_reference_price`) y el fill ocurre segundos después. Parte de la diferencia es **movimiento del precio** (media cero, p. ej. 1 minuto de volatilidad a las 9:35) y parte es **costo de ejecución** (medio spread + impacto de 40 contratos, > 0). **No está medida la mezcla**: con N = 2 no se puede separar (NO VERIFICADO). Si fuera solo ruido de precio, el EV por trade no cambia y solo cambia la forma del pago (acantilado); si fuera costo, cada tick adverso cuesta ≈ $50 por trade.")
P("- **Orden límite ‘marketable’ / tolerancia (tope de k ticks adversos; si no llena, no hay trade ese día):** convierte la distribución de slippage en una truncada. Ventaja: nunca se opera con TP efectivo < 32 − k (con k = 1 siempre alcanzan 2 TP, $3,002.4 > $3,000). Costo: días sin operar (el Combine cuesta ≈ $49/mes, no hay límite de días) y el riesgo de no llenar justo en los días de movimiento fuerte a favor del lado jugado. **No se puede cuantificar sin la distribución de slippage**: falta el registro (parche C3).")
P("- **Prioridad:** (1) **C3** (registro de `ref_price`, `fill_price`, `slip_ticks` por sesión): sin 20–30 sesiones no hay ni la media ni la dispersión. (2) Solo después decidir entre tolerancia / límite / anclar el bracket al fill. Anclar al fill (colocar TP/SL tras conocer el fill) elimina el acantilado pero deja una ventana sin protección de segundos: la propia regla de diseño del Pi (‘entrada y protección juntas’) lo impide; requiere revisión humana.")
open(os.path.join(HERE, "resultados_F3_slippage.md"), "w").write("\n".join(out))
