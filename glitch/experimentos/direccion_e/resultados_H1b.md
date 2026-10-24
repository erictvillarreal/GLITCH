# resultados_H1b — H1 rehecho: slippage empírico (7 obs.), costos operativos A/B/C y cascada sin «costos → $0»

**Fuentes y estado.** Slippage de entrada: 7 valores (0, +1, 0, +3, −1, +1, +3 ticks) **entregados por Eric en el chat**; no los puedo rastrear a un CSV de TopstepX (faltan fecha, lado, tamaño nc 10/40 y hora): **NO VERIFICADOS**. Media +1.00 tick, desvío 1.53, IC95 de la media (t de Student, 6 gl) [−0.41, +2.41]; P(adverso ≥ 2) = 2/7 = 29 % [IC exacto 4 %–71 %]. **N = 7: sin potencia para distinguir una media de 0, 1 o 2 ticks.** Costos operativos: A = $240 ($174 de API por cuenta + ≈ $65 de Railway), B = $827 (A + la mensualidad del Combine de $49 × 12 aparte), C = lo que Eric confirme con facturas; el $714 anterior sale del encargo de la Parte D (`xfa/REPORTE_D.md:24`, `xfa/chain.py:18`), no de una factura. Convención de slippage: M2 (costo; `slip` de `OutcomeTable`), una realización por día del Combine con la distribución indicada.

Distribución empírica usada: -1: 14 %, +0: 29 %, +1: 29 %, +3: 29 %. Sensibilidad: mezcla {1, 3} 50/50 (la de H1 original). Hipótesis de tolerancia (solo en la cascada): los +3 pasan a +1.

## 1. Línea base (Combine P0 nc 40, XFA 3×364, stop 0.5; el resto como en H1)

| slippage del Combine | costos operativos | equilibrio de la cadena | neto/año a WR 50 % | valor de 1 pp (48→50 %) | P(pasar) cuenta nueva (WR 50 %) |
|---|---|---|---|---|---|
| empírica-7 | A ($240) | **47.47 %** | $2,629 | $1,038 | 24.9 % |
| empírica-7 | B ($827) | **48.03 %** | $2,042 | $1,038 | 24.9 % |
| mezcla {1,3} | A ($240) | **48.05 %** | $1,839 | $945 | 20.5 % |
| mezcla {1,3} | B ($827) | **48.67 %** | $1,252 | $945 | 20.5 % |

**Escenario C (facturas de Eric):** el neto es lineal en los costos: cada **$100/año** de costos operativos mueve el equilibrio **+0.10 pp** y el neto −$100 (pendiente local $1,038/pp). Equilibrio(C) = equilibrio(A) + (C − 240) / $1,038 pp; ejemplos: C = $500 → 47.72 %, C = $1,000 → 48.20 %.

## 2. Cada componente por separado (los demás en la línea base). Equilibrio bajo costos A y B; Δ vs la línea base con A

