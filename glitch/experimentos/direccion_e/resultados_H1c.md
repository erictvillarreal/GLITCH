# resultados_H1c — H0-0 (P&L neto por sesión y definiciones de WR) y por qué 728×3 baja el equilibrio

## Parte 1 — H0-0: P&L neto por sesión y las definiciones de WR

**Fuente y estado.** Días reales de 5 min (MGC: 488 días limpios, contrato dominante; MES: 492 días) reproducidos con el motor de las Partes A/D (`sim_day`): MODELADO sobre historia real, **no** son las sesiones vivas (no tengo el CSV de TopstepX ni `geometry_mes_log.json`: las 8 sesiones reales de MES y las 3 de MGC Practice **no se pudieron cruzar**). P&L **neto de comisión** (MGC $1.92 y MES $1.22 por contrato round-turn), slip de entrada 0, stop de MGC llenado a 0.5 (convención C1), liquidación del Combine = pérdida exacta del colchón.

**Definiciones de WR** (cuatro; la quinta métrica es la que importa para el pago):
- **WR_dec = TP / (TP + SL + LIQ)**: solo sesiones que tocan una barrera; **FLATTEN queda fuera del denominador**. Es la del modelo de valor (la deriva se calibra para fijarla).
- **WR_todos = TP / n**: FLATTEN cuenta como no ganador.
- **WR_signo = P(cierre del flatten > referencia en el lado jugado)**: exactitud de dirección (E1–E5); no mira barreras.
- **WR_pnl = sesiones con P&L neto > 0 / sesiones con P&L ≠ 0**: FLATTEN cuenta por su signo.
- **Días ganadores ≥ $150 netos** (lo que mira el pago de la XFA Standard: 5 días ≥ $150, no consecutivos): fracción de sesiones con P&L neto ≥ +$150.


**MGC 3 micros, SL = TP = 364, entrada 7:15 CT, flatten 14:30 CT, slip de entrada 0 ticks**

| regla | n | P&L neto medio/sesión [IC95] | mediana | desvío | p10 – p90 | mejor / peor | ≥ +$150 (de ellas, FLATTEN) | ≤ −$150 | WR_dec | WR_todos | WR_signo | WR_pnl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alternate | 488 | $-47.9 [-117.0, +25.5] | $-19.3 | $826 | $-1,149 – $+1,086 | $+1,086 / $-2,404 | 43.0 % (51 %) | 43.2 % | **47.4 %** [40.8, 54.2] | 20.9 % | 50.0 % | 49.2 % |
| siempre LARGO | 488 | $-33.6 [-99.1, +37.2] | $+18.2 | $832 | $-1,182 – $+1,086 | $+1,086 / $-2,404 | 44.9 % (55 %) | 41.6 % | **46.0 %** [39.9, 52.4] | 20.3 % | 52.5 % | 50.8 % |
| siempre CORTO | 488 | $-19.7 [-85.7, +43.0] | $-29.8 | $814 | $-1,131 – $+1,086 | $+1,086 / $-1,731 | 41.4 % (43 %) | 45.3 % | **54.0 %** [47.6, 60.1] | 23.8 % | 47.5 % | 48.8 % |

**MES nc 40, TP 32, SL 100 (liquidación por MLL a 40 ticks), 9:35 → 14:30 CT, slip de entrada 0 ticks**

| regla | n | P&L neto medio/sesión [IC95] | mediana | desvío | p10 – p90 | mejor / peor | ≥ +$150 (de ellas, FLATTEN) | ≤ −$150 | WR_dec | WR_todos | WR_signo | WR_pnl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alternate | 492 | $+54.3 [-105.7, +189.7] | $+1,551.2 | $1,751 | $-2,000 – $+1,551 | $+1,551 / $-2,000 | 57.7 % (0 %) | 42.3 % | **58.0 %** [53.5, 61.8] | 57.7 % | 51.2 % | 57.7 % |
| siempre LARGO | 492 | $-123.3 [-282.1, +35.4] | $+1,551.2 | $1,773 | $-2,000 – $+1,551 | $+1,551 / $-2,000 | 52.8 % (0 %) | 47.2 % | **52.8 %** [48.4, 57.3] | 52.8 % | 55.1 % | 52.8 % |
| siempre CORTO | 492 | $+18.2 [-121.8, +166.7] | $+1,551.2 | $1,756 | $-2,000 – $+1,551 | $+1,551 / $-2,000 | 56.7 % (0 %) | 43.3 % | **56.9 %** [53.0, 61.2] | 56.7 % | 44.9 % | 56.7 % |

