# REPORTE B — Dirección práctica (¿long o short hoy?) — 20-oct-2026

Rama `experimentos-research`. Hipótesis, reglas, parámetros y criterios **pre-registrados antes de cualquier resultado** (`PREREGISTRO.md`: commits `0b81a9b` original, `0d13941` enmienda 1, `cf81a01` enmienda 2, `e2c7e2a` enmienda 3; las enmiendas solo definen cómo se mide y se registraron antes de calcular reglas). Reproducible: `python run_partB.py` (5 s), `python lectura_hoy.py`. Datos: `mes_5min_2y.parquet`, 443 días de evaluación (2024-11-04 → 2026-08-25) tras 50 de calentamiento, serie diaria ajustada por los 8 rolls de contrato.

## Veredicto

**Ninguna de las tres reglas pasa D2 — no hay base para elegir lado.** Se sigue con `alternate` (o con el criterio de menor riesgo operativo). Un resultado negativo es válido y es el resultado.

| regla | días operados | P(TP-primero) regla | `alternate` | siempre LONG | (a) gana a `alternate` en bloques (≥ 7/10) | (b) dif. media pp [IC98.3 %] | (c) pierde vs LONG (≤ 3/10) | (d) dif. sin ventana dominante | veredicto |
|---|---|---|---|---|---|---|---|---|---|
| R1 tendencia simple | 443 | 51.4 % | 55.5 % | 52.3 % | 4/10 ✗ | −4.18 [−11.17, +3.39] ✗ | 4/10 ✗ | −5.61 ✗ | no pasa |
| R2 sesgo largo + baja confirmada | 443 | 54.0 % | 55.5 % | 52.3 % | 5/10 ✗ | −1.58 [−8.13, +5.87] ✗ | 1/10 ✓ | −2.61 ✗ | no pasa |
| R3 R2 + día saltado | 358 | 53.1 % | 56.1 % | 49.3 % | 4/10 ✗ | −3.07 [−10.67, +5.08] ✗ | 0/10 ✓ | −3.61 ✗ | no pasa |

Falla (a), (b) y (d) en las tres (R1 falla además (c)). Las reglas rinden **menos** que alternar en la muestra (R1 −4.2 pp, R2 −1.6 pp, R3 −3.1 pp); ningún IC al 98.3 % excluye cero y todos incluyen ambos signos. Esto es lo que predice la hipótesis nula: más de 1,800 configuraciones previas no hallaron ventaja de dirección y el reality check de Westfall–Young del 8-oct (productos × horas, p corregido 0.085) tampoco.

## Controles y reglas (medida base: nc = 40, colchón $2,000, TP 32/SL 100, slip de entrada {1,3} promediado)

| regla / control | días operados | P(TP-primero) | P(liquidar 1 día) | ticks netos medios/día | P(TP) sin la ventana dominante |
|---|---|---|---|---|---|
| R1 | 443 | 51.4 % | 48.6 % | −4.54 | 51.8 % |
| R2 | 443 | 54.0 % | 46.0 % | −2.75 | 54.8 % |
| R3 | 358 | 53.1 % | 46.9 % | −3.36 | 54.8 % |
| `alternate` (producción) | 443 | 55.5 % | 44.0 % | −1.58 | 57.4 % |
| siempre LONG | 443 | 52.3 % | 47.7 % | −3.92 | 53.4 % |
| siempre SHORT | 443 | 54.7 % | 44.8 % | −2.12 | 54.4 % |
| aleatorio (1,000 corridas) | 443 | 53.5 % (p2.5–p97.5: 49.3–57.7) | — | — | — |
| oráculo (ex post, informativo) | 443 | 99.1 % | 0.9 % | +28.40 | 99.5 % |

`alternate` queda en 55.5 %, **dentro del intervalo del azar** (49.3–57.7 %): no hay evidencia de que ninguna regla ni ninguna alternancia sea distinta de lanzar una moneda. El P(TP-primero) cercano a 55 % es la barrera nominal (40/72 = 55.6 %), no una ventaja.

## D1 — asimetría LONG vs SHORT por bloque (descriptivo)

| bloque | fechas | LONG | SHORT | LONG − SHORT |
|---|---|---|---|---|
| 1 | 2024-11-04 → 2025-01-10 | 69.3 % | 45.5 % | +23.9 pp |
| 2 | 2025-01-13 → 2025-03-20 | 58.0 % | 51.1 % | +6.8 |
| 3 | 2025-03-21 → 2025-05-22 | 50.0 % | 56.8 % | −6.8 |
| 4 | 2025-05-23 → 2025-07-29 | 38.6 % | 56.8 % | −18.2 |
| 5 | 2025-07-30 → 2025-09-30 | 40.9 % | 60.2 % | −19.3 |
| 6 | 2025-10-01 → 2025-12-03 | 61.4 % | 53.4 % | +8.0 |
| 7 | 2025-12-04 → 2026-02-09 | 52.3 % | 56.8 % | −4.5 |
| 8 | 2026-02-10 → 2026-04-15 | 47.7 % | 52.3 % | −4.5 |
| 9 | 2026-04-16 → 2026-06-17 | 60.2 % | 47.7 % | +12.5 |
| 10 | 2026-06-18 → 2026-08-25 | 44.7 % | 66.0 % | −21.3 |
| **total** | 443 días | 52.3 % | 54.7 % | **−2.5 pp** [IC98.3 %: −13.0, +7.8] |

