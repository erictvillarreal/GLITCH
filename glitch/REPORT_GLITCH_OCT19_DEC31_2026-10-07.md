# Tus números del 19-oct al 31-dic y qué esperar
*Simulación sandbox, 07-oct-2026. Rama `research/pass-rate-levers`. No toca producción. Código en `scripts/simulate_glitch_oct19_dec31.py`, salida completa en `dd_cash/glitch_oct19_dec31_report.txt`.*

## 0. Respuesta corta
- **Combine:** casi seguro lo pasas pronto *si reinicias después de cada fallo*. Pasar al primer intento ocurre 26% de las veces; en promedio son **3.9 intentos**. A los 10 días hábiles del 19 al 30 de octubre ya lo habrías pasado el **86%** de las veces (mediana: 23-oct). Eso cuesta $49 por intento más $149 de activación. Hasta tener la XFA activa pagarías **~$250 (mediana) y hasta ~$490 (p90)**.
- **El cuello de botella es la XFA, no el Combine.** Solo **~39%** de las veces la XFA llega a pedir un primer payout (**~31%** con el ajuste por liquidación en tiempo real, ver §4). Si lo pide, el monto mediano es **~$940** al trader (el máximo posible en una XFA 50K es **$1,800**, no $5,000) y la fecha mediana es **~6-nov**.
- **Neto en caja al 31-dic:** lo más probable es **negativo (~−$330)**. El promedio sale ligeramente positivo (+$256, o +$74 con el ajuste) porque un tercio de los casos cobra. Probabilidad de terminar el año en pérdida: **~67–70%** si solo haces un ciclo, **~55–63%** si recompras Combines cuando la XFA quiebra. **Para tener el dinero listo:** el colchón (p95) es ~$770 en un ciclo y ~$1,600 con ciclos repetidos.
- **Qué NO esperar:** que el resultado de la Practice anticipe el del Combine. Son juegos distintos (§1).

## 1. Por qué la Practice no predice el Combine
| | Practice (nc=10, MLL $4,500, SL100 completo) | Combine 50K (nc=40, MLL $2,000: liquidación a −40 ticks) |
|---|---|---|
| P(TP) / P(SL o liquidación) / P(flatten) | 65.2% / 23.7% / 11.1% | 49.3% / 48.2% / 2.5% |
| P(≥2 SL en 3 días) | 14% (1 de cada 7) | **47% (1 de cada 2)** |
Tu muestra de 3 días (SL, TP, SL) es poco común en Practice (1 de 7) y **normal en el Combine**. En el Combine, cerca de la mitad de los intentos terminan el primer día. Fuente: tablas first-touch de 515 días de MES, barras de 5 min, SL primero si la barra toca ambos.

**Intentos hasta pasar (p=26% por intento):** al 1.º 26%; en ≤3 intentos 59%; ≤5 78%; ≤8 91%. Con reinicios inmediatos (hasta 2 por día en Topstep), eso cabe en las dos primeras semanas.
**Aviso de conducta:** la ToU de Topstep penaliza "excessive purchases of Combines or Resets" sin dar umbral numérico. Con 3.9 intentos de media y p90 de 8, esto no es un riesgo despreciable.

## 2. Escenarios (50K, G2 como corre hoy: nc=40, TP40, SL100; XFA con Cerebro 2/MGC, motor validado `engine_real`)
Supuestos: calendario real (52 días hábiles; 26-nov y 25-dic cerrados; 27-nov y 24-dic sin operar porque el Pi aún no maneja el flatten anticipado); activación de la XFA 2 días después de pasar; cobro de payouts 5 días después de pedirlos; costos operativos $59.5/mes (Massive + Pi + API). 40,000 trayectorias.

**Solo el primer ciclo** (si la XFA quiebra, no recompras):
| Handoff del MGC | P(≥1 payout al 31-dic) | Fecha mediana del 1.er payout* | Payouts al trader hasta 31-dic (media) | Neto al 31-dic: mediana / media / P(<0) |
|---|---|---|---|---|
| Inmediato | 39% (≈31% ajustado) | 6-nov | $746 (≈$559 aj.) | −$328 / +$256 (+$74 aj.) / 67% (70% aj.) |
| Listo el 2-nov | 40% (≈32%) | 13-nov | $744 | −$328 / +$250 (+$70 aj.) / 67% |
| Listo el 1-dic | 40% (≈32%) | 11-dic | $576 | −$328 / +$22 (−$101 aj.) / 68% |
| TP 32 en vez de 40, inmediato | 39% (≈32%) | 6-nov | $755 | −$328 / +$310 (+$125 aj.) / 66% |
*Entre quienes sí cobran.