**MES nc 40, TP 32, SL 100 (liquidación por MLL a 40 ticks), 9:35 → 14:30 CT, slip de entrada 1 ticks**

| regla | n | P&L neto medio/sesión [IC95] | mediana | desvío | p10 – p90 | mejor / peor | ≥ +$150 (de ellas, FLATTEN) | ≤ −$150 | WR_dec | WR_todos | WR_signo | WR_pnl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alternate | 492 | $+3.8 [-156.9, +138.6] | $+1,501.2 | $1,729 | $-2,000 – $+1,501 | $+1,501 / $-2,000 | 57.1 % (0 %) | 42.9 % | **57.3 %** [52.7, 61.3] | 57.1 % | 51.2 % | 57.1 % |
| siempre LARGO | 492 | $-185.4 [-334.8, -35.7] | $+1,501.2 | $1,749 | $-2,000 – $+1,501 | $+1,501 / $-2,000 | 51.8 % (0 %) | 48.2 % | **51.8 %** [47.6, 56.1] | 51.8 % | 55.1 % | 51.8 % |
| siempre CORTO | 492 | $-31.7 [-171.1, +111.8] | $+1,501.2 | $1,734 | $-2,000 – $+1,501 | $+1,501 / $-2,000 | 56.1 % (0 %) | 43.9 % | **56.3 %** [52.3, 60.5] | 56.1 % | 44.9 % | 56.1 % |

Lectura (cifras de las tablas). **MGC (stop llenado a 0.5; con stop exacto, como en `resultados_F2.md`, la sesión media es ≈ $20 mejor):** la sesión media pierde $48 (`alternate`), $34 (LARGO) y $20 (CORTO), con IC95 que incluye 0; desvío ≈ $826 por sesión; 43 % de las sesiones llega a +$150 netos (de ellas, 51 % son FLATTEN) y 43 % cae a −$150 o peor. El peor día (−$2,404) es el stop con salto; con el colchón inicial de la XFA ($2,000) esa sesión sería una liquidación de −$2,000. **MES:** la sesión es binaria, +$1,551 (TP) o −$2,000 (liquidación); el P&L medio de `alternate` es +$54 (IC95 que incluye 0), de LARGO $-123 y de CORTO +$18: la diferencia entre lados es la deriva de la muestra, no una señal. WR_dec = WR_todos = WR_pnl en MES (no hay FLATTEN relevante). **WR_signo ≈ 50 % con `alternate` en las dos: no hay información de dirección.** Un slippage de 1 tick resta ≈ $50 por sesión.

## Parte 2 — ¿Por qué 728×3 baja el equilibrio 0.72 pp? ¿Se remidió el WR con esa geometría?

**Respuesta corta sobre la medición: NO se remidió.** En H1 (y en E §4, F1, G4, H6 §3) el eje «WR» es una **etiqueta**: la deriva en ticks/día se calibra **una sola vez** con `xfa/worlds.py::drift_for_wr(..., sl=364, tp=364)`, que simula el bracket nominal 364/364 con 1 contrato y colchón 10⁹ (sin MLL), y esa **misma deriva** se aplica a la geometría que se evalúe. El «equilibrio de 728×3 = 47.72 %» es, por tanto, «la deriva que equivale a 47.72 % en un bracket 364/364»; **no** es el WR_dec que se mediría operando 728×3. A continuación se remide.

### 2a. WR_dec remedido con cada geometría, a la misma deriva (etiqueta de WR en el eje)

`nominal` = bracket simétrico sin MLL, 1 contrato (lo que mide la etiqueta). `con MLL, colchón inicial $2,000` = 3 micros: la liquidación ocurre a **667 ticks** ($2,000 / $3) y el TP está a 728. `con MLL, colchón $2,178` = tras el 1.er TP (balance ≈ colchón ≈ $2,178): la liquidación está a ≈ 726 ticks, de nuevo casi simétrico. Cada celda es el WR_dec **por sesión** sobre los 443 días reales (ambos lados); n decididas pequeño en 3×728 ⇒ ruido de ± 4–5 pp. (No se usa la razón TP/decididas acumulada en vidas simuladas: está sesgada por la regla de parada, porque cada vida termina con una liquidación.)

