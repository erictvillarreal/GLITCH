# T2 — Momento de la tercera cuenta
*Rama `research/t2-third-account` (sandbox, sin producción; parte de `research/t1-combine-size` porque `origin/main` no contiene el motor). Motor `dd_cash/lever_engine.py`, convención de `structural-levers` y `stacking-timing`: liquidación explícita de la XFA, slip 0.5, fees completos, 12 meses desde 19-oct-2026, tres mundos. Script `scripts/t2_third_account.py`; tablas completas en `dd_cash/t2_third_account_report.txt`. La 2.ª cuenta se supone a las 4 semanas (día hábil 20 = lun 16-nov-2026), como recomendó `stacking-timing`.*

## Resumen (10 líneas)
1. **Hay una tercera señal distinta con datos y con estructura, pero está a medias en infraestructura**: C = MGC 9:45 > MGC 9:45 (Combine nc 26 TP 62; XFA 490×4). MES (A) y MCL (B) ya eran las dos primeras; MNQ/M2K son el mismo trade que MES (ρ 0.9–0.96) y M6E es ilíquida. Falta casi todo para ejecutarla (§3).
2. **Corrección importante a mis reportes anteriores**: el límite oficial de MCL y MGC en Combine/XFA es **30 micros** (50K), no 50. La cuenta B (MCL) se re-diseñó con nc = 30 (TP 54): el valor de 2 cuentas baja a **$9.4k justo / $5.5k con oro / $4.4k sin oro** (antes $9.5k / $6.1k / $4.8k).
3. **Valor marginal de la 3.ª cuenta (distinta, junto a la 2.ª)**: **+$4,663 justo, +$1,016 con oro, +$843 sin oro**; con 4 semanas de espera +$4,153 / +$884 / +$731; con 8 semanas +$3,692 / +$756 / +$600.
4. **Costo marginal en riesgo (historia con oro, "junto a la 2.ª")**: colchón p95 $6.9k → **$9.1k**, pico p99 $9.1k → **$12.0k**, P(año negativo) 24% → 26%, días con ≥ 2 cuentas en el MLL **10 → 30** al año, con ≥ 3 cuentas **0 → 3.3**, compras de Combine **105 → 157** al año.
5. **Esperar no vuelve la 3.ª cuenta más segura** (colchón −$0.2k por cada 4 semanas), solo menos rentable; **los condicionales sí bajan la coincidencia** (30 → 16 días ≥ 2 MLL; colchón $7.2k–$7.5k) pero **pierden ~70–80% de la ganancia** (+$0.3k con oro).
6. **Relación beneficio/riesgo pobre en historia real**: ~$0.9k/año por ~$2.2k más de colchón y +52 compras; en mundo justo es mejor (+$4.7k) pero depende de que MGC 9:45 no tenga la deriva negativa de la historia.
7. **Una 3.ª señal idéntica a MES rinde más (+$3.5k con oro) pero llega a 47 días con ≥ 2 cuentas en el MLL y 9.8 con ≥ 3**: es el patrón que el RTP describe ("multiple accounts hit the MLL in one day").
8. **Recomendación**: **evaluar el lunes 14-dic-2026 (≈ 4 semanas después de la 2.ª) y sumar la 3.ª el martes 15-dic solo si la compuerta de §4 está en verde**; si no, **posponer a la prueba de N = 20 Combines (≈ 16-feb-2027)**. Confianza **baja–media** (el beneficio histórico es pequeño y depende de la respuesta de Topstep).
9. **Dependencia**: no hay respuesta escrita de Topstep sobre RTP/compras excesivas; con 3 cuentas son ~157 compras de Combine al año (~52 por cuenta). **Sin esa respuesta, no sumar la 3.ª.**
10. **No hace falta un ejecutor multi-cuenta**: con productos distintos (MES / MCL / MGC) las claves de estado del Pi ya se separan por producto; lo que falta es una instancia por producto y cuenta (ver T4d).