**Ciclo repetido** (si la XFA quiebra, recompras Combine y vuelves a intentar):
| Handoff | P(≥1 payout) al 13-nov / 30-nov / 15-dic / 31-dic | Mediana del 1.er payout | Payouts hasta 31-dic: mediana / media | Neto 31-dic: p10 / p50 / p90 / media | P(<0) |
|---|---|---|---|---|---|
| Inmediato | 34% / 51% / 67% / 77% | 18-nov | $1,150 / $1,590 | −$1,508 / −$208 / +$2,734 / +$257 | 55% (63% aj.) |
| Listo el 1-dic | 0% / 0% / 34% / 50% | 14-dic | $24 / $694 | −$1,064 / −$672 / +$1,059 / −$245 | 70% (75% aj.) |
La caja acumulada **mediana** no cruza a positivo antes del 31-dic en ningún escenario.

**Monto del primer payout (al trader, ya con el 90%):** p10 $268 · mediana $941 · p90 $1,702 · máximo $1,800. El tope de la XFA 50K Standard es $2,000 por solicitud (código y fuente oficial del 24-sep); el tope de $5,000 es de la 150K.

## 3. Comparación con la extrapolación del resumen del 7-oct
| Punto del resumen | Esta simulación |
|---|---|
| Pasa el Combine "mediados de nov" (central) | Mediana **23-oct** si reinicias tras cada fallo (p90 3-nov); con 3.9 intentos de media |
| Primer payout "mediados de dic" (central) | Mediana **6-nov** entre quienes cobran (p90 18-nov), pero solo cobra ~31–39% en el primer ciclo |
| Monto $500–$2,000, tope $5,000 | Mediana ~$940; máximo $1,800 al trader ($2,000 bruto); el tope de $5,000 no aplica a la 50K |
| "1 de cada 3 sin payout al 31-dic" | **61–69% sin payout** en un solo ciclo; 23% si recompras Combines tras cada quiebre de la XFA (cifra sin ajuste; con el ajuste sería mayor, no se calculó) |
| Neto al 31-dic "cerca de cero" | Mediana −$208 a −$328; media entre −$99 y +$310 según el escenario. Coincide en el orden de magnitud |
| Cruce a positivo "día 49" | No cruza antes del 31-dic en la mediana de ningún escenario |

## 4. Límites del modelo
- **El XFA de `engine_real` no modela la liquidación en tiempo real del MLL.** El log del 24/25-sep midió el efecto en 50K (nc3): payout medio $822 → $620 (−25%) y P(≥1 pago) 39.6% → 31.6%. Por eso van las cifras "ajustadas" (−25% a payouts; P(≥1) ×0.80 solo en el primer ciclo). Es un ajuste aproximado, no una simulación nueva.
- **Supone reinicio inmediato** tras cada fallo del Combine (hasta 2 reinicios al día). Si lo espacias, los tiempos se alargan.
- **Solo vale con ejecución real:** 40 contratos, liquidación por MLL y falla de API a las 14:30 nunca se han ejecutado. El paper sobrecuenta TP en ~24% (log 24-sep) y las barras ambiguas se cuentan como SL primero.
- **Los 515 días de MES y MGC son una sola historia.** El XFA de MGC usa la serie del Cerebro 2 (nc=3 en 50K). No se corrió H1/H2 para este calendario.
- **El handoff del MGC al Pi todavía no existe.** Los escenarios con handoff tardío muestran cuánto cuesta esperarlo en fechas, no en probabilidad.
- **Impuestos/RFC no entran.** Falta confirmarlos con un contador antes de cobrar.

## 5. Qué me parece decidible
1. **Antes del 19-oct:** definir una regla para los reinicios (cuántos, con qué espaciado). La simulación asume muchos; el riesgo de conducta crece con ellos.
2. **El handoff del MGC no cambia la probabilidad de cobrar, solo cuándo.** Tenerlo listo para los primeros días de noviembre protege la fecha mediana del primer payout (6-nov vs 11-dic).
3. **Preparar el colchón de ~$800–$1,600** (p50–p95) para el primer trimestre, no contar con payouts en 2026.
4. **Cambiar TP de 40 a 32** mejora el promedio ($310 vs $256) y reduce intentos (3.1 vs 3.9), pero no cambia que ~2/3 de los casos termina 2026 sin payout. Sigue siendo propuesta que requiere tu revisión (regla 4).

## Reproducir
```bash
cd glitch   # rama research/pass-rate-levers; datos en data_cache/*.parquet (no versionados)
python scripts/simulate_glitch_oct19_dec31.py        # ~2 s, escribe dd_cash/glitch_oct19_dec31_report.txt
python -m pytest tests/test_engine_real_cal.py -q     # 5 pruebas: la copia con calendario == engine_real
```
