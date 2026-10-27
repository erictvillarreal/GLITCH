# resultados_J8 — Estrategia del primer día XFA (miércoles 28-oct-2026, día de FOMC)

**Fuentes y estado.** Días reales de 5 min de MGC (datos limpios de contrato, `GLITCH_MGC_PARQUET`; 488 días, 443 sin la ventana de oro 14-nov-2025 → 26-ene-2026), reproducidos con el motor `sim_day` / `xfa_engine` de las Partes A/D: **MODELADO sobre historia real**. No son sesiones vivas (no tengo el CSV de TopstepX ni el Gist). Fechas FOMC: `fomc_dates.txt` (federalreserve.gov, consultada 20-oct): MEDIDO. Dirección de producción: `strategies/geometry_pure.py::decide_side(trading_day_index(fecha), 'alternate')` (código en `main`, a387a70).
**Dirección de producción (calculada con el código, no supuesta):** mar 27-oct → CORTO; **mié 28-oct → LARGO**; jue 29-oct → CORTO (MES y MGC usan el mismo índice). Si la activación de la XFA consume un día (el modelo supone 1), el primer día XFA sería el jueves: se reporta también ese caso.
**Etiquetas de configuración (J8.1).** «XFA / Cerebro 2» = MGC, 3 micros, SL = TP = 364 ticks, `alternate`, entrada 7:13–7:15 CT, flatten 14:30 CT (`CANDIDATES['MGC']` = `xfa_mgc_config('50K')`). «Combine / Cerebro 1» = MES nc 40, TP 32, liquidación por MLL a 40 ticks (el SL de 100 no opera), 9:35 → 14:30 CT. **Las cifras de este archivo son de XFA/MGC salvo que diga MES.** Supuestos comunes: comisión MGC $1.92 por micro round-turn; stop llenado a 0.5 (convención C1); slippage de entrada: ver cada sección.

## A. H0-0 por candidata XFA (P&L neto por sesión, MGC, 488 días; colchón 9,000 como en `resultados_H1c.md` salvo la columna «LIQ día 1»)

`alternate (histórico)` = la alternancia que habría tocado en cada fecha real (la misma que H0-0 de H1c); `alternate (promedio L/C)` = promedio de LARGO y CORTO, que es lo que espera una alternancia de paridad desconocida. **Slip de entrada 0** (sin supuesto). «LIQ día 1» = P(la sesión toca la liquidación por MLL) con el colchón inicial de $2,000 (la XFA arranca con 2,000 de colchón).

