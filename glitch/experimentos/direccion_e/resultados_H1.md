# resultados_H1 — descomposición del equilibrio de la cadena completa (WR_dec en que el neto anual por cuenta = 0)

**Idea en tres líneas.** El equilibrio es el WR mínimo para no perder dinero después de todos los costos; cada costo que baja (o cada forma de la cadena que mejora) baja el listón, **no la puntería**. Como un volado con cuota del 3 % exige 51.5 % y con cuota del 1 % exige 50.5 %, aquí cada componente mueve el equilibrio tantos puntos como dólares/año valga dividido por lo que vale un punto de WR (≈ $1.1–1.4k/año/cuenta en esta cadena).

Línea base: Combine P0 nc 40 con slip de entrada mezcla {1,3} 50/50 (SUPUESTO), salida del SL con 3 ticks de gap (SUPUESTO), comisión MES $1.22 y MGC $1.92, reset/mensualidad $49 por intento, activación $149, costos operativos $714/año compartidos, XFA 3×364 con stop 0.5, slip MGC 0. **Equilibrio base = 48.55 %**; neto anual a 48 % = $-524, a 50 % = $1,365; **valor de un punto de WR ≈ $945/año/cuenta** (pendiente local 48–50 %).

## 1. Cada componente por separado (los demás en la línea base)

| grupo | componente | equilibrio | Δ equilibrio (pp) | neto/año a WR 50 % | Δ $/año/cuenta a WR 50 % | neto/año a 47.4 % (extrapolado) | estado |
|---|---|---|---|---|---|---|---|
| Combine | reset/mensualidad $49 → $0 (límite teórico) | 45.35 % | -3.21 | $3,897 | +2,531 | $1,719 | MEDIDO (tarifa oficial) |
| Combine | reset/mensualidad $49 → $98 | 51.11 % | +2.55 | $-1,166 | -2,531 | $-3,900 | MEDIDO (tarifa oficial) |
| Combine | activación $149 → $0 | 46.88 % | -1.68 | $2,933 | +1,568 | $491 | MEDIDO (tarifa oficial) |
| Combine | slip de entrada del Combine = 0 ticks fijos (base: mezcla 1/3) | 47.40 % | -1.15 | $2,900 | +1,535 | $-2 | MODELADO; el valor del parámetro es SUPUESTO |
| Combine | slip de entrada del Combine = 1 ticks fijos (base: mezcla 1/3) | 47.46 % | -1.09 | $2,791 | +1,426 | $-70 | MODELADO; el valor del parámetro es SUPUESTO |
| Combine | slip de entrada del Combine = 4 ticks fijos (base: mezcla 1/3) | 49.47 % | +0.91 | $455 | -911 | $-1,769 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | tamaño 728×3 (SL = TP = 728) | 47.72 % | -0.83 | $2,676 | +1,311 | $-378 | MODELADO |
| Combine | finish-line (P3) en lugar de 40 fijos | 47.72 % | -0.83 | $2,337 | +972 | $-330 | MODELADO |
| XFA | tamaño 4→1 micros (cobro ≥ $1,500) | 47.75 % | -0.80 | $1,952 | +587 | $-307 | MODELADO |
| Combine | costos operativos $714 → $0 | 47.80 % | -0.76 | $2,079 | +714 | $-377 | MODELADO |
| Combine | costos operativos $714 → $1,428 | 49.31 % | +0.76 | $651 | -714 | $-1,805 | MODELADO |
| Combine | comisión MES $1.22 → $0 (límite inferior teórico) | 47.82 % | -0.74 | $2,297 | +932 | $-439 | MODELADO |
| Combine | slip de entrada del Combine = 3 ticks fijos (base: mezcla 1/3) | 49.22 % | +0.67 | $681 | -684 | $-1,590 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | slip de entrada MGC = 4 ticks (base: 0) | 49.12 % | +0.57 | $769 | -596 | $-1,502 | MODELADO; el valor del parámetro es SUPUESTO |
| Combine | comisión MES $1.22 → $2.44 (duplicada) | 49.12 % | +0.56 | $776 | -589 | $-1,514 | MODELADO |
| XFA | stop exacto (convención optimista) en lugar de 0.5 | 48.01 % | -0.55 | $2,136 | +771 | $-649 | MODELADO |
| Combine | slip de entrada del Combine = 2 ticks fijos (base: mezcla 1/3) | 49.06 % | +0.51 | $837 | -528 | $-1,478 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | slip de entrada MGC = 3 ticks (base: 0) | 48.97 % | +0.41 | $916 | -449 | $-1,391 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | slip de entrada MGC = 2 ticks (base: 0) | 48.82 % | +0.27 | $1,068 | -297 | $-1,293 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | comisión MGC $1.92 → $3.84 | 48.79 % | +0.24 | $1,104 | -261 | $-1,271 | MEDIDO (tarifa oficial) |
| XFA | comisión MGC $1.92 → $0 | 48.34 % | -0.22 | $1,651 | +286 | $-928 | MODELADO |
| XFA | slip de entrada MGC = 1 ticks (base: 0) | 48.69 % | +0.14 | $1,213 | -153 | $-1,199 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | slip de salida MGC 0 → 6 ticks | 48.66 % | +0.11 | $1,240 | -125 | $-1,172 | MODELADO; el valor del parámetro es SUPUESTO |
| XFA | slip de salida MGC (SL/FLATTEN) 0 → 3 ticks | 48.61 % | +0.05 | $1,298 | -67 | $-1,126 | MODELADO; el valor del parámetro es SUPUESTO |
| Combine | slip de salida del SL/liquidación 3 → 0 ticks | 48.55 % | +0.00 | $1,365 | +0 | $-1,091 | MODELADO; el valor del parámetro es SUPUESTO |
| Combine | slip de salida 3 → 6 ticks | 48.55 % | +0.00 | $1,365 | +0 | $-1,091 | MODELADO; el valor del parámetro es SUPUESTO |

