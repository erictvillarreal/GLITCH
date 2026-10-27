# resultados_K1_equilibrio — equilibrio de la cadena con los costos reales de Eric

**Fuente y estado.** MODELADO (motor de las Partes A/D; MES 492 días, MGC 443 días; 80,000 intentos y vidas por punto de la rejilla de WR, ruido de simulación ≈ ± $100 por celda). Costos anuales: los **totales** los dio Eric en el chat (recurrente GLITCH ≈ $54/mes ≈ $640/año; con Massive Futures sustituido ≈ $25/mes ≈ $290/año; $245 = base de la Parte J); **el desglose por rubro NO lo tengo** (SUPUESTO que el recurrente incluye Massive Futures Starter $29/mes, Railway, API de ProjectX). Los $49 por intento de Combine y los $149 de activación ya están dentro del motor. Slippage de entrada del Combine: 8 observaciones de MES (la 8.ª inferida = 0, NO VERIFICADA). La etiqueta de WR es la de H1 (deriva calibrada en el bracket nominal 364/364).

## Neto anual por cuenta ($) a WR 47.4 % y 50 %, según costos

| costos al año | hoy (P0, 3×364) (47.4 / 50 %) | + finish-line (47.4 / 50 %) | + 728×3 (47.4 / 50 %) | finish-line + 728×3 (47.4 / 50 %) |
|---|---|---|---|---|
| OPS heredado de la Parte D: $714 | $-520 / $2,165 | $-167 / $2,628 | $8 / $3,655 | $405 / $4,180 |
| recurrente GLITCH hoy ($54/mes): $640 | $-446 / $2,239 | $-93 / $2,702 | $82 / $3,729 | $479 / $4,254 |
| con Massive Futures sustituido ($25/mes): $290 | $-96 / $2,589 | $257 / $3,052 | $432 / $4,079 | $829 / $4,604 |
| base de la Parte J: $245 | $-51 / $2,634 | $302 / $3,097 | $477 / $4,124 | $874 / $4,649 |

## Equilibrio de la cadena (WR de la etiqueta con neto anual = 0)

| costos al año | hoy (P0, 3×364) | + finish-line | + 728×3 | finish-line + 728×3 |
|---|---|---|---|---|
| OPS heredado de la Parte D: $714 | 47.86 % | 47.50 % | 47.30 % | 47.03 % |
| recurrente GLITCH hoy ($54/mes): $640 | 47.78 % | 47.43 % | 47.25 % | 46.98 % |
| con Massive Futures sustituido ($25/mes): $290 | 47.44 % | 47.10 % | 47.00 % | 46.74 % |
| base de la Parte J: $245 | 47.39 % | 47.05 % | 46.96 % | 46.71 % |

Pendiente local (hoy): ≈ $992 por punto de WR ⇒ cada $100 de costos al año mueve el equilibrio ≈ 0.10 pp. De $714 a $290 el equilibrio baja ≈ 0.43 pp; de $640 a $290, ≈ 0.35 pp.

(El motor resta los costos como una constante anual; la API de ProjectX en realidad se cobra por cuenta **activa** y por mes: ver `RESULTADOS_K1.md`.)