| candidata | regla | n | P&L neto medio/sesión [IC95] | desvío | ≥ +$150 | ≤ −$150 | TP % | SL+LIQ % | FLATTEN % | WR_dec | LIQ día 1 (colchón $2,000) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3×364 (producción) | alternate (histórico) | 488 | $-47.9 [-114.0, +28.0] | $826 | 43.0 % | 43.2 % | 20.9 | 23.2 | 55.9 | 47.4 % | 0.4 % |
| 3×364 (producción) | siempre LARGO (= mié 28) | 488 | $-33.6 [-102.5, +38.2] | $832 | 44.9 % | 41.6 % | 20.3 | 23.8 | 55.9 | 46.0 % | 0.4 % |
| 3×364 (producción) | siempre CORTO | 488 | $-19.7 [-85.9, +47.2] | $814 | 41.4 % | 45.3 % | 23.8 | 20.3 | 55.9 | 54.0 % | 0.0 % |
| 3×364 (producción) | alternate (promedio L/C) | 488 | $-26.6 [-32.5, -20.4] | $55 | 43.1 % | 43.4 % | 22.0 | 22.0 | 55.9 | 50.0 % | 0.2 % |
| 3×728 | alternate (histórico) | 488 | $-45.3 [-136.1, +48.1] | $1,051 | 43.0 % | 41.4 % | 5.5 | 7.4 | 87.1 | 42.9 % | 9.2 % |
| 3×728 | siempre LARGO (= mié 28) | 488 | $-16.0 [-97.5, +74.8] | $1,055 | 45.1 % | 39.5 % | 4.9 | 8.0 | 87.1 | 38.1 % | 9.6 % |
| 3×728 | siempre CORTO | 488 | $-8.4 [-98.9, +73.9] | $1,040 | 39.1 % | 45.7 % | 8.0 | 4.9 | 87.1 | 61.9 % | 6.1 % |
| 3×728 | alternate (promedio L/C) | 488 | $-12.2 [-14.7, -9.6] | $28 | 42.1 % | 42.6 % | 6.5 | 6.5 | 87.1 | 50.0 % | 7.9 % |
| 1 micro, 364 | alternate (histórico) | 488 | $-16.0 [-38.0, +9.3] | $275 | 28.9 % | 32.2 % | 20.9 | 23.2 | 55.9 | 47.4 % | 0.0 % |
| 1 micro, 364 | siempre LARGO (= mié 28) | 488 | $-11.2 [-34.2, +12.7] | $277 | 30.9 % | 30.1 % | 20.3 | 23.8 | 55.9 | 46.0 % | 0.0 % |
| 1 micro, 364 | siempre CORTO | 488 | $-6.6 [-28.6, +15.7] | $271 | 29.9 % | 30.9 % | 23.8 | 20.3 | 55.9 | 54.0 % | 0.0 % |
| 1 micro, 364 | alternate (promedio L/C) | 488 | $-8.9 [-10.8, -6.8] | $18 | 30.4 % | 30.5 % | 22.0 | 22.0 | 55.9 | 50.0 % | 0.0 % |
| 4 micros, 364 (1.ª etapa de 4→1) | alternate (histórico) | 488 | $-63.8 [-152.0, +37.3] | $1,101 | 44.7 % | 45.5 % | 20.9 | 23.2 | 55.9 | 47.4 % | 1.0 % |
| 4 micros, 364 (1.ª etapa de 4→1) | siempre LARGO (= mié 28) | 488 | $-44.8 [-136.7, +51.0] | $1,109 | 46.9 % | 43.0 % | 20.3 | 23.8 | 55.9 | 46.0 % | 0.6 % |
| 4 micros, 364 (1.ª etapa de 4→1) | siempre CORTO | 488 | $-26.2 [-114.5, +62.9] | $1,085 | 42.8 % | 47.3 % | 23.8 | 20.3 | 55.9 | 54.0 % | 0.8 % |
| 4 micros, 364 (1.ª etapa de 4→1) | alternate (promedio L/C) | 488 | $-35.5 [-43.3, -27.3] | $73 | 44.9 % | 45.2 % | 22.0 | 22.0 | 55.9 | 50.0 % | 0.7 % |
| 3×364, flatten 13:30 | alternate (histórico) | 498 | $-45.9 [-111.3, +26.1] | $808 | 43.6 % | 43.2 % | 19.3 | 22.5 | 58.2 | 46.2 % | 0.4 % |
| 3×364, flatten 13:30 | siempre LARGO (= mié 28) | 498 | $-29.7 [-98.3, +43.8] | $814 | 45.2 % | 41.4 % | 19.3 | 22.5 | 58.2 | 46.2 % | 0.4 % |
| 3×364, flatten 13:30 | siempre CORTO | 498 | $-21.9 [-90.5, +44.5] | $796 | 41.2 % | 45.8 % | 22.5 | 19.3 | 58.2 | 53.8 % | 0.0 % |
| 3×364, flatten 13:30 | alternate (promedio L/C) | 498 | $-25.8 [-30.6, -19.8] | $54 | 43.2 % | 43.6 % | 20.9 | 20.9 | 58.2 | 50.0 % | 0.2 % |
| 3×364, flatten 12:00 | alternate (histórico) | 503 | $-39.0 [-102.6, +29.6] | $783 | 42.9 % | 41.6 % | 18.1 | 20.5 | 61.4 | 46.9 % | 0.4 % |
| 3×364, flatten 12:00 | siempre LARGO (= mié 28) | 503 | $-33.3 [-99.0, +31.3] | $792 | 43.1 % | 41.4 % | 17.1 | 21.5 | 61.4 | 44.3 % | 0.4 % |
| 3×364, flatten 12:00 | siempre CORTO | 503 | $-13.8 [-75.0, +50.2] | $771 | 40.8 % | 43.9 % | 21.5 | 17.1 | 61.4 | 55.7 % | 0.0 % |
| 3×364, flatten 12:00 | alternate (promedio L/C) | 503 | $-23.6 [-28.6, -18.0] | $51 | 41.9 % | 42.6 % | 19.3 | 19.3 | 61.4 | 50.0 % | 0.2 % |
| 3×364, flatten 10:30 | alternate (histórico) | 503 | $-28.2 [-90.7, +31.8] | $744 | 41.0 % | 41.2 % | 16.5 | 16.9 | 66.6 | 49.4 % | 0.4 % |
| 3×364, flatten 10:30 | siempre LARGO (= mié 28) | 503 | $-36.9 [-101.7, +24.3] | $754 | 42.1 % | 40.8 % | 14.5 | 18.9 | 66.6 | 43.5 % | 0.4 % |
| 3×364, flatten 10:30 | siempre CORTO | 503 | $-8.0 [-64.3, +54.0] | $733 | 40.0 % | 42.1 % | 18.9 | 14.5 | 66.6 | 56.5 % | 0.0 % |
| 3×364, flatten 10:30 | alternate (promedio L/C) | 503 | $-22.4 [-27.4, -16.7] | $51 | 41.1 % | 41.5 % | 16.7 | 16.7 | 66.6 | 50.0 % | 0.2 % |