## 1. Qué terceras señales existen
Retornos diarios dirigidos (entrada→flatten, normalizados por el rango mediano), 497 días: MES 9:45 vs MNQ 0.96, M2K 0.89, MGC 7:13 0.17, MGC 9:45 0.27, M6E 0.12–0.14, MCL 0.01–0.02. Estructuralmente (correlación + liquidez + misma ruta de código) el orden de candidatas para la 3.ª es: **(1) MGC 9:45**, (2) M6E (descartada: 25.7% de pase en el mundo justo y neto $1.1k por cuenta, ilíquida, ρ = 0.32 con MGC), (3) otra copia de MES (no distinta). "MES/MCL/MGC" cubre las tres clases de activo disponibles con datos; la 3.ª es MGC por exclusión.
| Cuenta | Combine → XFA | Geometría estructural (tope 30 micros MCL/MGC) |
|---|---|---|
| A (vigente) | MES 9:45 → MGC 7:13 | nc 40, TP 32 / XFA 728×3 (propuesta) |
| B | MCL 8:43 → MCL 8:43 | **nc 30, TP 54** / XFA 195×11 |
| C | MGC 9:45 → MGC 9:45 | nc 26, TP 62 / XFA 490×4 |
Nota: el stop de B (nc 30) es la liquidación del MLL a 67 ticks, 52% del rango mediano; la regla estructural (misma fracción que MES) pedía nc 50 y no es ejecutable.