| etiqueta de WR | geometría | nominal | con MLL, colchón inicial $2,000 | con MLL, colchón $2,178 | % de sesiones decididas (colchón $2,000) |
|---|---|---|---|---|---|
| 45.0 % | 3×364 | 45.1 % | 45.1 % | 45.1 % | 43 % |
| 45.0 % | 3×728 | 42.3 % | 38.5 % | 42.3 % | 14 % |
| 47.4 % | 3×364 | 47.5 % | 47.5 % | 47.5 % | 42 % |
| 47.4 % | 3×728 | 46.8 % | 42.1 % | 46.8 % | 14 % |
| 48.5 % | 3×364 | 48.5 % | 48.5 % | 48.5 % | 42 % |
| 48.5 % | 3×728 | 50.0 % | 44.8 % | 50.0 % | 14 % |
| 50.0 % | 3×364 | 50.0 % | 50.0 % | 50.0 % | 42 % |
| 50.0 % | 3×728 | 50.0 % | 45.2 % | 50.0 % | 14 % |
| 52.0 % | 3×364 | 51.9 % | 51.9 % | 51.9 % | 42 % |
| 52.0 % | 3×728 | 50.4 % | 46.3 % | 50.4 % | 14 % |

Lectura: en 3×364 la etiqueta se cumple (el MLL de 667 ticks no toca un bracket de 364). **En 3×728 el WR_dec por sesión con colchón $2,000 es ≈ 4–5 pp MENOR que la etiqueta** (liquidación a 667 < TP a 728: martingala ⇒ 667/(667+728) = 47.8 %; con tiempo finito, además, la barrera más cercana se toca más), y vuelve a ≈ la etiqueta tras el primer TP (colchón ≈ $2,178). **El 728×3 no baja el equilibrio por un WR mayor ni por simetría: su WR_dec real es peor que el de la etiqueta.**

### 2b. Qué cambia de verdad: composición de las vidas (a deriva = etiqueta 50 % y 48.5 %)

| etiqueta | geometría | sesiones decididas por vida (TP / SL / liquidación) | sesiones FLATTEN por vida | P(≥ 1 pago) | cobrado por XFA | vida media (días) | P(muere sin cobrar nada) |
|---|---|---|---|---|---|---|---|
| 50.0 % | 3×364 | 2.01 / 1.53 / 1.00 | 5.36 | 33.0 % | $647 | 9.9 | 67.0 % |
| 50.0 % | 3×728 | 0.66 / 0.27 / 1.00 | 8.81 | 28.1 % | $824 | 10.7 | 71.9 % |
| 48.5 % | 3×364 | 1.76 / 1.40 / 1.00 | 4.84 | 29.9 % | $508 | 9.0 | 70.1 % |
| 48.5 % | 3×728 | 0.56 / 0.19 / 1.00 | 7.43 | 25.3 % | $636 | 9.2 | 74.7 % |

### 2c. La medida comparable entre geometrías: deriva z* necesaria para neto anual = 0 (misma convención que H1: deriva en las dos etapas; slip empírico de 7 obs.; costos A $240) y WR_dec remedido en z*

| geometría | neto $/año a z = 0 (costos A) | z* (μ/σ de la sesión) | etiqueta de WR equivalente (bracket 364 nominal) | **WR_dec remedido en z*: colchón $2,000** | colchón $2,178 |
|---|---|---|---|---|---|
| 3×364 | $2,659 | -0.070 | 47.47 % | **47.47 %** | 47.47 % |
| 3×728 | $4,044 | -0.084 | 46.97 % | **41.67 %** | 45.45 % |

**Diferencia de equilibrio en la etiqueta, medida aquí con una rejilla de z (resolución ± 0.2 pp; H1 reportó −0.72 como paso de la cascada tras el finish-line, y −0.67 como componente aislado en H1b): -0.50 pp.** **Diferencia en WR_dec por sesión remedido con cada geometría (colchón $2,000): -5.80 pp.** Si el segundo número es negativo o ≈ 0, el 728×3 necesita *menos deriva*, no *menos WR*: el «−0.72 pp» (entre −0.5 y −0.8 según el método) es un efecto de la estructura de pagos medido en una escala —la etiqueta del bracket 364 nominal— que no corresponde a la geometría evaluada.