Lectura A: ver la sección de conclusiones del reporte; los IC95 son remuestras de bloques de 5 días de la historia real (1,000).

## B. Tabla de decisión para el primer día XFA (vidas simuladas hasta liquidación; MGC; slippage de entrada = distribución empírica de 8 obs. {-1.0: 0.125, 0.0: 0.375, 1.0: 0.25, 3.0: 0.25}, **8.ª observación inferida = 0, NO VERIFICADA**; OPS $245/año)

Cada celda: media sobre 60,000 vidas, IC95 = percentiles de 40 remuestras de bloques de 5 días de los 443 días del pool (cada una con 8,000 vidas; mismas semillas en todas las políticas ⇒ las **diferencias son pareadas**). «Cobrado» = pagos netos al trader (división 90/10, tope $2,000 por pago, 5 días ≥ $150, regla de ganancia desde el 2.º pago; `xfa_engine.Rules()` por defecto = `RULEBOOK_XFA.md`), **no** descuenta la activación de $149 (igual para todas). «Neto tras OPS» resta $245 × vida/252. La deriva es la etiqueta de WR (nominal 364/364); 50 % = deriva 0 sobre la historia real.


### WR 50 % (deriva 0) — primer día XFA: mié 28-oct = LARGO

| política | cobrado esperado por XFA [IC95] | Δ vs 3×364 (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) [IC95] | P(muerte en 3 días) [IC95] | P(muerte el día 1) | vida (días) | mediana días al 1.er pago | 1.er pago medio | neto tras OPS $245/año |
|---|---|---|---|---|---|---|---|---|---|---|
| 3×364 alternate (producción) | $618 [592, 698] | — | — | 32.2 % [30.4, 34.0] | 18.4 % [16.3, 20.9] | 0.4 % | 9.7 | 8 | $1,044 | $609 |
| 3×728 | $798 [730, 869] | $+180 [+125, +253] | SÍ | 28.0 % [26.0, 29.4] | 30.7 % [27.6, 35.1] | 9.1 % | 10.4 | 8 | $1,331 | $788 |
| 4→1 micros (4 hasta saldo $1,500, luego 1) | $715 [671, 770] | $+97 [+58, +122] | SÍ | 32.1 % [30.5, 33.1] | 34.8 % [32.7, 37.8] | 0.6 % | 11.2 | 10 | $1,171 | $704 |
| 1 micro toda la vida | $356 [343, 384] | $-262 [-314, -237] | SÍ | 63.6 % [62.4, 65.2] | 0.0 % [0.0, 0.0] | 0.0 % | 26.0 | 14 | $312 | $331 |
| 1 micro la 1.ª semana (5 días), luego 3 | $582 [561, 646] | $-36 [-56, -1] | SÍ | 40.2 % [39.0, 41.9] | 0.0 % [0.0, 0.0] | 0.0 % | 12.8 | 10 | $804 | $570 |
| 1 micro SOLO el día 1, luego 3 | $614 [588, 683] | $-4 [-25, +14] | NO | 33.4 % [31.9, 35.2] | 9.8 % [8.2, 11.2] | 0.0 % | 10.4 | 9 | $1,002 | $604 |
| NO operar el día 1, luego 3 | $619 [593, 680] | $+1 [-24, +28] | NO | 32.3 % [30.8, 33.8] | 7.4 % [5.9, 8.7] | 0.0 % | 10.8 | 9 | $1,045 | $609 |
| 3×364 siempre LARGO (sin respaldo fuera de muestra) | $574 [321, 908] | $-44 [-285, +257] | NO | 32.1 % [22.4, 40.6] | 19.7 % [16.2, 24.0] | 0.4 % | 9.1 | 8 | $1,010 | $565 |
| 3×364 siempre CORTO (sin respaldo fuera de muestra) | $689 [470, 1,441] | $+70 [-186, +829] | NO | 33.0 % [27.2, 42.3] | 15.9 % [12.2, 18.8] | 0.0 % | 10.6 | 9 | $1,084 | $678 |
| 3×364, flatten 12:00 CT | $615 [574, 665] | $-3 [-78, +51] | NO | 33.6 % [31.9, 36.4] | 15.7 % [12.7, 18.7] | 0.4 % | 10.3 | 9 | $1,000 | $605 |
| 3×364, flatten 10:30 CT | $612 [574, 663] | $-6 [-80, +39] | NO | 35.6 % [33.8, 38.6] | 13.3 % [10.1, 15.9] | 0.4 % | 10.8 | 9 | $934 | $602 |

