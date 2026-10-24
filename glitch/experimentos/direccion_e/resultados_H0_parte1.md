# resultados_H0 — mapa de probabilidades (Parte H)

IC95 = percentiles 2.5–97.5 de **20** remuestras (modo `--quick`; con 20 el IC es aproximado y tiende a ser algo ancho; `python h0_mapa.py` sin `--quick` usa 100 y tarda ≈ 1 h) de la HISTORIA REAL (bloques de 5 días; MGC 488 días limpios, MES 492 días), cada una con su banco de 20,000 intentos/vidas. Cuenta lo incierto del conjunto de días, **no** lo incierto del futuro (cambio de régimen). Estados: MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO.

## Filas 1–2. MGC (3 micros, SL = TP = 364 ticks, 7:15→14:30 CT, datos limpios de contrato; FLATTEN = cierre a las 14:30 sin tocar barrera)

| regla | TP % | SL % | FLATTEN % | WR_dec = TP/(TP+SL) | N | estado |
|---|---|---|---|---|---|---|
| alternate | 20.9 % [17.7, 24.5] | 23.2 % [19.6, 27.4] | 55.9 % [49.2, 59.6] | **47.4 % [41.1, 54.0]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |
| siempre LARGO | 20.3 % [17.2, 23.6] | 23.8 % [21.0, 28.2] | 55.9 % [49.2, 59.6] | **46.0 % [40.7, 51.7]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |
| siempre CORTO | 23.8 % [21.0, 28.2] | 20.3 % [17.2, 23.6] | 55.9 % [49.2, 59.6] | **54.0 % [48.3, 59.3]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |

WR_todos = TP/n (FLATTEN como no-ganador) = la columna TP %. WR_signo y WR_pnl: ver `resultados_F2.md`. En LARGO y CORTO FLATTEN cuenta igual: queda fuera del denominador de WR_dec.

## Fila 1b. MES (nc 40, TP 32, SL 100 pero **la liquidación por MLL ocurre a 40 ticks**; ventana 9:35→14:30 CT)

| slip de entrada | lado | TP % | SL % | **LIQ (MLL) %** | FLATTEN % | estado |
|---|---|---|---|---|---|---|
| 0 | LARGO | 52.8 % [48.5, 56.3] | 0.0 % [0.0, 0.0] | 47.2 % [43.7, 51.5] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 0 | CORTO | 56.7 % [54.2, 59.3] | 0.0 % [0.0, 0.0] | 42.9 % [40.3, 45.2] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 1 | LARGO | 51.8 % [48.3, 54.8] | 0.0 % [0.0, 0.0] | 48.2 % [45.2, 51.7] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 1 | CORTO | 56.1 % [53.7, 58.8] | 0.0 % [0.0, 0.0] | 43.5 % [40.8, 45.7] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 3 | LARGO | 50.8 % [47.0, 53.8] | 0.0 % [0.0, 0.0] | 49.2 % [46.2, 53.0] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 3 | CORTO | 54.7 % [52.0, 57.7] | 0.0 % [0.0, 0.0] | 44.9 % [41.8, 47.7] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |

## Fila 3. Un día del Combine con nc 40 desde el estado actual (balance $51,401.20, piso $49,401.20 ⇒ colchón $2,000; lado de lunes 26-oct = LARGO)

El colchón es el de una cuenta nueva ($2,000): la probabilidad de TP/liquidación de UN día es la de la tabla anterior (LARGO). Lo que cambia con el estado es **pasar** (fila 4).

## Filas 4–5. P(pasar el Combine) y duración, nc 40 fijo (P0) y finish-line (P3); slip 0–4 ticks (M2 = costo de ejecución; M1 = movimiento de precio)

| inicio | política | slip | M2 P(pasar) | M1 P(pasar) | días a resolver (media) | intentos esperados hasta pasar (1/p, M2) | estado |
|---|---|---|---|---|---|---|---|
| cuenta nueva | P0 | 0 | 29.9 % [29.1, 31.2] | 29.9 % [29.1, 31.2] | 1.55 | 3.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 1 | 29.0 % [27.8, 30.4] | 31.3 % [29.5, 32.6] | 1.54 | 3.4 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 2 | 18.0 % [16.6, 19.1] | 21.0 % [19.3, 22.7] | 1.83 | 5.6 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 3 | 17.2 % [15.9, 18.3] | 21.1 % [19.5, 22.4] | 1.81 | 5.8 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 4 | 16.1 % [15.5, 17.8] | 21.3 % [20.0, 23.3] | 1.79 | 6.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 0 | 29.9 % [29.0, 31.9] | 29.9 % [29.0, 31.9] | 1.55 | 3.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 1 | 29.0 % [27.6, 29.9] | 31.3 % [30.1, 32.3] | 1.54 | 3.4 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 2 | 27.0 % [26.2, 29.6] | 30.5 % [29.0, 32.9] | 1.93 | 3.7 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 3 | 25.2 % [24.0, 26.2] | 29.9 % [28.6, 31.6] | 1.89 | 4.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 4 | 23.0 % [21.4, 23.8] | 29.2 % [26.6, 30.3] | 1.93 | 4.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 0 | 35.6 % [32.7, 38.2] | 35.6 % [32.7, 38.2] | 1.54 | 2.8 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 1 | 34.0 % [32.7, 36.7] | 36.6 % [35.2, 39.6] | 1.53 | 2.9 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 2 | 33.4 % [31.5, 35.6] | 36.5 % [34.8, 38.6] | 1.53 | 3.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 3 | 32.6 % [30.2, 34.3] | 37.0 % [33.8, 38.8] | 1.52 | 3.1 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 4 | 31.4 % [29.5, 32.4] | 37.3 % [35.7, 38.9] | 1.51 | 3.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 0 | 51.5 % [47.8, 53.8] | 51.5 % [47.8, 53.8] | 1.72 | 1.9 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 1 | 49.4 % [46.9, 51.8] | 51.6 % [49.0, 54.2] | 1.71 | 2.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 2 | 47.7 % [44.8, 50.4] | 51.1 % [48.0, 55.0] | 1.68 | 2.1 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 3 | 46.2 % [41.7, 48.9] | 50.8 % [47.7, 53.2] | 1.66 | 2.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 4 | 43.8 % [40.4, 47.6] | 50.2 % [45.1, 53.7] | 1.75 | 2.3 | MODELADO (reglas oficiales; slip SUPUESTO) |