## 2. Resultados — 3 cuentas, 12 meses (neto total tras $714)
"Apila" = % de trayectorias en las que se suma. "Compras" = compras de Combine al año, las 3 cuentas (proxy RTP). Columnas de riesgo: colchón p95 / pico p99 de la mayor caja acumulada negativa; días al año con ≥ 2 / ≥ 3 cuentas en el MLL.
### 2.1 Historia real CON oro (tercera distinta C)
| Momento de la 3.ª | Media | Mediana | P(<0) | P(≥$10k) | Colchón / Pico | ≥2 / ≥3 MLL | Compras | Apila |
|---|---|---|---|---|---|---|---|---|
| solo 2 cuentas | 5,501 | 4,691 | 24% | 25% | 6,917 / 9,111 | 10.0 / 0.0 | 105 | — |
| (a) con la 2.ª (día 20) | 6,517 | 5,546 | 26% | 32% | 9,124 / 12,032 | 30.4 / 3.3 | 157 | 100% |
| (b) 4 semanas después de la 2.ª (15-dic) | 6,385 | 5,414 | 26% | 31% | 8,897 / 11,780 | 28.6 / 3.0 | 153 | 100% |
| (c) 8 semanas después de la 2.ª (14-ene-2027) | 6,257 | 5,284 | 26% | 31% | 8,738 / 11,588 | 26.9 / 2.7 | 149 | 100% |
| (d) al 1.er payout de la 2.ª | 6,074 | 4,990 | 26% | 29% | 8,241 / 10,671 | 24.5 / 2.3 | 143 | 98% |
| (e1) mes 3: solo si 1.ª y 2.ª con XFA viva | 5,779 | 4,809 | 25% | 27% | 7,485 / 10,135 | 16.4 / 1.0 | 122 | 39% |
| (e2) mes 3: solo si caja 1.ª+2.ª (neta de ops) ≥ 0 | 5,791 | 4,679 | 26% | 27% | 7,161 / 9,336 | 16.8 / 1.1 | 123 | 41% |
| (e1) mes 4, XFA viva | 5,730 | 4,765 | 25% | 27% | 7,415 / 9,868 | 15.7 / 0.9 | 120 | 39% |
| (e2) mes 4, caja ≥ 0 | 5,812 | 4,666 | 26% | 27% | 7,124 / 9,207 | 17.2 / 1.1 | 124 | 49% |
| ref.: las 3 cuentas el día 0 | 6,911 | 5,994 | 25% | 34% | 9,257 / 12,338 | 33.3 / 3.7 | 166 | 100% |
### 2.2 Historia real SIN oro (tercera distinta C)
| Momento | Media | Mediana | P(<0) | P(≥$10k) | Colchón / Pico | ≥2 / ≥3 MLL | Compras | Apila |
|---|---|---|---|---|---|---|---|---|
| solo 2 cuentas | 4,357 | 3,608 | 29% | 20% | 7,415 / 9,645 | 10.5 / 0.0 | 107 | — |
| (a) con la 2.ª | 5,200 | 4,392 | 30% | 27% | 9,514 / 12,312 | 30.6 / 3.4 | 159 | 100% |
| (b) +4 semanas | 5,088 | 4,315 | 30% | 26% | 9,335 / 12,279 | 28.8 / 3.0 | 155 | 100% |
| (c) +8 semanas | 4,957 | 4,136 | 30% | 25% | 9,206 / 12,069 | 27.2 / 2.8 | 151 | 100% |
| (d) 1.er payout de la 2.ª | 4,804 | 3,923 | 31% | 25% | 8,679 / 11,183 | 24.8 / 2.3 | 145 | 98% |
| (e1) mes 3, XFA viva | 4,583 | 3,722 | 30% | 22% | 8,019 / 10,490 | 16.7 / 1.0 | 124 | 38% |
| (e2) mes 3, caja ≥ 0 | 4,596 | 3,606 | 30% | 22% | 7,666 / 9,891 | 16.7 / 1.0 | 124 | 38% |
| (e1) mes 4, XFA viva | 4,515 | 3,665 | 30% | 22% | 7,942 / 10,402 | 16.1 / 0.9 | 122 | 38% |
| (e2) mes 4, caja ≥ 0 | 4,552 | 3,548 | 30% | 22% | 7,594 / 9,782 | 17.1 / 1.1 | 125 | 45% |
| ref.: 3 cuentas el día 0 | 5,592 | 4,755 | 29% | 29% | 9,672 / 12,770 | 33.5 / 3.8 | 167 | 100% |
### 2.3 Mundo justo (productos independientes; cota optimista de diversificación)
| Momento | Media | Mediana | P(<0) | P(≥$10k) | Colchón / Pico | ≥2 / ≥3 MLL | Compras | Apila |
|---|---|---|---|---|---|---|---|---|
| solo 2 cuentas | 9,399 | 8,532 | 15% | 44% | 6,669 / 9,059 | 9.5 / 0.0 | 101 | — |
| (a) con la 2.ª | 14,062 | 13,210 | 9% | 61% | 7,297 / 10,203 | 25.8 / 2.1 | 153 | 100% |
| (b) +4 semanas | 13,552 | 12,662 | 10% | 60% | 7,341 / 10,189 | 24.4 / 1.9 | 149 | 100% |
| (c) +8 semanas | 13,091 | 12,248 | 10% | 58% | 7,275 / 10,137 | 23.0 / 1.7 | 145 | 100% |
| (d) 1.er payout de la 2.ª | 12,561 | 11,666 | 12% | 56% | 7,202 / 9,967 | 21.3 / 1.4 | 140 | 99% |
| (e1) mes 3, XFA viva | 10,846 | 9,795 | 14% | 49% | 6,843 / 9,361 | 14.6 / 0.6 | 118 | 39% |
| (e2) mes 3, caja ≥ 0 | 11,134 | 9,905 | 14% | 50% | 6,754 / 9,104 | 15.7 / 0.7 | 122 | 47% |
| (e1) mes 4, XFA viva | 10,628 | 9,568 | 14% | 48% | 6,838 / 9,327 | 14.2 / 0.6 | 117 | 40% |
| (e2) mes 4, caja ≥ 0 | 11,176 | 9,985 | 15% | 50% | 6,737 / 9,104 | 16.1 / 0.8 | 123 | 56% |
| ref.: 3 cuentas el día 0 | 14,952 | 14,134 | 9% | 64% | 7,432 / 10,310 | 28.4 / 2.4 | 161 | 100% |
**Referencia — tercera IDÉNTICA a A (A + B + A), historia CON oro:** (a) $9,018 · P(<0) 23% · colchón/pico $10.1k / $13.4k · **47.2 días ≥ 2 MLL, 9.8 días ≥ 3 MLL** · 154 compras; (b) $8,649; (c) $8,301; (d) $7,808; condicionales $6.4k–$6.6k con 20–23 días ≥ 2. Sin oro: (a) $6,822 · 48.6 / 10.2 días. Es +$3.5k de media frente a +$1.0k de la distinta, a costa de ~1.6× la coincidencia.