### WR 47.4 % (≈ el medido) — primer día XFA: mié 28-oct = LARGO

| política | cobrado esperado por XFA [IC95] | Δ vs 3×364 (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) [IC95] | P(muerte en 3 días) [IC95] | P(muerte el día 1) | vida (días) | mediana días al 1.er pago | 1.er pago medio | neto tras OPS $245/año |
|---|---|---|---|---|---|---|---|---|---|---|
| 3×364 alternate (producción) | $384 [362, 437] | — | — | 25.0 % [24.0, 26.6] | 20.8 % [18.4, 23.5] | 0.4 % | 8.2 | 8 | $1,008 | $376 |
| 3×728 | $450 [405, 502] | $+65 [+20, +105] | SÍ | 21.3 % [20.0, 22.5] | 33.4 % [30.8, 37.3] | 9.3 % | 7.9 | 9 | $1,283 | $442 |
| 4→1 micros (4 hasta saldo $1,500, luego 1) | $473 [443, 540] | $+89 [+72, +109] | SÍ | 25.2 % [24.3, 26.7] | 38.3 % [36.1, 41.2] | 0.6 % | 9.1 | 10 | $1,161 | $464 |
| 1 micro toda la vida | $215 [196, 246] | $-170 [-197, -160] | SÍ | 49.0 % [47.3, 51.9] | 0.0 % [0.0, 0.0] | 0.0 % | 24.2 | 15 | $299 | $191 |
| 1 micro la 1.ª semana (5 días), luego 3 | $372 [354, 426] | $-13 [-31, +13] | NO | 31.5 % [30.4, 33.7] | 0.0 % [0.0, 0.0] | 0.0 % | 11.5 | 10 | $787 | $360 |
| 1 micro SOLO el día 1, luego 3 | $381 [353, 436] | $-3 [-14, +12] | NO | 25.9 % [24.9, 27.6] | 11.2 % [9.3, 12.8] | 0.0 % | 8.9 | 9 | $974 | $373 |
| NO operar el día 1, luego 3 | $386 [354, 436] | $+1 [-13, +24] | NO | 25.1 % [24.2, 26.9] | 8.4 % [6.7, 9.5] | 0.0 % | 9.2 | 9 | $1,010 | $377 |
| 3×364 siempre LARGO (sin respaldo fuera de muestra) | $366 [210, 531] | $-19 [-182, +136] | NO | 25.3 % [17.5, 32.0] | 21.9 % [18.5, 26.7] | 0.4 % | 7.8 | 8 | $963 | $358 |
| 3×364 siempre CORTO (sin respaldo fuera de muestra) | $424 [270, 836] | $+40 [-116, +444] | NO | 25.2 % [19.0, 35.4] | 18.6 % [15.5, 21.5] | 0.0 % | 8.8 | 9 | $1,070 | $416 |
| 3×364, flatten 12:00 CT | $355 [324, 395] | $-29 [-91, +18] | NO | 24.4 % [23.0, 26.6] | 18.5 % [15.3, 21.3] | 0.4 % | 8.6 | 9 | $983 | $347 |
| 3×364, flatten 10:30 CT | $321 [287, 361] | $-64 [-124, -16] | SÍ | 24.7 % [23.3, 26.5] | 15.8 % [12.4, 18.7] | 0.4 % | 8.8 | 9 | $906 | $312 |

