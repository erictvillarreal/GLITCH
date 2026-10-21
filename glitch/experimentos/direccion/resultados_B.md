# resultados_B (generado por run_partB.py; semilla 20261020)

Muestra de evaluacion: 443 dias (2024-11-04 -> 2026-08-25), calentamiento 50 dias. Medida base: nc=40, colchon $2,000, TP32/SL100, slip entrada {1,3} promediado, salida SL supuesta 3.
Ventana dominante (Enmienda 2): 2025-04-09 -> 2025-07-08 (60 dias de evaluacion).

## D1 - P(TP-primero) LONG vs SHORT por bloque (TODA la muestra)

| bloque | fechas | dias | LONG | SHORT | LONG - SHORT |
|---|---|---|---|---|---|
| 1 | 2024-11-04..2025-01-10 | 44 | 69.3% | 45.5% | +23.9 pp |
| 2 | 2025-01-13..2025-03-20 | 44 | 58.0% | 51.1% | +6.8 pp |
| 3 | 2025-03-21..2025-05-22 | 44 | 50.0% | 56.8% | -6.8 pp |
| 4 | 2025-05-23..2025-07-29 | 44 | 38.6% | 56.8% | -18.2 pp |
| 5 | 2025-07-30..2025-09-30 | 44 | 40.9% | 60.2% | -19.3 pp |
| 6 | 2025-10-01..2025-12-03 | 44 | 61.4% | 53.4% | +8.0 pp |
| 7 | 2025-12-04..2026-02-09 | 44 | 52.3% | 56.8% | -4.5 pp |
| 8 | 2026-02-10..2026-04-15 | 44 | 47.7% | 52.3% | -4.5 pp |
| 9 | 2026-04-16..2026-06-17 | 44 | 60.2% | 47.7% | +12.5 pp |
| 10 | 2026-06-18..2026-08-25 | 47 | 44.7% | 66.0% | -21.3 pp |
| **total** |  | 443 | 52.3% | 54.7% | -2.5 pp |

Diferencia media LONG-SHORT = -2.48 pp; IC 98.3% (bootstrap de bloques de 5 dias) = [-12.98, +7.79] pp.

## D1 - P(TP-primero) LONG vs SHORT por bloque (SIN la ventana dominante)

| bloque | fechas | dias | LONG | SHORT | LONG - SHORT |
|---|---|---|---|---|---|
| 1 | 2024-11-04..2025-01-10 | 44 | 69.3% | 45.5% | +23.9 pp |
| 2 | 2025-01-13..2025-03-20 | 44 | 58.0% | 51.1% | +6.8 pp |
| 3 | 2025-03-21..2025-05-22 | 13 | 38.5% | 61.5% | -23.1 pp |
| 4 | 2025-05-23..2025-07-29 | 15 | 46.7% | 53.3% | -6.7 pp |
| 5 | 2025-07-30..2025-09-30 | 44 | 40.9% | 60.2% | -19.3 pp |
| 6 | 2025-10-01..2025-12-03 | 44 | 61.4% | 53.4% | +8.0 pp |
| 7 | 2025-12-04..2026-02-09 | 44 | 52.3% | 56.8% | -4.5 pp |
| 8 | 2026-02-10..2026-04-15 | 44 | 47.7% | 52.3% | -4.5 pp |
| 9 | 2026-04-16..2026-06-17 | 44 | 60.2% | 47.7% | +12.5 pp |
| 10 | 2026-06-18..2026-08-25 | 47 | 44.7% | 66.0% | -21.3 pp |
| **total** |  | 383 | 53.4% | 54.4% | -1.0 pp |

Diferencia media LONG-SHORT = -1.04 pp; IC 98.3% (bootstrap de bloques de 5 dias) = [-12.88, +10.39] pp.

Las 8 sesiones en vivo (anecdota): NO DISPONIBLE localmente (viven en el Gist `geometry_mestest_log.json`, requiere token; ver Enmienda 1 §8).

## D2 - reglas candidatas (P(TP-primero) sobre los dias que la regla opera)