Sin la ventana dominante (2025-04-09 → 2025-07-08, +1,124.8 puntos, definida solo con precio): LONG 53.4 % / SHORT 54.4 % / −1.0 pp [−12.9, +10.4]. **El signo de la asimetría cambia 5 veces entre los 10 bloques consecutivos**: es régimen y azar, no una ventaja. Un rally de 12 meses no se tradujo en ventaja del lado largo (LONG 52.3 % vs SHORT 54.7 %).

Las **8 sesiones en vivo** (anécdota que el encargo pide): **NO DISPONIBLE** localmente — viven en `geometry_mestest_log.json` del Gist y requieren un token que este agente no maneja. Eric puede exportar ese JSON y se agrega la tabla con n = 8, rotulada como anécdota. (Con n = 8 no habría cambiado nada de D2: la hipótesis “longs ganan, shorts pierden en 8 sesiones” ya figura como p ≈ 0.14 en el encargo.)

## Puente a P(pase del Combine) (M2h: un intento por fecha de inicio, resultados reales de cada día)

| tamaño | regla de lado | intentos | P(pase) [IC95 % por bloques] | P(liquidación) |
|---|---|---|---|---|
| P0 40 fijo | R1 | 443 | 30.9 % [24.6, 36.1] | 69.1 % |
| P0 40 fijo | R2 | 442 | 33.0 % [27.1, 38.9] | 67.0 % |
| P0 40 fijo | R3 | 439 | 34.6 % [28.9, 41.5] | 65.4 % |
| P0 40 fijo | `alternate` | 442 | **35.7 %** [30.5, 40.5] | 64.3 % |
| P0 40 fijo | siempre LONG | 442 | 32.4 % [26.5, 38.5] | 67.6 % |
| P0 40 fijo | siempre SHORT | 443 | 35.2 % [29.8, 40.4] | 64.8 % |
| P0 40 fijo | oráculo | 442 | 98.9 % | 1.1 % |
| P3 finish-line | R1 / R2 / R3 | 443 / 442 / 439 | 47.4 % / 49.8 % / 49.7 % | 52.6 / 50.2 / 50.3 % |
| P3 finish-line | `alternate` | 442 | **51.6 %** [45.2, 56.8] | 48.4 % |
| P3 finish-line | siempre LONG / SHORT | 442 / 442 | 48.2 % / 52.0 % | 51.8 / 48.0 % |

Los intentos de fechas de inicio vecinas comparten días (no son independientes; el IC por bloques lo refleja solo en parte). Sin regla de dirección real, la “ventaja direccional” que traduce a P(pase) es **cero**: `alternate` es la mejor o está empatada en ambos tamaños. Cuánto valdría una ventaja *hipotética*: +5 ticks/día a favor subiría P(pase) solo ~+1.2 a +1.4 pp (Parte A, §7).

## Lectura de hoy (informativa, NO se aplica) — Yahoo `MES=F`, **menor calidad** que el parquet

Con el cierre COMPLETO más reciente (19-oct): cierre ajustado 7,735.75 · SMA20 7,791.91 · SMA50 7,736.47 · ATR14 81.39 → c − SMA20 = −56.2 (> 0.5·ATR = 40.7) → R1 = SHORT, R2 = LONG (no hay baja confirmada: SMA20 > SMA50 y precio ≈ SMA50), R3 = LONG. Con el 20-oct **provisional** (barra diaria incompleta de Yahoo, 7,786.75): c − SMA20 = −2.85 (< 0.5·ATR) → R1 = SHORT por un pelo, R2 = LONG, **R3 = NO OPERAR**. Producción mañana: **SHORT por paridad**, sin cambios. La serie de Yahoo se ajustó con el mismo método de rolls (tercer viernes de septiembre = 18-sep-2026); no se verificó contra el parquet porque este termina el 25-ago.

## Supuestos y límites

- **Muestra única** de 443 días (2 años, un solo producto): ningún IC cubre un cambio de régimen. Con 10 bloques de ~44 días la potencia para detectar una ventaja de 3–5 pp es baja; el criterio (b) exige IC95 % > 0 con corrección de Bonferroni por 3 reglas: una regla *muy* buena habría pasado, ninguna se acercó.
- **P(TP-primero)** usa slip {1,3} y salida 3 (supuestos de la Parte A); no cambia el ranking porque afecta a todas las reglas por igual.
- **Comparaciones múltiples:** 3 reglas + 4 controles + oráculo. Sin barrido de parámetros. No se agregó ninguna regla tras ver resultados; lo que se exploró después (hora de entrada, TP × nc) está en `preservacion/` y `PROPUESTAS.md`, rotulado como exploración.
- **Paper forward en sombra (§3.8)**: no aplica, ninguna regla pasó D2. El patch de logging en sombra **no se entrega** porque no hay candidata (entregarlo sería construir una estructura sin hipótesis que probar).