### WR 50 % (deriva 0) — primer día XFA: jue 29-oct = CORTO

| política | cobrado esperado por XFA [IC95] | Δ vs 3×364 (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) [IC95] | P(muerte en 3 días) [IC95] | P(muerte el día 1) | vida (días) | mediana días al 1.er pago | 1.er pago medio | neto tras OPS $245/año |
|---|---|---|---|---|---|---|---|---|---|---|
| 3×364 alternate (producción) | $641 [602, 676] | — | — | 32.8 % [30.8, 34.2] | 17.0 % [15.7, 19.5] | 0.0 % | 9.9 | 8 | $1,053 | $631 |
| 3×728 | $819 [746, 878] | $+178 [+88, +229] | SÍ | 28.2 % [25.6, 29.7] | 28.7 % [26.1, 33.8] | 6.5 % | 10.7 | 8 | $1,333 | $809 |
| 4→1 micros (4 hasta saldo $1,500, luego 1) | $724 [689, 758] | $+83 [+51, +118] | SÍ | 32.7 % [31.2, 33.4] | 33.4 % [32.2, 37.2] | 0.9 % | 11.3 | 10 | $1,175 | $713 |
| 1 micro toda la vida | $361 [348, 376] | $-280 [-304, -254] | SÍ | 64.0 % [62.3, 66.2] | 0.0 % [0.0, 0.0] | 0.0 % | 26.1 | 14 | $315 | $335 |
| 1 micro la 1.ª semana (5 días), luego 3 | $598 [551, 635] | $-43 [-84, -19] | SÍ | 40.5 % [38.7, 42.2] | 0.0 % [0.0, 0.0] | 0.0 % | 12.9 | 10 | $800 | $585 |
| 1 micro SOLO el día 1, luego 3 | $632 [587, 658] | $-8 [-31, +4] | NO | 34.0 % [31.8, 35.1] | 9.4 % [8.2, 11.0] | 0.0 % | 10.4 | 9 | $1,006 | $622 |
| NO operar el día 1, luego 3 | $639 [586, 677] | $-1 [-41, +11] | NO | 32.8 % [30.3, 33.8] | 7.3 % [6.3, 8.6] | 0.0 % | 10.9 | 9 | $1,047 | $629 |

