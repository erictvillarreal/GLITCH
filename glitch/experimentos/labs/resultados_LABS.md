# resultados_LABS — ¿vale la pena perseguir los retos de Topstep Labs con geometría convexa?

Miércoles 28-oct-2026 · MODELADO RÁPIDO (no auditado). Cada reto se modela por separado, con su propio producto, bracket y tamaño. Plan elegido en el 60 % cronológico más viejo de los días reales (2 años, MES/MNQ/MGC/MCL) y **reportado en el 40 % más reciente** (≈ 200 días). Reglas: texto pegado por Eric y página de Topstep Labs (extracción automática); lo que la página no dice, SUPUESTO/DESCONOCIDO. Slippage de entrada 1 tick (media de 8 observaciones de MES, 0.9; la 8.ª inferida = 0, NO VERIFICADA); comisión por producto de la página de Topstep; stop llenado a 0.5.

## Resumen

| reto | cuota | P(pasar) / P(cobrar) a WR 47.4 / 50 / 52 % | EV por compra a WR 47.4 / 50 / 52 % | IC95 del EV a WR 50 % (días remuestreados) | P(EV > 0) a 47.4 / 50 / 52 % | ROI sobre la cuota (WR 50 %) | cota teórica sin ventaja |
|---|---|---|---|---|---|---|---|
| **$25K Static (#001)** | $75 | 21 % / 23 % / 25 % | $-30 / $-18 / $-4 | [-58, +18] | 6 % / 12 % / 19 % | -24 % | P(pasar) ≤ 33 % |
| **$50K Static (#006)** | $149 | 21 % / 23 % / 25 % | $-73 / $-40 / $-20 | [-111, +25] | 0 % / 12 % / 31 % | -27 % | P(pasar) ≤ 33 % |
| **$250K Freedom (#002)** | $499 | 17 % / 20 % / 22 % | $+216 / $+533 / $+808 | [+155, +815] | 88 % / 100 % / 100 % | +107 % | P(pasar) ≤ 40 % |
| **$1.5K Powered Up (#007)** | $99 | 4.3 % / 4.9 % / 5.6 % | $-34 / $-26 / $-16 | [-37, -11] | 0 % / 0 % / 6 % | -26 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **REF: 50K estándar ($49/intento + $149 activación)** | $49 | 28 % / 28 % / 28 % | $+31 / $+72 / $+110 | [+16, +139] | 88 % / 100 % / 100 % | +147 % | P(pasar) ≤ 40 % |
| **REF-prod: 50K estándar con el plan de producción (MES nc 40 TP 32 / SL 100 + MGC 3×364)** | $49 | 28 % / 29 % / 31 % | $+49 / $+73 / $+106 | [+63, +83] | 100 % / 100 % / 100 % | +149 % | P(pasar) ≤ 40 % |
| **(sens) $250K: XFA con DLL de $5,000** | $499 | 17 % / 20 % / 22 % | $+17 / $+223 / $+395 | — | — | +45 % | P(pasar) ≤ 40 % |
| **(sens) $250K: XFA siempre 30 micros (3 lotes)** | $499 | 17 % / 20 % / 22 % | $+216 / $+533 / $+808 | — | — | +107 % | P(pasar) ≤ 40 % |
| **(sens) $250K: pago = 25 % del saldo (en vez de 50 %)** | $499 | 17 % / 20 % / 22 % | $+64 / $+377 / $+679 | — | — | +76 % | P(pasar) ≤ 40 % |
| **(extra) $1.5K original ($39, 2 micros)** | $39 | 2.5 % / 3.4 % / 4.0 % | $-1 / $+11 / $+20 | — | — | +29 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K (#003, $49, 10 micros)** | $49 | 4.2 % / 4.6 % / 4.9 % | $+77 / $+90 / $+99 | — | — | +184 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $6K (#005, $149, 10 micros)** | $149 | 2.8 % / 3.4 % / 3.8 % | $+21 / $+54 / $+81 | — | — | +36 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K Undead (#008, $199, 50 micros)** | $199 | 4.2 % / 4.6 % / 4.9 % | $-73 / $-60 / $-51 | — | — | -30 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K Slasher (#009, $65, 20 micros)** | $65 | 0.9 % / 1.2 % / 1.4 % | $-38 / $-30 / $-24 | — | — | -47 % | P(cobrar) ≤ 2.04 % (dos rondas) |

(La cota sin ventaja sale del teorema de parada opcional: con deriva cero ningún plan puede pasar con más de L/(T+L); aquí se cumple en los resultados.)

## $25K Static (#001)

**Reglas usadas.** cuota $75 única (sin resets); meta $2,000; MLL $1,000 estático; DLL $500; consistencia 55 %; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 423 ticks, 2 contratos (k = 1.0, ρ = 1, f = 1.0). A WR 50 %: P(pasar) 23.0 %, días hasta pasar 8.5, liquidada 77 %.
**XFA (supuestos donde la página calla):** MLL $1,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $500, camino Standard: 5 días ≥ $150 netos, tope por pago $4,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 212, TP 424, 4 contratos base (k = 0.5, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $247, P(≥ 1 pago) 11 %, vida 5.8 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 21.3 % | $209 | **$-30** | $-37 | $352 |
| 50.0 % | 23.0 % | $247 | **$-18** | $-25 | $326 |
| 52.0 % | 25.3 % | $281 | **$-4** | $-11 | $296 |

## $50K Static (#006)

**Reglas usadas.** cuota $149 única (sin resets); meta $4,000; MLL $2,000 estático; DLL $1,000; consistencia 55 %; tope 40 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 423 ticks, 4 contratos (k = 1.0, ρ = 1, f = 1.0). A WR 50 %: P(pasar) 23.0 %, días hasta pasar 8.5, liquidada 77 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $1,000, camino Standard: 5 días ≥ $150 netos, tope por pago $8,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); tamaño ≤ 20 micros (la XFA 50K trae un escalado «2/3/4» sin explicar: se asume el primer escalón).
**Plan XFA elegido:** MGC, SL 212, TP 424, 9 contratos base (k = 0.5, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $472, P(≥ 1 pago) 9 %, vida 5.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 21.3 % | $356 | **$-73** | $-80 | $699 |
| 50.0 % | 23.0 % | $472 | **$-40** | $-47 | $648 |
| 52.0 % | 25.3 % | $510 | **$-20** | $-27 | $588 |

## $250K Freedom (#002)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $5,167, P(≥ 1 pago) 22 %, vida 6.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $4,132 | **$+216** | $+210 | $2,883 |
| 50.0 % | 20.0 % | $5,167 | **$+533** | $+527 | $2,498 |
| 52.0 % | 21.8 % | $5,989 | **$+808** | $+802 | $2,286 |

## $1.5K Powered Up (#007)

**Reglas usadas.** cuota $99 única (sin resets); meta $1,500; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MNQ, SL 416 ticks, TP 416 ticks, 4 contratos (k = 0.5, ρ = 1, f = 2.0). A WR 50 %: P(pasar) 22.1 %, días hasta pasar 2.7, liquidada 78 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $1,500 en la ronda del reto y **otra vez** $1,500 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $1,500 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 20.7 % | 4.30 % | **$-34** |
| 50.0 % | 22.1 % | 4.88 % | **$-26** |
| 52.0 % | 23.6 % | 5.56 % | **$-16** |

## REF: 50K estándar ($49/intento + $149 activación)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $2,000 de cierre (trailing EOD); DLL ninguno; consistencia 55 %; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 106 ticks, TP 53 ticks, 30 contratos (k = 0.25, ρ = 0.5, f = 3.0). A WR 50 %: P(pasar) 28.0 %, días hasta pasar 2.0, liquidada 72 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $150 netos, tope por pago $2,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 4 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $581, P(≥ 1 pago) 15 %, vida 8.1 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 27.7 % | $438 | **$+31** | $+28 | $177 |
| 50.0 % | 28.0 % | $581 | **$+72** | $+69 | $175 |
| 52.0 % | 28.0 % | $716 | **$+110** | $+107 | $175 |

## REF-prod: 50K estándar con el plan de producción (MES nc 40 TP 32 / SL 100 + MGC 3×364)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $2,000 de cierre (trailing EOD); DLL ninguno; consistencia 55 %; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MES, SL 100 ticks, TP 32 ticks, 40 contratos (plan fijo de producción). A WR 50 %: P(pasar) 28.6 %, días hasta pasar 2.0, liquidada 71 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $150 netos, tope por pago $2,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 364, TP 364, 3 contratos base (plan fijo de producción). A WR 50 %: cobrado esperado $575, P(≥ 1 pago) 24 %, vida 7.5 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 27.8 % | $502 | **$+49** | $+46 | $176 |
| 50.0 % | 28.6 % | $575 | **$+73** | $+70 | $171 |
| 52.0 % | 30.9 % | $653 | **$+106** | $+103 | $159 |

## (sens) $250K: XFA con DLL de $5,000

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $5,000, camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $3,614, P(≥ 1 pago) 20 %, vida 7.4 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $2,980 | **$+17** | $+11 | $2,883 |
| 50.0 % | 20.0 % | $3,614 | **$+223** | $+216 | $2,498 |
| 52.0 % | 21.8 % | $4,097 | **$+395** | $+389 | $2,286 |

## (sens) $250K: XFA siempre 30 micros (3 lotes)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $5,167, P(≥ 1 pago) 22 %, vida 6.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $4,132 | **$+216** | $+210 | $2,883 |
| 50.0 % | 20.0 % | $5,167 | **$+533** | $+527 | $2,498 |
| 52.0 % | 21.8 % | $5,989 | **$+808** | $+802 | $2,286 |

## (sens) $250K: pago = 25 % del saldo (en vez de 50 %)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $4,385, P(≥ 1 pago) 22 %, vida 8.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $3,250 | **$+64** | $+57 | $2,883 |
| 50.0 % | 20.0 % | $4,385 | **$+377** | $+370 | $2,498 |
| 52.0 % | 21.8 % | $5,397 | **$+679** | $+672 | $2,286 |

## (extra) $1.5K original ($39, 2 micros)

**Reglas usadas.** cuota $39 única (sin resets); meta $1,500; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 2 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 1 contratos (k = 1.0, ρ = 2, f = 3.0). A WR 50 %: P(pasar) 18.3 %, días hasta pasar 8.8, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $1,500 en la ronda del reto y **otra vez** $1,500 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $1,500 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 15.9 % | 2.52 % | **$-1** |
| 50.0 % | 18.3 % | 3.35 % | **$+11** |
| 52.0 % | 19.9 % | 3.95 % | **$+20** |

## (extra) $3K (#003, $49, 10 micros)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $1,000 estático; DLL ninguno; consistencia ninguna; tope 10 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MNQ, SL 416 ticks, TP 137 ticks, 9 contratos (k = 0.5, ρ = 0.33, f = 2.0). A WR 50 %: P(pasar) 21.6 %, días hasta pasar 6.1, liquidada 78 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $1,000; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 20.5 % | 4.20 % | **$+77** |
| 50.0 % | 21.6 % | 4.65 % | **$+90** |
| 52.0 % | 22.2 % | 4.95 % | **$+99** |

## (extra) $6K (#005, $149, 10 micros)

**Reglas usadas.** cuota $149 única (sin resets); meta $6,000; MLL $2,000 estático; DLL ninguno; consistencia ninguna; tope 10 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 6 contratos (k = 1.0, ρ = 2, f = 3.0). A WR 50 %: P(pasar) 18.4 %, días hasta pasar 4.5, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $6,000 en la ronda del reto y **otra vez** $6,000 en la ronda de pago, ambas con MLL estático de $2,000; el pago fijo de $6,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 16.8 % | 2.84 % | **$+21** |
| 50.0 % | 18.4 % | 3.38 % | **$+54** |
| 52.0 % | 19.6 % | 3.84 % | **$+81** |

## (extra) $3K Undead (#008, $199, 50 micros)

**Reglas usadas.** cuota $199 única (sin resets); meta $3,000; MLL $1,000 estático; DLL ninguno; consistencia ninguna; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MNQ, SL 416 ticks, TP 137 ticks, 9 contratos (k = 0.5, ρ = 0.33, f = 2.0). A WR 50 %: P(pasar) 21.6 %, días hasta pasar 6.1, liquidada 78 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $1,000; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 20.5 % | 4.20 % | **$-73** |
| 50.0 % | 21.6 % | 4.65 % | **$-60** |
| 52.0 % | 22.2 % | 4.95 % | **$-51** |

## (extra) $3K Slasher (#009, $65, 20 micros)

**Reglas usadas.** cuota $65 única (sin resets); meta $3,000; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 2 contratos (k = 1.0, ρ = 2, f = 2.0). A WR 50 %: P(pasar) 10.7 %, días hasta pasar 7.2, liquidada 89 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 9.4 % | 0.89 % | **$-38** |
| 50.0 % | 10.7 % | 1.15 % | **$-30** |
| 52.0 % | 11.7 % | 1.37 % | **$-24** |