### 2d. Descomposición: ¿importa la simetría 667/728? Geometrías contrafactuales a la misma deriva (etiqueta 50 % y 48.5 %)

| etiqueta | TP / SL (ticks) | decididas por vida (TP / SL / liq.) | FLATTEN por vida | P(≥ 1 pago) | cobrado por XFA | pago medio si cobra | vida (días) |
|---|---|---|---|---|---|---|---|
| 50.0 % | TP 364 / SL 364 | 2.01 / 1.53 / 1.00 | 5.36 | 33.0 % | $647 | $1,958 | 9.9 |
| 50.0 % | TP 546 / SL 546 | 1.05 / 0.72 / 1.00 | 7.23 | 28.5 % | $728 | $2,553 | 10.0 |
| 50.0 % | TP 667 / SL 667 | 0.77 / 0.32 / 1.00 | 8.37 | 28.0 % | $804 | $2,868 | 10.5 |
| 50.0 % | TP 728 / SL 667 | 0.66 / 0.34 / 1.00 | 8.72 | 28.1 % | $820 | $2,917 | 10.7 |
| 50.0 % | TP 728 / SL 728 | 0.66 / 0.27 / 1.00 | 8.81 | 28.1 % | $824 | $2,935 | 10.7 |
| 48.5 % | TP 364 / SL 364 | 1.76 / 1.40 / 1.00 | 4.84 | 29.9 % | $508 | $1,699 | 9.0 |
| 48.5 % | TP 546 / SL 546 | 0.89 / 0.61 / 1.00 | 6.32 | 25.7 % | $568 | $2,206 | 8.8 |
| 48.5 % | TP 667 / SL 667 | 0.64 / 0.23 / 1.00 | 7.07 | 25.3 % | $615 | $2,434 | 8.9 |
| 48.5 % | TP 728 / SL 667 | 0.56 / 0.25 / 1.00 | 7.40 | 25.3 % | $634 | $2,505 | 9.2 |
| 48.5 % | TP 728 / SL 728 | 0.56 / 0.19 / 1.00 | 7.43 | 25.3 % | $636 | $2,513 | 9.2 |

Lectura (cifras de la tabla): el efecto de ensanchar de 364 a 728 es **monótono** (546 queda en medio) y **no depende de la simetría 667/728** (TP 728 / SL 667 ≈ 728/728). Existe **ya a deriva 0** (etiqueta 50 %: $824 vs $647), así que **no es cosecha de deriva ni mejor puntería**. Cambia la composición: las sesiones decididas por vida (sin contar la liquidación final) caen de ≈ 3.5 a ≈ 0.9, los FLATTEN suben de ≈ 5.4 a ≈ 8.8, la vida casi no cambia (9.9 → 10.7 días) y P(≥ 1 pago) baja (33.0 → 28.1 %), pero el pago cuando llega es mayor (ver 2e).

### 2e. Dónde está el dinero: tamaño de los pagos (deriva 0)

| geometría | P(≥ 1 pago) | pagos por vida que cobra | P(≥ 2 pagos) | primer pago neto medio | pago neto medio (todos) | mediana de días al 1.er pago | p90 |
|---|---|---|---|---|---|---|---|
| 3×364 | 33.0 % | 1.59 | 10.1 % | $1,051 | $1,235 | 7 | 10 |
| 3×728 | 28.1 % | 1.89 | 10.3 % | $1,335 | $1,519 | 7 | 11 |

**Mecanismo (lo que muestran las cifras; la causa última dentro del motor no se aisló con un experimento de apagado):** con 3×728 cada sesión ganadora suma ≈ $2,178 en lugar de ≈ $1,092 y cada FLATTEN positivo cuenta igual para los 5 días ≥ $150; cuando la cuenta llega a ser elegible su saldo —y por tanto el 50 % que se puede retirar (tope $2,000)— es mayor: el **primer pago medio sube de $1,051 a $1,335 y el pago medio de $1,235 a $1,519**, con la misma proporción de vidas con ≥ 2 pagos (10.1 vs 10.3 %). Es **estructura de pagos y de saldo**, no WR. Además un solo TP de $2,178 supera los +$2,000 que fijan el piso del MLL en $0 (`rules.lock`), cosa que en 3×364 exige dos TP seguidos.
