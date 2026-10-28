# resultados_LABS — ¿vale la pena perseguir los retos de Topstep Labs con geometría convexa?

Miércoles 28-oct-2026 · MODELADO RÁPIDO (no auditado). Cada reto se modela por separado, con su propio producto, bracket y tamaño. Plan elegido en el 60 % cronológico más viejo de los días reales (2 años, MES/MNQ/MGC/MCL) y **reportado en el 40 % más reciente** (≈ 200 días). Reglas: texto pegado por Eric y página de Topstep Labs (extracción automática); lo que la página no dice, SUPUESTO/DESCONOCIDO. Slippage de entrada = distribución empírica de 8 observaciones de MES {−1, 0, +1, +3} (la 8.ª observación inferida = 0, NO VERIFICADA); comisión por producto de la página de Topstep; stop llenado a 0.5.

## Resumen

| reto | cuota | P(pasar) / P(cobrar) a WR 47.4 / 50 / 52 % | EV por compra a WR 47.4 / 50 / 52 % | IC95 del EV a WR 50 % (días remuestreados) | P(EV > 0) a 47.4 / 50 / 52 % | ROI sobre la cuota (WR 50 %) | cota teórica sin ventaja |
|---|---|---|---|---|---|---|---|
| **$25K Static (#001)** | $75 | 21 % / 23 % / 25 % | $-30 / $-18 / $-3 | [-57, +19] | 6 % / 12 % / 19 % | -24 % | P(pasar) ≤ 33 % |
| **$50K Static (#006)** | $149 | 21 % / 23 % / 25 % | $-73 / $-40 / $-18 | [-111, +26] | 0 % / 12 % / 31 % | -27 % | P(pasar) ≤ 33 % |
| **$250K Freedom (#002)** | $499 | 17 % / 20 % / 22 % | $+218 / $+537 / $+809 | [+155, +819] | 88 % / 100 % / 100 % | +108 % | P(pasar) ≤ 40 % |
| **$1.5K Powered Up (#007)** | $99 | 2.5 % / 3.4 % / 4.0 % | $-61 / $-49 / $-39 | [-56, -32] | 0 % / 0 % / 0 % | -49 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **REF: 50K estándar ($49/intento + $149 activación)** | $49 | 21 % / 22 % / 22 % | $+12 / $+45 / $+74 | [+0, +106] | 62 % / 94 % / 100 % | +92 % | P(pasar) ≤ 40 % |
| **REF-prod: 50K estándar con el plan de producción (MES nc 40 TP 32 / SL 100 + MGC 3×364)** | $49 | 24 % / 25 % / 27 % | $+37 / $+58 / $+86 | [+51, +69] | 100 % / 100 % / 100 % | +119 % | P(pasar) ≤ 40 % |
| **(sens) $250K: XFA con DLL de $5,000** | $499 | 17 % / 20 % / 22 % | $+18 / $+225 / $+401 | — | — | +45 % | P(pasar) ≤ 40 % |
| **(sens) $250K: XFA siempre 30 micros (3 lotes)** | $499 | 17 % / 20 % / 22 % | $+218 / $+537 / $+809 | — | — | +108 % | P(pasar) ≤ 40 % |
| **(sens) $250K: pago = 25 % del saldo (en vez de 50 %)** | $499 | 17 % / 20 % / 22 % | $+66 / $+380 / $+680 | — | — | +76 % | P(pasar) ≤ 40 % |
| **(extra) $1.5K original ($39, 2 micros)** | $39 | 2.5 % / 3.4 % / 4.0 % | $-1 / $+11 / $+21 | — | — | +29 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K (#003, $49, 10 micros)** | $49 | 2.5 % / 3.4 % / 4.0 % | $+27 / $+52 / $+70 | — | — | +105 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $6K (#005, $149, 10 micros)** | $149 | 2.9 % / 3.4 % / 3.9 % | $+22 / $+55 / $+83 | — | — | +37 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K Undead (#008, $199, 50 micros)** | $199 | 2.5 % / 3.4 % / 4.0 % | $-123 / $-98 / $-80 | — | — | -49 % | P(cobrar) ≤ 6.25 % (dos rondas) |
| **(extra) $3K Slasher (#009, $65, 20 micros)** | $65 | 0.9 % / 1.2 % / 1.4 % | $-38 / $-30 / $-23 | — | — | -46 % | P(cobrar) ≤ 2.04 % (dos rondas) |

(La cota sin ventaja sale del teorema de parada opcional: con deriva cero ningún plan puede pasar con más de L/(T+L); aquí se cumple en los resultados.)

## $25K Static (#001)

**Reglas usadas.** cuota $75 única (sin resets); meta $2,000; MLL $1,000 estático; DLL $500; consistencia 55 %; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 423 ticks, 2 contratos (k = 1.0, ρ = 1, f = 1.0). A WR 50 %: P(pasar) 23.1 %, días hasta pasar 8.5, liquidada 77 %.
**XFA (supuestos donde la página calla):** MLL $1,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $500, camino Standard: 5 días ≥ $150 netos, tope por pago $4,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 212, TP 424, 4 contratos base (k = 0.5, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $248, P(≥ 1 pago) 11 %, vida 5.8 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 21.4 % | $210 | **$-30** | $-37 | $351 |
| 50.0 % | 23.1 % | $248 | **$-18** | $-25 | $325 |
| 52.0 % | 25.4 % | $282 | **$-3** | $-10 | $295 |

## $50K Static (#006)

**Reglas usadas.** cuota $149 única (sin resets); meta $4,000; MLL $2,000 estático; DLL $1,000; consistencia 55 %; tope 40 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 423 ticks, 4 contratos (k = 1.0, ρ = 1, f = 1.0). A WR 50 %: P(pasar) 23.1 %, días hasta pasar 8.5, liquidada 77 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $1,000, camino Standard: 5 días ≥ $150 netos, tope por pago $8,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); tamaño ≤ 20 micros (la XFA 50K trae un escalado «2/3/4» sin explicar: se asume el primer escalón).
**Plan XFA elegido:** MGC, SL 212, TP 424, 9 contratos base (k = 0.5, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $471, P(≥ 1 pago) 9 %, vida 5.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 21.4 % | $357 | **$-73** | $-79 | $697 |
| 50.0 % | 23.1 % | $471 | **$-40** | $-47 | $646 |
| 52.0 % | 25.4 % | $514 | **$-18** | $-25 | $586 |

## $250K Freedom (#002)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $5,182, P(≥ 1 pago) 22 %, vida 6.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $4,138 | **$+218** | $+212 | $2,881 |
| 50.0 % | 20.0 % | $5,182 | **$+537** | $+531 | $2,495 |
| 52.0 % | 21.8 % | $5,989 | **$+809** | $+803 | $2,284 |

## $1.5K Powered Up (#007)

**Reglas usadas.** cuota $99 única (sin resets); meta $1,500; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 1 contratos (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: P(pasar) 18.3 %, días hasta pasar 8.7, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $1,500 en la ronda del reto y **otra vez** $1,500 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $1,500 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 15.9 % | 2.53 % | **$-61** |
| 50.0 % | 18.3 % | 3.35 % | **$-49** |
| 52.0 % | 19.9 % | 3.97 % | **$-39** |

## REF: 50K estándar ($49/intento + $149 activación)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $2,000 de cierre (trailing EOD); DLL ninguno; consistencia 55 %; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MNQ, SL 208 ticks, TP 69 ticks, 19 contratos (k = 0.25, ρ = 0.33, f = 1.0). A WR 50 %: P(pasar) 21.6 %, días hasta pasar 5.0, liquidada 78 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $150 netos, tope por pago $2,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 4 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $584, P(≥ 1 pago) 15 %, vida 8.0 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 21.2 % | $439 | **$+12** | $+8 | $231 |
| 50.0 % | 21.6 % | $584 | **$+45** | $+40 | $227 |
| 52.0 % | 21.6 % | $718 | **$+74** | $+69 | $227 |

## REF-prod: 50K estándar con el plan de producción (MES nc 40 TP 32 / SL 100 + MGC 3×364)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $2,000 de cierre (trailing EOD); DLL ninguno; consistencia 55 %; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MES, SL 100 ticks, TP 32 ticks, 40 contratos (plan fijo de producción). A WR 50 %: P(pasar) 25.0 %, días hasta pasar 2.3, liquidada 75 %.
**XFA (supuestos donde la página calla):** MLL $2,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $150 netos, tope por pago $2,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO)
**Plan XFA elegido:** MGC, SL 364, TP 364, 3 contratos base (plan fijo de producción). A WR 50 %: cobrado esperado $577, P(≥ 1 pago) 24 %, vida 7.5 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 24.4 % | $502 | **$+37** | $+34 | $201 |
| 50.0 % | 25.0 % | $577 | **$+58** | $+55 | $196 |
| 52.0 % | 26.8 % | $655 | **$+86** | $+83 | $183 |

## (sens) $250K: XFA con DLL de $5,000

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL $5,000, camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $3,622, P(≥ 1 pago) 20 %, vida 7.4 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $2,986 | **$+18** | $+12 | $2,881 |
| 50.0 % | 20.0 % | $3,622 | **$+225** | $+219 | $2,495 |
| 52.0 % | 21.8 % | $4,121 | **$+401** | $+395 | $2,284 |

## (sens) $250K: XFA siempre 30 micros (3 lotes)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $5,182, P(≥ 1 pago) 22 %, vida 6.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $4,138 | **$+218** | $+212 | $2,881 |
| 50.0 % | 20.0 % | $5,182 | **$+537** | $+531 | $2,495 |
| 52.0 % | 21.8 % | $5,989 | **$+809** | $+803 | $2,284 |

## (sens) $250K: pago = 25 % del saldo (en vez de 50 %)

**Reglas usadas.** cuota $499 única (sin resets); meta $15,000; MLL $10,000 de cierre (trailing EOD); DLL $5,000; consistencia 55 %; tope 250 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (Combine):** MGC, SL 423 ticks, TP 846 ticks, 11 contratos (k = 1.0, ρ = 2, f = 0.5). A WR 50 %: P(pasar) 20.0 %, días hasta pasar 8.1, liquidada 80 %.
**XFA (supuestos donde la página calla):** MLL $10,000 estático que pasa a $0 tras el 1.er pago (DOCUMENTADO), DLL no indicado (se modela sin DLL), camino Standard: 5 días ≥ $1,000 netos, tope por pago $25,000, pago = 50 % del saldo (**SUPUESTO**: la página remite a la política de pagos), división 90/10 (SUPUESTO), mínimo $125 (SUPUESTO); escalado por saldo 30/50/100/150/250 micros (SUPUESTO)
**Plan XFA elegido:** MGC, SL 423, TP 846, 23 contratos base (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: cobrado esperado $4,394, P(≥ 1 pago) 22 %, vida 8.6 días.

| WR | P(pasar) | cobrado por XFA | EV por compra = P·cobrado − cuota | EV tras API ($14.30/mes por cuenta activa) | costo por XFA alcanzada = cuota / P |
|---|---|---|---|---|---|
| 47.4 % | 17.3 % | $3,261 | **$+66** | $+60 | $2,881 |
| 50.0 % | 20.0 % | $4,394 | **$+380** | $+373 | $2,495 |
| 52.0 % | 21.8 % | $5,398 | **$+680** | $+673 | $2,284 |

## (extra) $1.5K original ($39, 2 micros)

**Reglas usadas.** cuota $39 única (sin resets); meta $1,500; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 2 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 1 contratos (k = 1.0, ρ = 2, f = 3.0). A WR 50 %: P(pasar) 18.3 %, días hasta pasar 8.7, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $1,500 en la ronda del reto y **otra vez** $1,500 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $1,500 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 15.9 % | 2.53 % | **$-1** |
| 50.0 % | 18.3 % | 3.35 % | **$+11** |
| 52.0 % | 19.9 % | 3.97 % | **$+21** |

## (extra) $3K (#003, $49, 10 micros)

**Reglas usadas.** cuota $49 única (sin resets); meta $3,000; MLL $1,000 estático; DLL ninguno; consistencia ninguna; tope 10 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 2 contratos (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: P(pasar) 18.3 %, días hasta pasar 8.7, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $1,000; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 15.9 % | 2.53 % | **$+27** |
| 50.0 % | 18.3 % | 3.35 % | **$+52** |
| 52.0 % | 19.9 % | 3.97 % | **$+70** |

## (extra) $6K (#005, $149, 10 micros)

**Reglas usadas.** cuota $149 única (sin resets); meta $6,000; MLL $2,000 estático; DLL ninguno; consistencia ninguna; tope 10 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 6 contratos (k = 1.0, ρ = 2, f = 3.0). A WR 50 %: P(pasar) 18.4 %, días hasta pasar 4.6, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $6,000 en la ronda del reto y **otra vez** $6,000 en la ronda de pago, ambas con MLL estático de $2,000; el pago fijo de $6,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 16.9 % | 2.85 % | **$+22** |
| 50.0 % | 18.4 % | 3.39 % | **$+55** |
| 52.0 % | 19.6 % | 3.86 % | **$+83** |

## (extra) $3K Undead (#008, $199, 50 micros)

**Reglas usadas.** cuota $199 única (sin resets); meta $3,000; MLL $1,000 estático; DLL ninguno; consistencia ninguna; tope 50 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 2 contratos (k = 1.0, ρ = 2, f = 1.0). A WR 50 %: P(pasar) 18.3 %, días hasta pasar 8.7, liquidada 82 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $1,000; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 15.9 % | 2.53 % | **$-123** |
| 50.0 % | 18.3 % | 3.35 % | **$-98** |
| 52.0 % | 19.9 % | 3.97 % | **$-80** |

## (extra) $3K Slasher (#009, $65, 20 micros)

**Reglas usadas.** cuota $65 única (sin resets); meta $3,000; MLL $500 estático; DLL ninguno; consistencia ninguna; tope 20 micros; vence a los 90 días (≈ 63 hábiles).
**Plan elegido (cada ronda):** MGC, SL 423 ticks, TP 846 ticks, 2 contratos (k = 1.0, ρ = 2, f = 2.0). A WR 50 %: P(pasar) 10.8 %, días hasta pasar 7.2, liquidada 89 %.
**Estructura (DOCUMENTADA, extracción de la página y de una publicación de Topstep): dos rondas.** Hay que ganar $3,000 en la ronda del reto y **otra vez** $3,000 en la ronda de pago, ambas con MLL estático de $500; el pago fijo de $3,000 se cobra una vez (100 %, sin división) y la cuenta se cierra. Por eso P(cobrar) = P(ronda)².

| WR | P(pasar una ronda) | P(cobrar) = P² | EV = P²·$1,500 − $99 |
|---|---|---|---|
| 47.4 % | 9.4 % | 0.89 % | **$-38** |
| 50.0 % | 10.8 % | 1.16 % | **$-30** |
| 52.0 % | 11.9 % | 1.40 % | **$-23** |

