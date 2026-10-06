# Glitch en Tradeify y Bulenox: ¿es viable? Cash flow comparado con Topstep
*R&D / sandbox, 05-oct-2026. Rama `research/pass-rate-levers`. Nada de esto toca producción, Railway ni el Pi. Detalle de reglas con citas en `GLITCH_RESEARCH_LOG.md` (secciones del 05-oct).*

## 0. Veredicto
1. **Con la misma estrategia y las mismas políticas, ninguna de las dos plataformas supera a Topstep en cash flow esperado.** Topstep queda arriba en las 4 comparaciones de políticas (2 evaluaciones × 2 políticas fondeadas), contra cada una de las otras cuentas modeladas.
2. **Las candidatas más cercanas son Bulenox Momentum y Tradeify Growth.** Con la evaluación propuesta (TP al target restante) y la política fondeada de máximo riesgo, Momentum rinde $648/mes frente a $885 de Topstep, y Growth $479. En la segunda mitad de la historia (H2) bajan a $318 y $248 contra $609.
3. **Pasar la evaluación más fácil no basta.** Bulenox pasa 41–44% de las veces y Tradeify 31–37%, contra 33% de Topstep. Pero su etapa fondeada exige más (consistencia 35% y balance mínimo, o 10 días y reserva), y eso se come la ventaja.
4. **Con la política fondeada "defendible" (riesgo diario ≤ 50% de la distancia al piso), todas rinden casi cero en H2, incluida Topstep.** Casi todo el dinero modelado viene de apostar al límite cada día. Eso también es lo que más se parece a lo que cada firma castiga.
5. **Costos que cambian el resultado:** Bulenox cobra $100/mes por API de terceros (Momentum conservadora: $134/mes con API a $100 vs $234 sin ella) y ninguna de las dos tiene adaptador de ejecución hoy. Para Tradeify, la disponibilidad de API en evaluación sigue sin verificarse.
6. **Recomendación:** no migrar. Topstep sigue siendo la mejor plataforma para esta estrategia. Si quieres una segunda plataforma, la candidata es **Bulenox Momentum**, y solo después de resolver con su soporte los puntos de la sección 7.

## 1. Qué se midió
- **Motor:** `dd_cash/engine_firms.py` (numba, offline), con pruebas en `tests/test_engine_firms.py` (9 pasan). Simula 30,000 trayectorias de 252 días, tomando días al azar de los 515 días de MES (barras de 5 min, tablas first-touch). El ciclo es evaluación → fondeada → quiebre → nueva compra. Incluye fees, resets, ventana de acceso de Bulenox, reglas de pago y quiebre por piso o DLL en tiempo real.
- **Evaluación:** (i) **G2 tal cual** (nc=40, TP40, SL100), que es lo que corre hoy en Topstep; (ii) **TP al target restante** con stop propio, la propuesta de investigación del 05-oct.
- **Fondeada** (misma familia en todas las firmas): un bracket diario con TP bruto G_f, tamaño derivado y stop = rho × distancia al piso.
  - **A (óptima sin restricciones):** la mejor del grid de 75 combinaciones, siempre G_f=$600 y rho=1 (stop en el piso).
  - **B (conservadora):** rho ≤ 0.5 y G_f ≤ $400.
- **Costos operativos:** Massive $43.5 + Pi $1.5 + API (Topstep $14.5; Bulenox $100; Tradeify $0, sin verificar).
- **No son comparables en valor absoluto** con el flujo validado del 24-sep (Topstep, G2 + XFA MGC: $523/mes). Aquí la fondeada es un bracket de MES, no la MGC de Cerebro 2. Úsalo para comparar plataformas entre sí, no como pronóstico en dólares.

## 2. Resultados
Neto = payouts al trader − fees de compra/reset/activación − costos operativos. "Neto/mes medio" promedia los meses 3 a 12. Entre paréntesis, H1 / H2: la historia dividida en dos mitades.

