# resultados_J5 — intervalo del «+$206» (H6 §2.5) y cascada rehecha

**Fuentes y estado.** MODELADO sobre días reales de 5 min (MES 492 días para el Combine; MGC 443 días sin la ventana de oro para la XFA). Slippage de entrada del Combine = distribución empírica de 8 observaciones {−1: 1/8, 0: 3/8, +1: 2/8, +3: 2/8} (7 dadas por Eric + una 8.ª **inferida = 0** a partir de «media 0.9, N=8»: **NO VERIFICADA**); slippage de entrada MGC 0 (no medido), stop 0.5, comisión MES $1.22 y MGC $1.92, OPS $245/año. Neto anual por cuenta = efectivo cobrado − tarifas − OPS, horizonte 252 días hábiles (`xfa/chain.py`).
IC95 = percentiles 2.5–97.5 de 30 remuestras de bloques de 5 días de la historia real (cada una con 30,000 intentos y vidas); cuenta lo incierto del conjunto de días, **no** el cambio de régimen, **no** la distribución real de slippage, **no** la etiqueta de WR.

## 1. Neto anual por cuenta ($, OPS $245) y su intervalo

| configuración | WR 47.4 % (≈ el medido) | WR 50 % |
|---|---|---|
| hoy (P0, 3×364) | $-145 [-356, 319] | $2,543 [2,336, 2,939] |
| + finish-line (P3, 3×364) | $188 [-9, 701] | $2,981 [2,786, 3,417] |
| P0 + 728×3 | $319 [96, 991] | $4,051 [3,836, 4,563] |
| finish-line + 728×3 | $702 [470, 1,421] | $4,585 [4,372, 5,098] |

## 2. Diferencias pareadas (misma remuestra de días) frente a «hoy»

| configuración | Δ a WR 47.4 % [IC95] | ¿IC excluye 0? | Δ a WR 50 % [IC95] | ¿IC excluye 0? |
|---|---|---|---|---|
| + finish-line (P3, 3×364) | $+334 [+319, +385] | SÍ | $+438 [+415, +496] | SÍ |
| P0 + 728×3 | $+464 [+106, +952] | SÍ | $+1,507 [+1,109, +1,833] | SÍ |
| finish-line + 728×3 | $+848 [+488, +1,354] | SÍ | $+2,041 [+1,651, +2,359] | SÍ |

**Respuesta al «+$206»:** el valor de H6 (finish-line + 728×3, WR 47.4 %, slippage {1,3}, OPS $714) era un solo número sin intervalo. Rehecho con el slippage empírico de 8 observaciones y OPS $245: **$702 [470, 1,421]**; la fracción de remuestras con neto > 0 es 100 %. La diferencia con $206 combina (i) OPS $714 → $245 (+$469/año) y (ii) el slippage empírico (media 0.9 ticks en vez de 2) y (iii) ruido de simulación; no se separó cada parte.
