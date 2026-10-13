# T1 — Tamaño de posición del Combine (decisión del vie 16-oct)
*Rama `research/t1-combine-size` (sandbox, sin producción). Motor `dd_cash/lever_engine.py`, convención de `structural-levers`: liquidación explícita de la XFA, slip de stop 0.5, fees completos, 12 meses desde 19-oct-2026, tres mundos (justo / real con oro / real sin oro), comisión $1.22/contrato RT. Script `scripts/t1_combine_size.py`; salida `dd_cash/t1_combine_size_report.txt`. Nota de ramas: `origin/main` no contiene el motor de investigación (vive en `research/stacking-timing`), así que esta rama parte de esa; ninguna rama toca código de producción.*

## Resumen (10 líneas)
1. **Recomendación: arrancar el Combine con nc = 40** (el tamaño que Eric ya confirmó). Confianza **alta** en el orden de las opciones (aparece igual en los 3 mundos y con ambas XFA), **media** en los dólares absolutos (40 contratos nunca se han ejecutado en vivo).
2. **Cada contrato menos cuesta dinero**: neto anual de 1 cuenta con TP32 — nc 40: $3,040 / $2,632 / $1,127 (justo / con oro / sin oro); nc 25: $1,238 / $978 / −$114; nc 16: $1,178 / $820 / −$82; nc 10: −$34 / −$242 / −$659.
3. **nc = 10 no es la estrategia validada**: el TP40 rinde $488 netos, la meta de $3,000 exige **7 días de TP** (no 6; $500 es bruto) y el pase por intento baja a **20.5%** (mediana de 10 días hasta pasar, vs 2 días con nc 40); neto anual negativo con P(año negativo) 62–72%. Los resultados de Practice con 10 contratos **no validan** el nc = 40.
4. **El 33% de pase es solo nc = 40 con TP32** (31.0% / 32.7% / 32.4%); el 26% es nc = 40 con TP40 (24.2% / 25.7% / 25.4%). Con nc = 16 o 25 el pase queda en 22–26% y **la ventaja del TP32 desaparece** (con nc 25, TP32 rinde menos que TP40).
5. **Perfil nc = 25, TP50, SL40**: pase 26.2% / 28.1% / 27.3%, neto $1,625 / $1,457 / $271; no usa más del 50% del máximo y una pérdida no liquida la cuenta ($1,250), pero rinde $0.9k–$1.4k menos al año que nc 40 TP32.
6. **Límite oficial verificado**: Combine 50K = 5 minis = **50 micros** por cuenta (10:1). **MGC y MCL: 30 micros** en Combine/XFA (restricción temporal por volatilidad). MES sin restricción salvo ventana de CPI (3 micros, 10 min). Practice: **150K y 15 lotes**, 1 cuenta, reset gratis 10/día.
7. **Costo por intento** ≈ $113–155 (cuota $49 + comisiones de ~1.6 trades por intento); **costo por pase** $558 (nc 40 TP32) a $875 (nc 10 TP32).
8. **Riesgo de nc = 40 es barato**: un intento perdido cuesta ~$127; lo que cambia con 40 contratos es que casi todo stop es una liquidación del MLL (43–49% de los días de Combine).
9. **Con nc = 40 hay que medir en la primera semana** slippage de entrada y llenado del TP (compuerta de `REPORT_STACKING_TIMING`); si el slippage de entrada supera 2 ticks, el pase baja ~3.7 puntos.
10. **Alerta de código (NO VERIFICADO en ejecución)**: con `GLITCH_PI_NC_MAX` < 40 el Pi escribe P&L de menos contratos en el **mismo historial** del que el scheduler deriva PASE/QUIEBRE (`_attempt_pnl` suma `pnl` crudo): las corridas de Practice a nc = 10 contaminarían el estado de intento del paper.

## 1. (a) Límites oficiales de contratos — verificación (help.topstep.com, 12-oct-2026)
| Dato | Valor | Fuente / estado |
|---|---|---|
| Combine 50K, máximo | **5 minis = 50 micros** "por cuenta", 10:1; "nunca estás obligado a operar el máximo" | Trading Combine Parameters (8284197) — **VERIFICADO** |
| ¿Por producto o total? ¿Orden rechazada o liquidación al excederlo? | El artículo solo dice "por cuenta" | **NO VERIFICADO** |
| MGC y MCL (restringidos) en Combine, XFA y Pro | **30 / 60 / 90 micros** (50K / 100K / 150K); "temporal, mientras la volatilidad esté elevada" | Risk Adjustments (13613539) — **VERIFICADO** (la página es inconsistente en otra sección: MCL = 3/6/9; el 30/60/90 es el de Combine/XFA) |
| MGC en XFA 50K (escalado) | 12 micros bajo $1,500, 18 en $1,500, 31 desde $2,000 | misma página — VERIFICADO |
| MES | sin restricción de tamaño; **ventana de CPI**: 10 minutos (5 antes, 5 después de la publicación) con aperturas limitadas a **3 micros** en 50K | misma página — VERIFICADO. La entrada de MES (9:45 CT) y la de MGC (7:13 CT) quedan fuera de una publicación de 7:30 CT; **otras ventanas (FOMC, etc.) NO VERIFICADO** |
| Labs: Combine estático 50K | 4 minis / 40 micros; MCL y MGC 25 lotes | Topstep Labs (15520357) — otro producto, no aplica al Combine estándar |
| Practice | **150K** sin importar el Combine, **15 lotes**, 1 cuenta a la vez, reset gratis hasta 10/día | Practice Account (8284134) — VERIFICADO. No se publica 2.ª Practice ni acceso por API |
| Resets del Combine | **2 por cuenta por calendario**; compras de Combine "sin límite" | Reset Purchase Limits (10370307) — VERIFICADO |
Consecuencia para el diseño: `_validate_signal` del Pi acepta nc ≤ 40, coherente con 50 micros; la cuenta MCL del portafolio de `structural-levers` (nc = 50) **no es ejecutable**: tope 30.