### 2.1 Evaluación con G2 tal cual (lo que hoy corre en Topstep), fondeada A (riesgo máximo)
| Plataforma / cuenta (50K) | Neto/mes medio (H1 / H2) | Neto/mes mediano | Acum. 12m p10 / p50 / p90 | P(neto 12m<0) | Colchón p95 | Mes equilibrio (mediana) | Compras/año · fondeadas · pagos | Comisiones +50% |
|---|---|---|---|---|---|---|---|---|
| Topstep (control) | **$690** ($1,023 / $425) | $551 | $-1,125 / $6,617 / $17,516 | 14% | $4,630 | 3 | 23.5 · 23.0 · 10.9 | $680 |
| Tradeify Growth | **$216** ($432 / $47) | $-475 | $-4,195 / $1,285 / $9,465 | 40% | $5,735 | 7 | 13.7 · 13.1 · 5.0 | $121 |
| Tradeify Select Flex | **$-21** ($322 / $-307) | $-917 | $-9,012 / $-1,898 / $8,615 | 61% | $10,839 | no llega | 18.8 · 16.5 · 7.1 | $-41 |
| Tradeify Select Daily | **$-46** ($156 / $-206) | $-45 | $-4,526 / $-1,627 / $2,245 | 72% | $5,398 | no llega | 4.5 · 3.9 · 6.7 | $-68 |
| Bulenox Qualification Opc.2 + Master | **$8** ($354 / $-219) | $-546 | $-6,762 / $-3,455 / $10,833 | 74% | $7,082 | no llega | 12.1 · 7.5 · 2.8 | $-28 |
| Bulenox Momentum | **$334** ($645 / $93) | $-574 | $-4,533 / $2,540 / $12,255 | 34% | $6,748 | 4 | 12.6 · 12.1 · 6.2 | $250 |

### 2.2 Evaluación con G2 tal cual, fondeada B (conservadora)
| Plataforma / cuenta (50K) | Neto/mes medio (H1 / H2) | Neto/mes mediano | Acum. 12m p10 / p50 / p90 | P(neto 12m<0) | Colchón p95 | Mes equilibrio (mediana) | Compras/año · fondeadas · pagos | Comisiones +50% |
|---|---|---|---|---|---|---|---|---|
| Topstep (control) | **$93** ($272 / $-44) | $-206 | $-2,710 / $416 / $5,105 | 44% | $3,609 | 8 | 12.3 · 12.0 · 10.1 | $62 |
| Tradeify Growth | **$32** ($152 / $-63) | $-190 | $-3,650 / $-545 / $4,390 | 57% | $4,215 | no llega | 7.0 · 6.7 · 2.1 | $-37 |
| Tradeify Select Flex | **$-84** ($-74 / $-95) | $-45 | $-2,723 / $-1,415 / $-814 | 100% | $3,215 | no llega | 1.8 · 1.5 · 0.0 | $-90 |
| Tradeify Select Daily | **$-55** ($11 / $-113) | $-45 | $-3,475 / $-1,580 / $1,292 | 79% | $4,143 | no llega | 2.9 · 2.5 · 3.5 | $-83 |
| Bulenox Qualification Opc.2 + Master | **$-85** ($196 / $-253) | $-320 | $-5,066 / $-2,650 / $3,654 | 75% | $5,389 | no llega | 6.8 · 4.3 · 2.0 | $-139 |
| Bulenox Momentum | **$13** ($244 / $-154) | $-288 | $-5,388 / $-887 / $5,542 | 58% | $6,316 | no llega | 7.9 · 7.6 · 2.9 | $-44 |

### 2.3 Evaluación con TP al target restante, fondeada A (riesgo máximo)
| Plataforma / cuenta (50K) | Neto/mes medio (H1 / H2) | Neto/mes mediano | Acum. 12m p10 / p50 / p90 | P(neto 12m<0) | Colchón p95 | Mes equilibrio (mediana) | Compras/año · fondeadas · pagos | Comisiones +50% |
|---|---|---|---|---|---|---|---|---|
| Topstep (control) | **$885** ($1,225 / $609) | $600 | $767 / $9,013 / $20,078 | 8% | $3,761 | 1 | 26.6 · 26.1 · 12.4 | $861 |
| Tradeify Growth | **$479** ($755 / $248) | $-380 | $-2,085 / $4,485 / $13,280 | 20% | $4,585 | 2 | 18.6 · 18.2 · 7.0 | $393 |
| Tradeify Select Flex | **$423** ($714 / $187) | $-484 | $-3,546 / $3,459 / $13,684 | 28% | $5,948 | 4 | 19.4 · 18.6 · 8.0 | $358 |
| Tradeify Select Daily | **$230** ($531 / $-12) | $-375 | $-3,965 / $1,659 / $9,108 | 37% | $5,659 | 6 | 14.4 · 13.8 · 16.3 | $87 |
| Bulenox Qualification Opc.2 + Master | **$291** ($730 / $-15) | $-546 | $-6,182 / $-1,038 / $15,027 | 56% | $7,226 | no llega | 13.6 · 12.5 · 4.6 | $251 |
| Bulenox Momentum | **$648** ($1,051 / $318) | $-288 | $-1,389 / $6,468 / $16,326 | 16% | $4,746 | 2 | 15.9 · 15.6 · 7.9 | $553 |
| Bulenox Fast Track | **$373** ($637 / $71) | $391 | $-2,169 / $4,321 / $9,681 | 19% | $6,380 | 2 | 20.3 · 20.3 · 9.6 | $297 |

