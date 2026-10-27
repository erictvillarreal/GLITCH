# resultados_J4a — ¿un kill-switch por colchón del MLL mejora algo? (simulación)

**Fuente y estado.** MODELADO sobre 443 días reales de MGC (sin la ventana de oro), motor `xfa_engine`, slippage de entrada = 8 obs. (8.ª inferida = 0, NO VERIFICADA), stop 0.5. Pérdida máxima por micro supuesta: $369 (SL 364 + comisión + 3 ticks). `colchón` = balance − piso del MLL. IC95 = 30 remuestras de bloques de 5 días (8,000 vidas cada una; semillas comunes ⇒ diferencias pareadas).


### WR 50 %

| política | cobrado por XFA [IC95] | Δ vs producción (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) | P(liquidada por MLL) | P(muerte ≤ 3 días) | vida (días) |
|---|---|---|---|---|---|---|---|
| 3×364 (producción, sin guardia) | $633 [581, 651] | — | — | 32.7 % | 100.0 % | 17.5 % | 9.9 |
| guardia: nc = ⌊colchón / $369⌋ (máx 3), no opera si < $369 | $517 [477, 545] | $-116 [-133, -85] | SÍ | 30.7 % | 12.8 % | 2.5 % | 36.4 |
| guardia estricta: igual, pero no opera si el colchón < $800 | $406 [375, 427] | $-226 [-243, -199] | SÍ | 21.8 % | 6.1 % | 1.9 % | 35.8 |
| guardia solo-1-micro: con colchón < $1,200 opera 1 micro (si cabe) | $477 [447, 507] | $-156 [-171, -126] | SÍ | 33.3 % | 7.3 % | 1.1 % | 40.0 |

### WR 47.4 %

| política | cobrado por XFA [IC95] | Δ vs producción (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) | P(liquidada por MLL) | P(muerte ≤ 3 días) | vida (días) |
|---|---|---|---|---|---|---|---|
| 3×364 (producción, sin guardia) | $402 [355, 422] | — | — | 25.5 % | 100.0 % | 20.0 % | 8.4 |
| guardia: nc = ⌊colchón / $369⌋ (máx 3), no opera si < $369 | $325 [294, 346] | $-77 [-88, -54] | SÍ | 23.3 % | 11.9 % | 2.8 % | 35.3 |
| guardia estricta: igual, pero no opera si el colchón < $800 | $260 [233, 279] | $-142 [-152, -118] | SÍ | 16.3 % | 5.6 % | 2.1 % | 35.0 |
| guardia solo-1-micro: con colchón < $1,200 opera 1 micro (si cabe) | $299 [274, 323] | $-103 [-109, -77] | SÍ | 25.2 % | 6.7 % | 1.1 % | 38.9 |

Lectura: ver J4_PARCHES.md (sección a). «P(liquidada por MLL)» es la fracción de vidas que terminan con la cuenta liquidada por Topstep; con la guardia una vida también termina cuando el colchón ya no alcanza ni para 1 micro (queda sin operar, no liquidada).

## Neto anual por cuenta (cadena Combine P0 → XFA, OPS $245, horizonte 252 días; sin remuestreo de días, 30,000 vidas)

| política | WR 50 % | WR 47.4 % |
|---|---|---|
| 3×364 (producción, sin guardia) | $2,398 | $-244 |
| guardia: nc = ⌊colchón / $369⌋ (máx 3), no opera si < $369 | $445 | $-600 |
| guardia estricta: igual, pero no opera si el colchón < $800 | $-99 | $-948 |
| guardia solo-1-micro: con colchón < $1,200 opera 1 micro (si cabe) | $265 | $-695 |

(Una vida con guardia que queda sin operar se cierra en el motor tras 30 días sin operar; un operador real abandonaría la cuenta antes y volvería a comprar: el número es conservador para la guardia.)