## 3. Qué falta para ejecutar la 3.ª señal (MGC 9:45) — inventario
| Pieza | Estado | Fuente |
|---|---|---|
| Geometría de Combine en `CANDIDATES` | **Falta**: `CANDIDATES["MGC"]` en `origin/main` es SL136/TP45, nc 30 (obsoleta); no existe MCL | `strategies/geometry_pure.py` |
| Scheduler | `geometry_scheduler.py` es agnóstico de producto (`GLITCH_PRODUCT`) y en modo real no necesita precio, pero la compuerta de entrada es **fija 9:35 CT** y la lista de feriados/flatten es la de MES; el paper de MGC no funciona (sin ticker de Yahoo) | `scheduler/geometry_scheduler.py` |
| Ejecutor Pi | Una instancia por producto sirve (claves por producto); falta resolver el **contrato activo** (la resolución actual elige el vencimiento más cercano, ver T4) y fijar la cuenta | `pi/pi_executor.py` |
| Límite de contratos | MGC y MCL: **30 micros** en Combine/XFA | Risk Adjustments (13613539) |
| Cuentas | Cada Combine/XFA/reinicio puede traer un `accountId` nuevo (el del API no es el del dashboard): el pin A5 exige actualizar el entorno en cada cambio — **NO VERIFICADO si un reinicio conserva el ID** | `pi/ARCHITECTURE.md` |
| Respuesta de Topstep sobre RTP / compras excesivas | **No existe** | pendiente de Eric |
| Datos / fills | MGC: Massive (ver T4 sobre el feed); la entrada real usa precios de ProjectX | — |

## 4. Compuerta propia y fecha recomendada para la 3.ª cuenta
Todas deben cumplirse el lunes 14-dic-2026 (≈ día 38 de la 1.ª cuenta; ≈ 10 Combines resueltos):
1. **Respuesta escrita de Topstep** que acepte ~157 compras de Combine al año y días con ≥ 2 cuentas en el MLL (sin ella: no).
2. **Compuerta de fricción de `REPORT_STACKING_TIMING` §3 en verde durante ≥ 4 semanas** con las dos primeras cuentas (slippage de entrada ≤ 1 tick, TP ≤ 1 tick de cruce, cero posiciones sin protección, ≤ 1 fallo de ejecución por 20 sesiones).
3. **Prueba de pase a N = 10**: la 1.ª cuenta tiene **≥ 1 pase** entre sus primeros 10 Combines resueltos (con 0 pases el modelo se rechaza al 2.5%).
4. **Colchón disponible**: capital de reserva ≥ **$12k** (pico p99 de 3 cuentas con oro) sin depender de los payouts.
5. **Sin advertencia ni RTP** activo en ninguna cuenta; ninguna de las dos primeras con más de 2 días ≥ 2 MLL en las últimas 4 semanas más de lo esperado (≈ 1 por cada 4 semanas con señales distintas: 10 al año).
6. **Ejecución lista**: instancia del Pi para MGC (T4) y para MCL probadas en Practice con los criterios de T4f.
**Fecha**: evaluar el **14-dic-2026**; si todo está en verde, sumar el **15-dic-2026** (momento (b), el mejor compromiso: pierde $132 frente a "con la 2.ª" en historia y baja el colchón $0.2k). **Si algo no está en verde, posponer a la prueba de N = 20 (≈ 16-feb-2027)** y no sumar antes. **Confianza: baja–media**; la ganancia histórica de la 3.ª cuenta (+$0.6k a +$1.0k) es menor que su costo en colchón (+$2k).

## 5. Supuestos y límites
- La 2.ª cuenta empieza el día 20 con señales distintas (B con tope de 30 micros); la 3.ª usa C (distinta) o A (idéntica) como referencia.
- Mundo justo: productos independientes (sin correlación entre cuentas) → diversificación optimista; en historia la correlación es la real, sobre una sola historia de 497 días.
- "XFA viva" = la cuenta está en estado XFA (activa o en espera de handoff) al día de la prueba; "caja" = suma de las dos primeras, neta de costos compartidos.
- Las compras incluyen la compra inicial, reinicios y recompras tras morir la XFA; el límite de reinicios es de 2 por cuenta por día (oficial) y el pipeline no lo alcanza.
- No se modela el RTP (umbrales públicos inexistentes), ni límites por producto del Combine (NO VERIFICADO si el máximo es por producto o total).