### 2.4 Evaluación con TP al target restante, fondeada B (conservadora)
| Plataforma / cuenta (50K) | Neto/mes medio (H1 / H2) | Neto/mes mediano | Acum. 12m p10 / p50 / p90 | P(neto 12m<0) | Colchón p95 | Mes equilibrio (mediana) | Compras/año · fondeadas · pagos | Comisiones +50% |
|---|---|---|---|---|---|---|---|---|
| Topstep (control) | **$150** ($332 / $9) | $-144 | $-2,051 / $1,107 / $5,829 | 35% | $3,053 | 5 | 13.0 · 12.8 · 10.8 | $115 |
| Tradeify Growth | **$129** ($301 / $-1) | $-235 | $-3,275 / $615 / $6,350 | 44% | $4,175 | 8 | 10.3 · 10.1 · 3.0 | $73 |
| Tradeify Select Flex | **$7** ($134 / $-98) | $-210 | $-3,400 / $-603 / $3,541 | 58% | $4,253 | no llega | 11.2 · 10.7 · 7.6 | $-48 |
| Tradeify Select Daily | **$48** ($204 / $-77) | $-210 | $-3,492 / $-387 / $4,606 | 55% | $4,202 | no llega | 7.3 · 7.0 · 9.5 | $-19 |
| Bulenox Qualification Opc.2 + Master | **$12** ($338 / $-192) | $-398 | $-5,115 / $-1,598 / $5,783 | 65% | $5,602 | no llega | 7.5 · 6.9 · 3.0 | $-53 |
| Bulenox Momentum | **$136** ($413 / $-65) | $-288 | $-4,101 / $613 / $7,185 | 44% | $5,172 | 8 | 9.0 · 8.8 · 3.4 | $82 |
| Bulenox Fast Track | **$-30** ($200 / $-228) | $-633 | $-5,351 / $-1,073 / $3,772 | 60% | $6,673 | no llega | 10.1 · 10.1 · 3.3 | $-84 |

*Fast Track no tiene evaluación (se compra fondeada), por eso aparece solo con "TP al target" y su pass de primera evaluación es 0.*

## 3. Lectura
- **Orden:** Topstep > Bulenox Momentum ≈ Tradeify Growth > Tradeify Select Flex > Bulenox Fast Track > Bulenox Qualification+Master ≈ Tradeify Select Daily.
- **Bulenox Momentum** ($143, Master gratis, 40 micros fijos) es la única que se acerca a Topstep. Esto tiene un costo:
  - su drawdown es de $2,250 y el DLL de $1,200 es permanente;
  - el pago exige 5 días ≥$150, consistencia 35%, balance mínimo $53,000 y solicitud mínima $1,000;
  - sus topes son $1,500, $2,000, $2,500 y luego $3,000.
- **Tradeify Select** tiene la mejor fondeada de Tradeify (sin consistencia). Aun así es peor que Growth, porque su evaluación pasa solo 31% (consistencia 40%, mínimo 3 días) y cuesta más de recomprar.
- **Bulenox Qualification + Master** es la peor opción de Bulenox pese a pasar 44%: paga $175 más $148 de activación, el escalado de contratos y la ventana de 21 días de trading cuestan, y el Master exige 10 días con reserva de $2,600.
- **Fast Track** ($488) exige consistencia de 20%, 25% y 30% en los primeros pagos. Compra una cuenta fondeada nueva cada vez que quiebra. Con política conservadora pierde dinero.
- **La distribución importa más que la media.**
  - En casi todas las cuentas nuevas la mediana mensual es negativa y la media positiva. El dinero llega en pocos pagos grandes.
  - La probabilidad de terminar el año en pérdida va de 8% (Topstep, política A) a 74% (otras con política A en G2 tal cual).
  - El colchón (p95 de capital hundido en 12 meses) va de $3.0k (Topstep, B) hasta $10.8k (Tradeify Select Flex con G2 tal cual y política A).
- **Qué mueve el resultado:** pass rate de la evaluación × valor de la etapa fondeada − número de cuentas que se compran. Las plataformas con mejor pass rate pierden en la segunda y tercera.
- **El cambio de TP en Topstep (40 a 32 ticks) mejora a Topstep más que cualquier cambio de plataforma:** en esta tabla, de $690 a $885/mes con política A, y de $93 a $150/mes con política B. Eso es independiente de la decisión de plataforma (ver log).

