# resultados_OPT_XFA — techo de lo que cobra y dura una XFA con tamaño y cobro óptimos (MGC, XFA 50K)

**Estado:** MODELADO. DP entrenada en 292 días (60 % más viejo), evaluada en 151 días (40 % reciente) con fricciones y reglas completas. «seguro» = nunca más de 4 micros; «ancho» incluye 6 y 8 (con 8 micros el piso del MLL, no el SL, es la barrera: es una lotería que además se parece al patrón de «tamaño máximo» del RTP; se muestra como techo, no como recomendación).

| bracket (SL = TP, ticks) | política | cobrado por XFA | Δ vs 3 micros fijos (pareado ± IC95) | P(≥ 1 pago) | vida (días) | P(muerte sin cobrar) | pagos por XFA |
|---|---|---|---|---|---|---|---|
| 273 | 3 micros fijos | $511 | — | 30 % | 8.1 | 70 % | 0.43 |
| 273 | mejor tamaño FIJO (4 micros) | $527 | +15 | 21 % | 6.6 | 79 % | 0.34 |
| 273 | **DP óptima, seguro (≤ 4 micros)** | **$549** | **+38 ± 9** | 33 % | 12.6 | 67 % | 0.60 |
| 273 | 3 micros fijos | $511 | — | 30 % | 8.1 | 70 % | 0.43 |
| 273 | mejor tamaño FIJO (4 micros) | $527 | +15 | 21 % | 6.6 | 79 % | 0.34 |
| 273 | **DP óptima, ancho (≤ 8 micros: «lotería»)** | **$729** | **+218 ± 13** | 40 % | 11.5 | 60 % | 0.70 |
| 364 | 3 micros fijos | $566 | — | 24 % | 7.4 | 76 % | 0.38 |
| 364 | mejor tamaño FIJO (3 micros) | $566 | +0 | 24 % | 7.4 | 76 % | 0.38 |
| 364 | **DP óptima, seguro (≤ 4 micros)** | **$645** | **+79 ± 13** | 28 % | 11.6 | 72 % | 0.53 |
| 364 | 3 micros fijos | $566 | — | 24 % | 7.4 | 76 % | 0.38 |
| 364 | mejor tamaño FIJO (3 micros) | $566 | +0 | 24 % | 7.4 | 76 % | 0.38 |
| 364 | **DP óptima, ancho (≤ 8 micros: «lotería»)** | **$866** | **+299 ± 17** | 36 % | 12.7 | 64 % | 0.66 |
| 546 | 3 micros fijos | $653 | — | 19 % | 8.1 | 81 % | 0.39 |
| 546 | mejor tamaño FIJO (4 micros) | $660 | +7 | 16 % | 7.5 | 84 % | 0.37 |
| 546 | **DP óptima, seguro (≤ 4 micros)** | **$796** | **+143 ± 19** | 29 % | 10.7 | 71 % | 0.54 |
| 546 | 3 micros fijos | $653 | — | 19 % | 8.1 | 81 % | 0.39 |
| 546 | mejor tamaño FIJO (4 micros) | $660 | +7 | 16 % | 7.5 | 84 % | 0.37 |
| 546 | **DP óptima, ancho (≤ 8 micros: «lotería»)** | **$905** | **+252 ± 22** | 29 % | 11.2 | 71 % | 0.59 |
| 728 | 3 micros fijos | $782 | — | 19 % | 9.3 | 81 % | 0.45 |
| 728 | mejor tamaño FIJO (4 micros) | $813 | +31 | 16 % | 9.6 | 84 % | 0.46 |
| 728 | **DP óptima, seguro (≤ 4 micros)** | **$957** | **+176 ± 25** | 30 % | 12.1 | 70 % | 0.61 |
| 728 | 3 micros fijos | $782 | — | 19 % | 9.3 | 81 % | 0.45 |
| 728 | mejor tamaño FIJO (4 micros) | $813 | +31 | 16 % | 9.6 | 84 % | 0.46 |
| 728 | **DP óptima, ancho (≤ 8 micros: «lotería»)** | **$1,042** | **+260 ± 28** | 28 % | 12.6 | 72 % | 0.64 |

## Tamaño de la DP (conjunto seguro) con **cobro inmediato** en cuanto sea elegible (lo que Eric quiere: cobrar ya)

| bracket | cobrado por XFA | Δ vs 3 micros fijos (pareado ± IC95) | P(≥ 1 pago) | mediana de días al 1.er pago | cobrado a 30 días |
|---|---|---|---|---|---|
| 273 | $559 | +48 ± 9 | 37 % | 8 | $522 (3 fijos: $483) |
| 364 | $676 | +110 ± 13 | 30 % | 8 | $596 (3 fijos: $507) |
| 546 | $812 | +159 ± 19 | 30 % | 9 | $675 (3 fijos: $508) |
| 728 | $963 | +181 ± 25 | 30 % | 10 | $741 (3 fijos: $533) |

## Forma de la política DP (SL = TP = 364, conjunto seguro): contratos por saldo y días ganadores acumulados (fase con el piso ya en $0 = después de +$2,000 o del 1.er pago)

| saldo | wd = 0 | wd = 1 | wd = 2 | wd = 3 | wd = 4 | wd = 5 (¿cobra ya?) |
|---|---|---|---|---|---|---|
| $100 | 3 | 3 | 3 | 3 | 3 | 3 / sigue |
| $300 | 4 | 4 | 4 | 4 | 4 | 4 / sigue |
| $500 | 1 | 1 | 1 | 1 | 1 | 1 / sigue |
| $1,000 | 4 | 4 | 4 | 4 | 1 | 1 / sigue |
| $1,500 | 1 | 1 | 1 | 1 | 1 | 1 / sigue |
| $2,000 | 1 | 1 | 1 | 1 | 1 | 1 / sigue |
| $3,000 | 1 | 1 | 1 | 1 | 1 | 1 / sigue |
| $4,000 | 1 | 1 | 1 | 1 | 1 | 1 / sigue |

## Fase inicial (el piso todavía puede subir: saldo < +$2,000 y sin pago): contratos de la DP según pico y saldo (SL = TP = 364, conjunto seguro, wd = 0)

| pico | saldo = pico (sin caída) | saldo = pico − $500 | saldo = pico − $1,000 | saldo = pico − $1,500 |
|---|---|---|---|---|
| $0 | 4 | 1 | 4 | 1 |
| $500 | 4 | 1 | 4 | 1 |
| $1,000 | 4 | 1 | 2 | 1 |
| $1,500 | 4 | 1 | 2 | 1 |
