# resultados_H4 — noticias como filtro y como riesgo

## 1. Catálogo con fuente primaria y fecha de verificación (24-oct-2026)

| evento | fecha(s) en la ventana 26-oct → 31-dic | hora | fuente / estado |
|---|---|---|---|
| **FOMC** | **27–28 oct**, 8–9 dic (con proyecciones); 28-oct es el día del anuncio | **2:00 PM EDT = 1:00 PM CDT** (el 28-oct aún es horario de verano; desde el 1-nov, 2:00 PM EST = 1:00 PM CST) | `federalreserve.gov/monetarypolicy/fomccalendars.htm` (fechas) y comunicado del 16-sep-2026 «For release at 2:00 p.m. EDT» (hora) — **VERIFICADO**; la hora no está en la página del calendario, sí en el comunicado |
| PIB adelantado T3 y Personal Income and Outlays (PCE) | jue 29-oct | 8:30 ET (7:30 CT) | `bea.gov/news/schedule` (snapshot del 24-oct) — VERIFICADO |
| Employment Cost Index | vie 30-oct | 8:30 ET (7:30 CT) | `bls.gov/schedule/2026/10_sched.htm` (página con «última modificación 18-feb-2026»: posible snapshot viejo) — VERIFICADO con reserva |
| Empleo (NFP, datos de octubre) | vie 6-nov | 8:30 ET | `bls.gov/schedule/news_release/empsit.htm` — VERIFICADO |
| CPI (datos de octubre) | mar 10-nov | 8:30 ET | `bls.gov/schedule/news_release/cpi.htm` — VERIFICADO |
| Reclamos semanales de desempleo | jueves 8:30 ET; si el jueves es feriado, el miércoles (**miércoles 25-nov**) | 8:30 ET | `oui.doleta.gov/unemploy/claims_arch.asp` — VERIFICADO |
| Inventarios de petróleo (EIA, relevante solo si hubiera MCL) | miércoles 10:30 ET; semana del 6-nov se retrasa al jueves 12-nov 12:00 ET | | `eia.gov/petroleum/supply/weekly/schedule.php` — VERIFICADO |
| PPI, ISM, ventas minoristas, PIB T4 | — | — | **NO VERIFICADO** (no se consultó la fuente primaria de cada uno) |
| Cierres anticipados | Topstep: 26-nov 11:45 CT, 27-nov 12:00 CT, 24-dic 12:00 CT; 25-dic y 1-ene cerrado | | `RULEBOOK_XFA.md` 1.9 (Help Center de Topstep, leído el 20-oct) — **VERIFICADO**; las fuentes de terceros sobre CME **discrepan** (26-nov cerrado vs 12:00 CT; 27-nov ≈ 12:15 CT): **DESCONOCIDO para CME** |

**Hora del dato frente a nuestras horas (CT):** MES entra a las 9:35 y aplana a las 14:30; MGC entra a las 7:13–7:15 y aplana a las 14:30. Los datos de las 7:30 CT (PIB/PCE/ECI/NFP/CPI) caen **15 minutos después de la entrada de MGC** y **antes** de la entrada de MES. El **FOMC (13:00 CT) cae dentro de la ventana de los dos**.

**Reglas de Topstep sobre noticias (verificadas el 20-oct, `RULEBOOK_XFA.md` 1.8):** Tier 1 = CPI, NFP, PPI 7:25–7:35 CT; FOMC 12:55–1:05 y 1:25–1:35 CT: no se pueden **abrir** posiciones nuevas en minis; en micros hay tope de aperturas; XFA 50K: 1 micro con saldo < $2,000 y 3 con más (MGC incluido); las posiciones ya abiertas se mantienen; los TP/SL que reducen posición se aceptan. **Para el Combine: DESCONOCIDO** (el artículo leído trata la XFA). Pregunta lista para el ticket: *«¿Aplican las restricciones de noticias Tier 1 al Combine 50K con MES, y cuál es el tope de aperturas de micros en esas ventanas?»*

## 2. FOMC en la ventana real (2 años, 5 min; lados LARGO y CORTO juntos)