| grupo | componente | equilibrio (A) empírica-7 | Δ pp | Δ $/año a WR 50 % | equilibrio (B) | equilibrio (A), mezcla {1,3} | Δ pp (mezcla) |
|---|---|---|---|---|---|---|---|
| Combine | reset $49 → $0 (cota teórica) | 44.65 % | -2.81 | +2,351 | 45.28 % | 44.78 % | -3.27 |
| Combine | reset $49 → $98 | 49.76 % | +2.29 | -2,351 | 50.27 % | 50.66 % | +2.61 |
| Combine | activación $149 → $0 | 45.69 % | -1.78 | +1,771 | 46.26 % | 46.37 % | -1.68 |
| Combine | slip de entrada del Combine = 4 ticks fijos | 48.91 % | +1.45 | -1,701 | 49.60 % | — | — |
| Combine | slip de entrada del Combine = 3 ticks fijos | 48.68 % | +1.21 | -1,474 | 49.35 % | — | — |
| Combine | slip de entrada del Combine = 2 ticks fijos | 48.53 % | +1.06 | -1,318 | 49.19 % | — | — |
| XFA | tamaño 4→1 micros (cobro ≥ $1,500) | 46.52 % | -0.95 | +627 | 47.15 % | 47.21 % | -0.85 |
| XFA | tamaño 728×3 (SL = TP = 728) | 46.80 % | -0.67 | +1,476 | 47.26 % | 47.32 % | -0.73 |
| Combine | comisión MES $1.22 → $2.44 | 47.96 % | +0.49 | -660 | 48.57 % | 48.58 % | +0.53 |
| Combine | slip de entrada del Combine = 0 ticks fijos | 46.98 % | -0.49 | +744 | 47.50 % | — | — |
| XFA | slip de entrada MGC = 4 ticks (base 0) | 47.95 % | +0.49 | -659 | 48.56 % | 48.58 % | +0.52 |
| Combine | slip adverso acotado a ≤ 1 tick (los +3 pasan a +1; hipotético) | 47.00 % | -0.47 | +699 | 47.53 % | — | — |
| XFA | stop exacto en lugar de 0.5 | 47.03 % | -0.44 | +828 | 47.53 % | 47.56 % | -0.49 |
| Combine | slip de entrada del Combine = 1 ticks fijos | 47.03 % | -0.43 | +636 | 47.57 % | — | — |
| Combine | finish-line (P3) en lugar de 40 fijos | 47.11 % | -0.36 | +480 | 47.65 % | 47.26 % | -0.79 |
| Combine | comisión MES $1.22 → $0 (cota teórica) | 47.11 % | -0.36 | +535 | 47.65 % | 47.37 % | -0.69 |
| XFA | slip de entrada MGC = 3 ticks (base 0) | 47.82 % | +0.35 | -495 | 48.42 % | 48.43 % | +0.38 |
| XFA | slip de entrada MGC = 2 ticks (base 0) | 47.70 % | +0.23 | -328 | 48.29 % | 48.30 % | +0.25 |
| XFA | comisión MGC $1.92 → $3.84 | 47.67 % | +0.21 | -289 | 48.26 % | 48.27 % | +0.22 |
| XFA | comisión MGC $1.92 → $0 | 47.29 % | -0.18 | +313 | 47.83 % | 47.86 % | -0.20 |
| XFA | slip de entrada MGC = 1 ticks (base 0) | 47.59 % | +0.12 | -170 | 48.16 % | 48.18 % | +0.13 |
| XFA | slip de salida MGC 0 → 3 ticks | 47.51 % | +0.04 | -73 | 48.08 % | 48.10 % | +0.05 |
| Combine | slip de salida del SL/liquidación 3 → 6 ticks | 47.47 % | +0.00 | +0 | 48.03 % | 48.05 % | +0.00 |

Las filas «→ $0», «$0» y «duplicada» son cotas teóricas, no palancas (las tarifas las fijan Topstep/CME). Los costos operativos **ya no aparecen como palanca**: son un escenario (sección 1).

## 3. Cascada acumulada (sin «costos operativos → $0»; el equilibrio se recalcula con la cadena completa)

| paso | equilibrio con costos A | con costos B | Δ pp (A) | neto/año a WR 50 % (A) | valor de 1 pp aquí |
|---|---|---|---|---|---|
| hoy (P0, 3×364, slip empírico) | 47.47 % | 48.03 % |  | $2,629 | $1,038 |
| + finish-line | 47.11 % | 47.65 % | -0.36 | $3,109 | $1,074 |
| + 728×3 | 46.47 % | 46.92 % | -0.63 | $4,676 | $1,326 |
| + slip adverso acotado a ≤ 1 tick (hipotético) | 46.35 % | 46.78 % | -0.12 | $4,965 | $1,361 |

Primer paso (acumulado) que baja el equilibrio por debajo de **47.4 %**: con costos A → + finish-line; con costos B → + 728×3. Por debajo de **46.5 %**: con A → + 728×3; con B → ninguna.

Sensibilidad (mezcla {1,3} en lugar de la empírica; costos A): hoy 48.05 % → + finish-line 47.26 % → + 728×3 46.63 %.