«¿distinguible?» = el IC95 de la diferencia pareada excluye 0. Este IC cuenta la incertidumbre del conjunto de días históricos y el ruido de simulación; **no** cuenta cambio de régimen, el slippage real de MGC (no medido) ni el WR verdadero.

## C. Efecto FOMC en MGC (J8.3) — geometría de producción, entrada 7:15 CT, flatten 14:30 CT

Días FOMC (día del anuncio, 13:00 CT) dentro de la muestra de MGC: **16** de 488 (ventana 2024-09-06 → 2026-09-04). Es una muestra pequeña: cualquier diferencia debajo es **anecdótica**, no prueba.

| geometría | lado | grupo | n | P&L neto medio/sesión | TP % | SL+LIQ % | FLATTEN % | |P&L| medio | peor sesión | sesiones sin resolver a las 13:00 CT |
|---|---|---|---|---|---|---|---|---|---|---|
| 3×364 | LARGO (mié 28) | FOMC | 16 | $-178.3 | 25 | 38 | 38 | $877 | $-1,342 | 56 % |
| 3×364 | LARGO (mié 28) | resto | 472 | $-27.7 | 20 | 23 | 57 | $698 | $-2,000 | 58 % |
| 3×364 | CORTO | FOMC | 16 | $+93.8 | 38 | 25 | 38 | $900 | $-1,717 | 56 % |
| 3×364 | CORTO | resto | 472 | $-23.5 | 23 | 20 | 57 | $686 | $-1,731 | 58 % |
| 3×728 | LARGO (mié 28) | FOMC | 16 | $-296.8 | 12 | 19 | 69 | $1,146 | $-2,000 | 94 % |
| 3×728 | LARGO (mié 28) | resto | 472 | $+3.7 | 5 | 9 | 86 | $759 | $-2,000 | 89 % |
| 3×728 | CORTO | FOMC | 16 | $+312.5 | 12 | 12 | 75 | $1,123 | $-2,000 | 94 % |
| 3×728 | CORTO | resto | 472 | $-15.7 | 8 | 6 | 86 | $758 | $-2,000 | 89 % |
| 1 micro, 364 | LARGO (mié 28) | FOMC | 16 | $-59.4 | 25 | 38 | 38 | $292 | $-447 | 56 % |
| 1 micro, 364 | LARGO (mié 28) | resto | 472 | $-9.6 | 20 | 23 | 57 | $233 | $-801 | 58 % |
| 1 micro, 364 | CORTO | FOMC | 16 | $+31.3 | 38 | 25 | 38 | $300 | $-572 | 56 % |
| 1 micro, 364 | CORTO | resto | 472 | $-7.8 | 23 | 20 | 57 | $229 | $-577 | 58 % |

**Diferencia FOMC − resto y p de permutación (20,000, bilateral):**

| geometría | lado | Δ P&L medio | p | Δ |P&L| medio | p |
|---|---|---|---|---|---|
| 3×364 | LARGO (mié 28) | $-150.6 | 0.48 | $+179.2 | 0.11 |
| 3×364 | CORTO | $+117.3 | 0.58 | $+213.7 | 0.05 |
| 3×728 | LARGO (mié 28) | $-300.5 | 0.25 | $+387.1 | 0.02 |
| 3×728 | CORTO | $+328.2 | 0.21 | $+364.4 | 0.03 |
| 1 micro, 364 | LARGO (mié 28) | $-49.8 | 0.49 | $+59.4 | 0.12 |
| 1 micro, 364 | CORTO | $+39.1 | 0.58 | $+71.2 | 0.05 |