| producto / geometría | días FOMC / total | rango de la ventana FOMC ÷ resto | fracción decidida FOMC vs resto | P(TP | decidido) en días FOMC [IC exacto] | % de días SIN resolver a las 13:00 CT (resto) | (FOMC) |
|---|---|---|---|---|---|---|
| MES nc 40, TP 32 / liquidación 40 | 16 / 492 | ×1.30 | 100 % vs 100 % | 19/32 = 59 % [41, 76] | 1 % | 0 % |
| MGC 3×364 | 16 / 488 | ×1.28 | 62 % vs 43 % | 10/20 = 50 % [27, 73] | ~~80 %~~ **58 %** (corregido en J8: el script ignoraba el SL de 364 ticks) | ~~81 %~~ **56 %** |

**Lectura.** (1) Con n = 16 días FOMC el IC de cualquier proporción es de ±25 pp: **sin potencia** para decir que el FOMC cambia P(TP). (2) El rango sí sube (consistente con ×1.43 en el S&P diario 2021–26, T5 de G2). (3) **Exposición:** en MES **solo ≈ 1 % de los días (0 % en los 16 FOMC) sigue sin resolver a las 13:00 CT**: casi todo se resuelve por TP o liquidación antes del anuncio, así que el FOMC **casi no toca al Combine de MES**; en MGC **≈ 80 % de los días siguen abiertos a esa hora** (son los FLATTEN), por eso el FOMC sí es un riesgo de la XFA (tres micros abiertos con MLL de $2,000 al momento del anuncio). El anuncio afecta sobre todo a las posiciones **abiertas a las 13:00**.

## 3. Costo de ejecución ese día (proxy; no hay tick ni libro)

- **MES, barras de 5 min de 13:00 a 13:15 CT** (el anuncio es a las 13:00): rango mediano **55 ticks en días FOMC** (n = 48 barras) vs **20** en el resto; volumen mediano 7,886 vs 6,682. Un stop o un cierre de mercado que se dispare en esa franja sufre un deslizamiento del orden de ese rango (**proxy, no medido**).

## 4. Operar / saltar / reducir tamaño: techo de valor y respuesta para el FOMC del miércoles 28-oct (LONG por paridad)

| opción | efecto esperado | techo arithmético en $/año/cuenta | veredicto |
|---|---|---|---|
| operar normal (40 contratos) | igual que cualquier día: P(TP antes de liquidación) ≈ 55.6 % con martingala (52.8 % LARGO en la muestra, IC [48.5, 56.3]) | — | **opción base** |
| saltar | pierde el valor esperado del día; no reduce el riesgo de liquidación de los demás días | ≈ 8 FOMC/año ÷ 252 días ≈ 3 % de los días ⇒ como máximo ≈ 3 % del neto anual (≈ $40–$110 con $1.4–3.9k/año), **a favor o en contra** | **no vale la pena** (< $500) |
| reducir a 20 contratos | mantiene P(liquidación) por trade y reduce a la mitad lo que paga el TP: en el Combine **alarga** el camino (dos TP dejan de bastar) | ≤ 3 % de los días | **peor que operar o saltar** salvo que el Combine esté a un TP de pasar con otro tamaño |

**Respuesta con número y su incertidumbre para el miércoles 28-oct:** operar de forma normal. Para MES el 28-oct se parece a cualquier día: P(TP) ≈ 53 % [49, 56] como LARGO en la muestra de 492 días (martingala 55.6 %); la fracción de días que sigue sin resolver a las 13:00 CT es ≈ 1 % (0 de 16 en FOMC), y la liquidación por MLL es una orden de mercado cuyo deslizamiento **no cuesta efectivo extra** (la cuenta se cierra de todos modos). **Nada de esto es evidencia de que el FOMC sea favorable o desfavorable** (n = 16, sin potencia). Si el Combine ya está en el último TP (finish-line) y se quiere minimizar varianza, saltar ese único día cuesta ≈ un día de calendario ($2.33 de mensualidad) y una oportunidad; es una **decisión de aversión al riesgo, no de valor esperado**. No se verificó si el Combine tiene restricción de noticias (ventana 12:55–1:05 CT): si la tuviera, afectaría solo a **abrir** posiciones, y MES abre a las 9:35.