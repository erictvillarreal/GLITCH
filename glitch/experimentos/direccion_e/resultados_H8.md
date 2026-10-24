# resultados_H8 — barras ambiguas y reproducibilidad

## 1. ¿Sigue el defecto de `label_triple_barrier()`?

- **Hecho (código de `main` a387a70):** `simulation/triple_barrier.py` comprueba el **SL primero** en largos y cortos (comentario «BUGFIX 25-ago-2026», metodología de López de Prado: en barra ambigua se asume la pérdida). **El defecto del handoff v8 está corregido en `main`** (commit 286bc8d y merge 99497ec).
- `scripts/quantify_ambiguous_bars.py` existe; el log (`GLITCH_RESEARCH_LOG.md` ~l.165) dice que el bug fue «confirmado y corregido» y `scripts/revalidate_geometry_table.py` volvió a validar con la corrección (WR empírico de RR = 0.33: 71.7 % vs 75 % del video).
- **Los motores que producen las cifras de las Partes A–G no pasan por esa función:** `preservacion/daydata.py::sim_day` (orden `adverse`: gana la pérdida en empate), `dd_cash/engine_real*.py`/`lever_engine.py` (`tp_hit = tb < ab`: empate ⇒ adverso) y `dd_wr/product_sweep.py` (SL primero). **Todas son conservadoras en el empate.**

## 2. Cuánto pesa el empate: cota conservadora ↔ cota optimista (TP gana el empate)

| caso | días con empate que decide | TP % conservador | TP % optimista | WR_dec conservador | WR_dec optimista |
|---|---|---|---|---|---|
| MGC 3×364 `alternate` (limpio) | 0 de 488 (0.0 %) | 20.9 | 20.9 | 47.4 % | 47.4 % |
| MES nc 40 TP 32 / liquidación 40 — LARGO | 6 de 492 (1.2 %) | 52.8 | 54.1 | 52.8 % | 54.1 % |
| MES nc 40 TP 32 / liquidación 40 — CORTO | 5 de 492 (1.0 %) | 56.7 | 57.7 | 56.9 % | 58.0 % |

Lectura: en MGC con barreras de 364 ticks una barra de 5 min casi nunca toca ambas: el 47.4 % **no** depende de la regla de empate. En MES (TP 32, liquidación a 40 ticks ⇒ 72 ticks entre barreras) algunos días de apertura sí: la columna optimista es una **cota superior**, no un resultado.

## 3. Cifras clave bajo las dos reglas (Combine MES, slip 1/3 mezcla; XFA 3×364 W2, WR 50 %)

- orden **adverse**: P(pasar, P0 mezcla 1/3) = 20.5 % · cobrado medio por XFA = $644 · P(≥1 pago) = 32.8 % · neto anual por cuenta = $1,365
- orden **favorable**: P(pasar, P0 mezcla 1/3) = 21.5 % · cobrado medio por XFA = $644 · P(≥1 pago) = 32.8 % · neto anual por cuenta = $1,527

## 4. El «81.44 % teórico» que el scheduler muestra cada día — SÍ se reproduce, y es un artefacto del límite diario de pérdida (DLL)

`THEORETICAL_PASS_RATE = 0.8144` (`scheduler/geometry_scheduler.py:145`) sale de `scripts/camino_b_grid.py` + `simulation/monte_carlo.py::TopstepMonteCarloSimulator` (SL 100 / TP 40, nc 40, `wr` de la medición de brackets, n_paths 8000, seed 42). **Reproducción con el código actual:**
- WR del bracket SL 100 / TP 40 con entrada en **cualquier barra** (no solo 9:35): optimista 0.6999, conservador 0.6988 (la regla de empate no importa); `wr_mid` = 0.6993.
- Simulador legado con el DLL de $1,000 que aplica el simulador (`day_pnl < −DLL ⇒ −DLL`): **P(pasar) = 81.44 %**, quiebra 18.6 %.
- Simulador legado sin DLL (la cuenta real no lo tiene: NO VERIFICADO en TopstepX): **P(pasar) = 33.99 %**, quiebra 66.0 %.
- **Motor actual** (MLL en tiempo real, liquidación a 40 ticks, 1 operación por día a las 9:35, slip 0, 15 días, orden adverse): **P(pasar) = 24.4 %** (con TP 32: ver §3).
- **Motor actual** (MLL en tiempo real, liquidación a 40 ticks, 1 operación por día a las 9:35, slip 0, 15 días, orden favorable): **P(pasar) = 25.2 %** (con TP 32: ver §3).

**Conclusión (hecho + inferencia marcada):** (1) el 81.44 % se reproduce **solo** con el DLL de $1,000 que recorta cada día perdedor de −$5,048 a −$1,000; sin él el simulador da ≈ 34 %. (2) El simulador además evalúa el piso al **cierre del día**, así que no ve la liquidación **intradía** a 40 ticks, y usa un `wr` ≈ 70 % de entradas en cualquier barra con SL de 100 ticks (que en tiempo real nunca se alcanza: la cuenta se liquida a −$2,000 = 40 ticks, y P(TP antes que liquidación) es ≈ 50 %, no 70 %). (3) Con las reglas reales el motor da **≈ 24 %** (TP 40) y **≈ 30 %** (TP 32). **El mensaje diario «Pass rate empírico vs 81.4 % teórico» compara contra un número inalcanzable: engañoso; no usarlo como criterio de graduación.** (Inferencia: la cuenta no tiene DLL; si Topstep lo impusiera —p. ej. bajo RTP— el cálculo cambiaría.)

## 5. Reproducibilidad de `economia_historial_cifras_24oct2026.md`

**No tengo ese documento (vive en el Project; no es legible desde aquí): no pude marcar fila por fila. REQUIERE HUMANO: pegarlo o subirlo.** Lo que sí puedo decir de las cifras que yo produje (todas reproducibles con un comando de `experimentos/`, semillas fijas): 47.4 % [41.0, 54.1] y TP/SL/FLATTEN (`f2_datos_limpios.py`), P(pasar) por slip (`g1_ejecucion.py`, `h0_mapa.py`), pagos por XFA y equilibrios (`value_wr.py`, `desglose_valor.py`, `h1_equilibrio.py`), +$1.0–1.5k de palancas (`xfa/run_partD*.py`). **Las cifras de motores anteriores a la Parte A (TP 32 «+7.1 pp», 17–29 %, 81.44 %) las dejo de usar salvo que se reproduzcan.** El «+7.1 pp» del TP 32 sale de `REPORT_TP32_COSTS_2ACCOUNTS_2026-10-09.md` (rama `research/firm-map-and-labs`, motor `dd_cash`: empate ⇒ adverso, conservador); no lo recalculé aquí.