## 2. (b) Tabla del motor (XFA vigente Cerebro 2: MGC 364×3)
Combine: MLL $2,000 en tiempo real, consistencia 55%, ≥ 2 días, SL 100 ticks salvo indicación. "Pase/intento" con un solo intento; "días a pase" = mediana de días hábiles hasta pasar, solo los intentos que pasan (mundo justo); "liq<SL" = % de días de Combine en que hubo stop **y** la distancia al MLL era menor que el SL nominal (el stop fue la liquidación del MLL); "stop/día" = % de días de Combine con stop. Neto de 1 cuenta = media a 12 meses tras $714 compartidos (el pipeline recompra Combine y activa XFA).
| nc | TP | SL | TP neto $ | Días de TP necesarios | Pase/intento justo / CON / SIN | Días a pase | liq<SL | stop/día | Neto 1 cuenta justo / CON / SIN | P(<0) justo / CON / SIN | Intentos/año | $/intento | $/pase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 40 | 100 | 488 | 7 | 20.5 / 20.3 / 21.8% | 10 | 10% | 26% | 21 / −205 / −628 | 62 / 65 / 70% | 27 | 139 | 829 |
| 10 | 32 | 100 | 388 | 8 | 21.4 / 21.1 / 22.1% | 13 | 8% | 23% | −34 / −242 / −659 | 63 / 66 / 72% | 24 | 155 | 875 |
| 16 | 40 | 100 | 780 | 4 | 25.0 / 25.2 / 25.4% | 4 | 6% | 25% | 1,336 / 914 / 11 | 44 / 48 / 57% | 44 | 113 | 599 |
| 16 | 32 | 100 | 620 | 5 | 25.0 / 24.8 / 25.6% | 5 | 5% | 21% | 1,178 / 820 / −82 | 46 / 49 / 59% | 40 | 123 | 642 |
| 25 | 40 | 100 | 1,220 | 3 | 24.2 / 25.8 / 25.8% | 3 | 35% | 35% | 1,740 / 1,439 / 219 | 42 / 43 / 54% | 56 | 115 | 623 |
| 25 | 32 | 100 | 970 | 4 | 22.5 / 23.7 / 23.3% | 4 | 30% | 30% | 1,238 / 978 / −114 | 46 / 48 / 58% | 53 | 127 | 714 |
| **25** | **50** | **40** | 1,532 | 2 | 26.2 / 28.1 / 27.3% | 2 | 24% | 59% | 1,625 / 1,457 / 271 | 43 / 43 / 54% | 47 | 135 | 663 |
| 40 | 40 | 100 | 1,951 | 2 | 24.2 / 25.7 / 25.4% | 2 | 49% | 49% | 2,073 / 1,743 / 347 | 39 / 40 / 52% | 65 | 124 | 662 |
| **40** | **32** | **100** | 1,551 | 2 | **31.0 / 32.7 / 32.4%** | 2 | 43% | 43% | **3,040 / 2,632 / 1,127** | **31 / 32 / 44%** | 55 | 127 | **558** |
Con la XFA propuesta (728×3, pendiente de aprobación) el orden es idéntico: nc 40 TP32 → 5,332 / 3,190 / 2,011; nc 40 TP40 → 4,193 / 2,237 / 1,141; nc 25 TP40 → 3,599 / 1,842 / 952; nc 25 TP50 SL40 → 3,316 / 1,824 / 879; nc 16 TP40 → 2,856 / 1,259 / 544; nc 10 TP40 → 753 / −42 / −377.
"Días de TP necesarios" = ceil($3,000 / TP neto), mínimo 2 por la consistencia del 55% (n días iguales cumplen el 55% si n ≥ 2); con nc 40 TP32 el margen es $102 (2 × $1,551 = $3,102): sensible a la comisión (TP31 ya es filo de navaja, ver `REPORT_TP32_COSTS`).
"$/intento" = $49 + comisiones esperadas por intento; "$/pase" = $/intento ÷ pase + $149 de activación.