## 4. Robustez (todo en `dd_cash/firms_cashflow_report.txt`)
- **H1 vs H2:** H2 es sistemáticamente peor que H1 (el grid se eligió sobre toda la muestra, así que hay sesgo de selección). Usa **H2 como estimación prudente**. En política B, H2 es ≈ 0 o negativo en todas las plataformas, Topstep incluida (Topstep $9/mes; Momentum −$65; Growth −$1).
- **Comisiones +50%:** el orden no cambia. Topstep política A baja de $885 a $861; Momentum de $648 a $553.
- **Payouts −20%** (demora o rechazos): el orden no cambia. Momentum A queda en $413/mes y Topstep A en $588/mes.
- **Costo de API de Bulenox** (Momentum, política B): $134/mes con API a $100; $220 con $14.5; $234 sin costo. Tradeify no tiene costo de API verificado (sigue sin confirmarse si la evaluación admite API).
- **Control Topstep con supuestos XFA no verificados** (escalado de contratos 20/30/40 y pago mínimo): no cambia el orden. Con 20 micros fijos: $845/mes (política A); con pago mínimo de $500: $225 (B).

## 5. Riesgos de conducta y operativos
- **La política A es la más rentable y la más riesgosa para la cuenta:** arriesga hasta el piso cada día y compra entre 5 y 27 cuentas al año según la plataforma (quiebra casi todas las fondeadas), con las compras que eso implica.
  - Topstep sanciona "excessive purchases of Combines or Resets".
  - Tradeify limita a 15 evaluaciones por 30 días (no se modeló el tope en ráfagas) y "hedging" no está permitido.
  - Bulenox "se reserva el derecho a negar profit si sospecha abuso" y revisa la actividad tras pasar.
  - Ninguna da un umbral numérico.
- **Ejecución:** nuestro executor habla con ProjectX/TopstepX. Bulenox opera por Rithmic y Tradeify por Tradovate o Rithmic. Cualquiera exige un adaptador nuevo y validación en demo antes de usar dinero.
- **Operativos:**
  - los pagos de Bulenox son por revisión (semanales en Master, el mismo día en Fast Track y Momentum);
  - Tradeify puede mover una cuenta a Live tras un payout;
  - todas las ventas son finales.

## 6. Limitaciones (qué NO está verificado)
- Una sola historia de 515 días, barras de 5 min, in-sample.
- La política fondeada se eligió en el grid sobre la misma historia; H2 es la lectura prudente.
- Supuestos de reglas sin verificar:
  - Momentum: reset (se asumió recompra a $143), DD y DLL de su Master (DLL permanente asumido, lock +$100).
  - Bulenox Qualification: lock +$100 en calificación.
  - Tradeify Growth: la consistencia del 35% en el Master se midió sobre el ciclo.
  - Topstep XFA: escalado de contratos (no cambia el resultado) y pago mínimo.
- Se supuso que se opera todos los días y no se modela la demora de procesamiento de pagos ni la revisión humana.
- No se modela correlación entre cuentas ni el límite de Topstep de una sola cuenta personal.
- El código promocional de Bulenox ("BULENOX") no se aplicó: se desconoce el descuento.
- No hay API verificada para Tradeify en evaluación.

## 7. Qué decidir y qué preguntar antes de construir nada
1. **¿Seguimos solo en Topstep?** Recomendado: sí. Aplicar el TP de 32 ticks sobre G2 sigue siendo una propuesta que requiere tu revisión (regla 4 de CLAUDE.md).
2. **Si quieres una segunda plataforma, la candidata es Bulenox Momentum.** Preguntas para su soporte:
   - ¿Aprueban una estrategia propia de un trade al día con brackets? (ToU: "third party algorithms must be approved").
   - ¿Momentum tiene resets y a qué precio?
   - ¿Cuáles son el DD, el DLL y el lock de su Master?
   - ¿La API de Rithmic cuesta $100/mes y requiere aprobación?
3. **Tradeify:** ¿la API de Tradovate está disponible en evaluación y Sim Funded? Si no, solo queda Rithmic.
4. **Próximo trabajo si se avanza:** adaptador de ejecución en demo (sin dinero) y motor de caja con el XFA de Cerebro 2 (MGC), para comparar con el flujo validado de Topstep.

## Reproducir
```bash
cd glitch   # rama research/pass-rate-levers, datos en data_cache/*.parquet (no versionados)
python scripts/run_firm_cashflow_report.py     # ~1 min, escribe dd_cash/firms_cashflow_report.txt y dd_cash/firms_cashflow_summary.csv
python -m pytest tests/test_engine_firms.py -q  # 9 pruebas de invariantes
```
Archivos: `dd_cash/engine_firms.py`, `scripts/run_firm_cashflow_report.py`, `tests/test_engine_firms.py`, `dd_cash/firms_cashflow_report.txt`, `dd_cash/firms_cashflow_summary.csv`, `scripts/pass_rate_firms_verified.py`, `scripts/pass_rate_ceiling_dp.py`.