| regla | dias operados | P(TP) regla | P(TP) alternate | P(TP) siempre LONG | (a) gana a alternate en bloques | (b) dif. media pp [IC98.3%] | (c) pierde vs siempre LONG | (d) dif. sin ventana dominante (pp) | veredicto |
|---|---|---|---|---|---|---|---|---|---|
| R1 | 443 | 51.4% | 55.5% | 52.3% | 4/10 (NO) | -4.18 [-11.17,+3.39] (NO) | 4/10 (NO) | -5.61 (NO) | no pasa |
| R2 | 443 | 54.0% | 55.5% | 52.3% | 5/10 (NO) | -1.58 [-8.13,+5.87] (NO) | 1/10 (OK) | -2.61 (NO) | no pasa |
| R3 | 358 | 53.1% | 56.1% | 49.3% | 4/10 (NO) | -3.07 [-10.67,+5.08] (NO) | 0/10 (OK) | -3.61 (NO) | no pasa |

Criterios (PREREGISTRO.md): (a) >=7/10, (b) limite inferior del IC98.3% > 0, (c) <=3/10, (d) dif. sin ventana dominante >= 0. Pasa D2 solo si cumple las cuatro.

## Controles y reglas: medida base (toda la muestra; dias operados de cada regla)

| regla/control | dias operados | P(TP-primero) | P(liq 1 dia) | ticks netos medios/dia | P(TP) sin ventana dominante |
|---|---|---|---|---|---|
| R1 | 443 | 51.4% | 48.6% | -4.54 | 51.8% |
| R2 | 443 | 54.0% | 46.0% | -2.75 | 54.8% |
| R3 | 358 | 53.1% | 46.9% | -3.36 | 54.8% |
| alternate | 443 | 55.5% | 44.0% | -1.58 | 57.4% |
| always_long | 443 | 52.3% | 47.7% | -3.92 | 53.4% |
| always_short | 443 | 54.7% | 44.8% | -2.12 | 54.4% |
| oracle | 443 | 99.1% | 0.9% | +28.40 | 99.5% |
| aleatorio (1000 corridas) | 443 | 53.5% (p2.5-p97.5: 49.3-57.7) | - | - | - |

## Puente a P(pase del Combine): repeticion historica M2h (un intento por fecha de inicio; solo intentos con ventana completa o ya resueltos)

| politica de tamano | regla de lado | intentos | P(pase) [IC95% bloques] | P(liquidacion) |
|---|---|---|---|---|
| P0 40 fijo | R1 | 443 | 30.9% [24.6,36.1] | 69.1% |
| P0 40 fijo | R2 | 442 | 33.0% [27.1,38.9] | 67.0% |
| P0 40 fijo | R3 | 439 | 34.6% [28.9,41.5] | 65.4% |
| P0 40 fijo | alternate | 442 | 35.7% [30.5,40.5] | 64.3% |
| P0 40 fijo | always_long | 442 | 32.4% [26.5,38.5] | 67.6% |
| P0 40 fijo | always_short | 443 | 35.2% [29.8,40.4] | 64.8% |
| P0 40 fijo | oracle | 442 | 98.9% [97.5,99.8] | 1.1% |
| P3 finish-line | R1 | 443 | 47.4% [41.5,52.8] | 52.6% |
| P3 finish-line | R2 | 442 | 49.8% [44.3,55.7] | 50.2% |
| P3 finish-line | R3 | 439 | 49.7% [43.5,56.7] | 50.3% |
| P3 finish-line | alternate | 442 | 51.6% [45.2,56.8] | 48.4% |
| P3 finish-line | always_long | 442 | 48.2% [42.5,54.1] | 51.8% |
| P3 finish-line | always_short | 442 | 52.0% [46.6,56.3] | 48.0% |
| P3 finish-line | oracle | 442 | 99.1% [98.0,99.8] | 0.9% |

(Los intentos de fechas de inicio vecinas comparten dias: las observaciones NO son independientes; el IC por bloques lo refleja solo en parte.)