**Primer toque de ±364 ticks por día FOMC** (barrera simétrica de la geometría de producción; el lado del trade decide si es TP o SL):

| fecha FOMC | primer toque (CT) | dirección | cierre del día (ticks) | ¿después de las 13:00? |
|---|---|---|---|---|
| 2024-09-18 | — (sin toque) | — | -109 | no |
| 2024-11-07 | — (sin toque) | — | 303 | no |
| 2024-12-18 | 13:40 | abajo | -502 | **SÍ** |
| 2025-01-29 | — (sin toque) | — | 72 | no |
| 2025-03-19 | — (sin toque) | — | 45 | no |
| 2025-05-07 | — (sin toque) | — | -168 | no |
| 2025-06-18 | — (sin toque) | — | -205 | no |
| 2025-07-30 | 10:15 | abajo | -556 | no |
| 2025-09-17 | 13:00 | arriba | -67 | **SÍ** |
| 2025-10-29 | 12:20 | abajo | -725 | no |
| 2025-12-10 | 14:05 | arriba | 400 | **SÍ** |
| 2026-01-28 | 9:00 | abajo | 807 | no |
| 2026-03-18 | 7:55 | abajo | -556 | no |
| 2026-04-29 | 8:25 | abajo | -223 | no |
| 2026-06-17 | 9:15 | arriba | -970 | no |
| 2026-07-29 | 12:55 | arriba | 646 | no |

**3 de 16 días FOMC (19 %) tuvieron su primer toque de ±364 DESPUÉS de las 13:00 CT, contra 6 de 472 (1.3 %) en los demás días; P(≥ 3 de 16 | tasa base) = 0.0010 (binomial exacta, una cola).** Es el único indicio de un efecto FOMC sobre la geometría: con 3 eventos es frágil y no dice la dirección.
**Corrección a H4:** `resultados_H4.md` y `REPORTE_H.md` §2.3 decían que «≈ 80 % de los días de MGC siguen abiertos a las 13:00 CT». Ese número ignoraba el SL de 364 ticks (el script de H4 contaba solo el TP y la liquidación por colchón de 9,000). **Medido con ambas barreras: 57.8 % de los días siguen sin resolver a las 13:00 CT (56 % en días FOMC)**; los días que se resuelven 'tras' las 13:00 son 1.8 % del total.

### C2. Vidas con el día 1 sorteado de los días FOMC históricos (WR 50 %, mié = LARGO; el resto de los días del pool)

| política | cobrado esperado [IC95] | P(≥ 1 pago) | P(muerte día 1) | P(muerte en 3 días) | vida |
|---|---|---|---|---|---|
| 3×364 alternate (producción) | $577 [560, 637] | 30.0 % | 0.0 % | 23.4 % | 9.3 |
| 1 micro SOLO el día 1, luego 3 | $599 [571, 660] | 33.0 % | 0.0 % | 10.8 % | 10.2 |
| NO operar el día 1, luego 3 | $619 [593, 680] | 32.3 % | 0.0 % | 7.4 % | 10.8 |
| 1 micro toda la vida | $343 [333, 368] | 62.6 % | 0.0 % | 0.0 % | 25.9 |

(Nota: el IC de C2 resortea solo los días del pool; los 16 días FOMC del día 1 no se remuestrean ⇒ el IC subestima la incertidumbre de n = 16.)

### C3. Diferencias pareadas con el día 1 sorteado de los días FOMC (remuestreando también los días FOMC; WR 50 %, mié = LARGO)

| política | Δ cobrado vs 3×364 [IC95] | fracción de remuestras con Δ > 0 | Δ P(muerte en 3 días) [IC95] |
|---|---|---|---|
| 1 micro SOLO el día 1 (FOMC) | $+23 [-82, +126] | 68 % | -12.6 pp [-19.7, -6.8] |
| NO operar el día 1 (FOMC) | $+46 [-103, +209] | 72 % | -16.0 pp [-24.9, -8.7] |