Lectura: los componentes de la tabla marcados «→ $0» o «duplicada» son **cotas teóricas**, no palancas disponibles (la comisión y la tarifa las fija Topstep/CME). Las palancas controlables son: **finish-line, tamaño/política de la XFA, slippage (por cómo se ejecuta y se ancla) y costos operativos**.

## 2. Cascada acumulada de palancas controlables (cada paso suma al anterior; el equilibrio se recalcula con la cadena completa, no se suma)

| paso | equilibrio | Δ vs paso anterior (pp) | neto/año a WR 50 % | valor de 1 pp aquí |
|---|---|---|---|---|
| hoy | 48.55 % |  | $1,365 | $945 |
| + finish-line (P3) | 47.72 % | -0.83 | $2,337 | $1,026 |
| + 728×3 | 47.00 % | -0.72 | $3,833 | $1,277 |
| + costos operativos $714 → $0 (pausar servicios sobrantes) | 46.44 % | -0.56 | $4,547 | $1,277 |
| + slip de entrada del Combine ≤ 1 tick (si el anclaje/límite lo logra) | 46.20 % | -0.24 | $5,129 | $1,351 |

**Primera combinación (en este orden) que baja el equilibrio de la cadena por debajo de 47.4 %:** + 728×3. **Por debajo de 46.5 %:** + costos operativos $714 → $0 (pausar servicios sobrantes).
Evidencia de cada paso: finish-line y 728×3 son **MODELADOS** con el motor de las Partes A/D sobre días reales (no medidos en vivo); 728×3 y 4→1 tocan los criterios de RTP/«conducta prohibida» (preguntas pendientes para Topstep); «costos operativos → $0» es una **decisión** (qué servicios se pausan), no un hecho de mercado; «slip ≤ 1 tick» es un **SUPUESTO** hasta tener C3 (hoy N = 2).