## 3. (c) ¿Qué parte del 26–33% aplica a cada nc? ¿Está validado nc = 10?
- **26% → nc = 40 con TP40** (24.2 / 25.7 / 25.4%); **33% → nc = 40 con TP32** (31.0 / 32.7 / 32.4%, techo de juego justo 32.7%). Esas dos cifras no se pueden aplicar a otros tamaños.
- **El pase depende poco de nc con TP40 (20–26%) y mucho del número de días de TP necesarios**: con nc ≤ 25 se necesitan 3 a 8 días de TP en lugar de 2, y cada día adicional es otra oportunidad de quiebre. La ventaja del TP32 existe solo si 2 TP suman ≥ $3,000 (nc = 40).
- **nc = 10 con los ticks de producción (SL100/TP40) es otra estrategia**: TP $488 netos → **7 días de TP** (la cuenta de $500 es bruta), pase 20.5%, mediana de **10 días** hasta pasar y neto anual negativo con oro o sin oro. Un stop de 100 ticks cuesta $1,263 (63% del MLL), así que dos pérdidas quiebran. **Validado en el sentido de que el motor lo calcula y los tres mundos coinciden; no validado en el sentido de que no hay evidencia en vivo de nada de esto** (ni a 10 ni a 40). La validación original (G2, backtest, pase 26%) es a nc = 40.
- `GLITCH_PI_NC_MAX` (commit `2ed2ec2`, "reduces size only; ticks unchanged") es exactamente una fila nc < 40 de esta tabla: **el Practice a 10 contratos mide ejecución (fills, API), no la probabilidad de pase** de lo que se va a operar el 19-oct.
- **Alerta**: `geometry_scheduler._attempt_pnl` suma `pnl` crudo del historial compartido y el Pi escribe en él con el nc operado; con `NC_MAX` = 10 el P&L real (1/4 del paper) se mezcla en la misma cuenta de intento. **NO VERIFICADO en ejecución; revisar antes de dejar el Pi con tope en paralelo al paper.**

## 4. (d) Recomendación para el vie 16-oct
1. **Decisión: operar el Combine con nc = 40** y, si Eric aprueba (regla 4 de CLAUDE.md), **TP32** (+$0.8k a +$1.0k por cuenta y año respecto de TP40 con nc 40). **Confianza: alta** en el ranking (todos los mundos, ambas XFA), **media** en el nivel.
2. **Por qué no reducir**: reducir el tamaño cuesta entre $0.9k y $3.1k por cuenta al año y sube P(año negativo) de 31–44% a 43–72%; el único beneficio es no ser "máximo en la mayoría de los trades" (nc 40 es 80% del tope de 50 micros; el umbral del RTP es **NO VERIFICADO**). Una intermedia razonable si Eric quiere bajar riesgo percibido: **nc = 25, TP50, SL40** (neto ≈ la mitad con y sin oro justo/CON, ≈ un cuarto sin oro; pase 26–28%).
3. **Riesgo real de nc = 40**: no es el capital (un intento perdido ≈ $127); es la fricción de ejecución de 40 contratos (slippage de entrada de 1 tick = −$0.37k por cuenta y −1.9 puntos de pase). Medir en la primera semana con los límites de `REPORT_STACKING_TIMING` §3.
4. **Plan de contingencia**: si en las primeras ~15 entradas el slippage medio de entrada es > 2 ticks, o el TP necesita > 2 ticks de cruce para llenarse, pasar a nc = 25 TP50 SL40 (conserva ~85% del pase) y revisar.
5. **No** usar el Practice a 10 contratos como evidencia del pase del Combine; usarlo para verificar el bracket, el flatten y los fills.

## 5. Supuestos y límites
- Barras de 5 minutos, un trade al día, SL primero en barras ambiguas, TP al tocar, slip de stop 0.5; el stop del Combine con nc ≥ 25 es en su mayoría la liquidación del MLL.
- "Días a pase" y "liq<SL" se midieron en el mundo justo; en historia real los pases por intento difieren ≤ 1.7 puntos.
- No se modelan CPI/FOMC ni límites por producto del Combine (NO VERIFICADO si el máximo es por producto o total).
- Neto = media de 20,000 trayectorias; la historia real es una sola de 497 días.

## 6. Anexo — hora de entrada real (9:35) vs. la del modelo (9:45)
El scheduler de producción (`origin/main`, `ENTRY_GATE_MINUTES = 9:35 CT`) deja entrar al Pi desde las 9:35; todo el modelo (tablas first-touch, `structural-levers`, esta tabla) entra a las 9:45. Sensibilidad con nc = 40 (`scripts/t1_entry_time_check.py`, `dd_cash/t1_entry_time_report.txt`): pase por intento TP32 en el mundo justo = 30.6% (9:35), 30.3% (9:40), 31.0% (9:45), 30.0% (9:50), 29.3% (10:00); neto anual justo $3,058 / $2,915 / $3,040 / $2,915 / $2,825. En historia real el pase oscila 29–36% (ruido de una sola historia, sin patrón). **Conclusión: la diferencia 9:35 vs 9:45 no cambia nada material**; la hora exacta de entrada del Pi (hasta el límite de 10:00 CT) no es una palanca.
