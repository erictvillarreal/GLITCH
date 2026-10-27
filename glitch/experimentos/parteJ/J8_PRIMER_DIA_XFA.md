# J8 — Estrategia del primer día XFA (mié 28-oct-2026, día de FOMC)

Lunes 26-oct-2026 · BORRADOR para decidir con Eric el martes 27-oct por la noche. Tablas completas, semillas y comando de reproducción: `resultados_J8.md` y `j8_primer_dia_xfa.py` (misma carpeta). Todo es **MODELADO** sobre 488 días reales de MGC (7:15 → 14:25 CT, contrato dominante; 443 sin la ventana de oro) con el motor de las Partes A/D; **no hay una sola sesión viva de la XFA en estos números**. Fuentes revisadas: barras de 5 min de MGC (`GLITCH_MGC_PARQUET`), `fomc_dates.txt` (federalreserve.gov, MEDIDO), código de producción en `golive/cerebro2-mgc-candidate` (`decide_side`, `xfa_mgc_config`, Pi), `RULEBOOK_XFA.md`. No revisé TopstepX, el Gist, Telegram ni el Pi.

## 1. Resumen (10 líneas)

1. **No existe, con lo que se sabe, una estrategia para el miércoles que sea distinguible en cobrado esperado de la de producción (3 micros, 364/364, `alternate`).** Para el miércoles son desplegables sin tocar código: **3×364 normal**, **1 micro** (con `GLITCH_PI_NC_MAX=1`) o **no operar el día 1**. Entre las tres, la diferencia de cobrado esperado por XFA es **−$4 [−25, +14]** (1 micro) y **+$1 [−24, +28]** (no operar) frente a $618: **NO distinguible**.
2. **Lo que sí se distingue es el riesgo de morir pronto:** P(muerte en 3 días) = **18.4 % [16.3, 20.9]** con 3×364, **9.8 % [8.2, 11.2]** con 1 micro el día 1, **7.4 % [5.9, 8.7]** sin operar ese día (WR 50 %). Con el día 1 sorteado de los 16 FOMC históricos: 23.4 % → 10.8 % → 7.4 %; diferencia pareada **−12.6 pp [−19.7, −6.8]** (1 micro) y **−16.0 pp [−24.9, −8.7]** (no operar).
3. **Mi recomendación (juicio sobre riesgo, no un resultado estadístico de EV): el miércoles 1 micro y desde el jueves 3×364.** Cuesta $0 de cobrado esperado dentro del ruido (Δ +$23 [−82, +126] condicionado a FOMC) y baja a la mitad la probabilidad de perder la XFA en 3 días. Operar normal es defendible; no es *mejor* en promedio, solo tiene más varianza.
4. **Las que sí mejoran el cobrado en el modelo no se pueden desplegar el miércoles:** 3×728 (+$180 [+125, +253] a WR 50 %; +$65 [+20, +105] a 47.4 %) y 4→1 micros (+$97 [+58, +122]; +$89 [+72, +109]) requieren cambiar código de capital (la geometría la fija `CANDIDATES['MGC']` = 364; el Pi rechaza `nc > 3`) y tocan RTP/«conducta prohibida» (ticket a Topstep sin respuesta). **Además matan más rápido:** P(muerte en 3 días) 30.7 % y 34.8 %; con 3×728, **9 % de las XFA mueren el día 1** (liquidación por MLL a 667 ticks < TP 728).
5. **«1 micro toda la vida»** da P(≥ 1 pago) 63.6 % (vs 32.2 %) pero cobra **$356 vs $618** (−$262, distinguible) y la XFA vive 26 días en vez de 10: es un plan lento, no una mejora.
6. **Siempre LARGO / siempre CORTO:** no hay respaldo fuera de muestra (Parte E: 0 de 16 pruebas, solo sesgo del índice) y los IC son enormes (cobrado $574 [321, 908] y $689 [470, 1,441]); no se recomienda.
7. **H0-0 (J8.1):** el «−$48 por sesión [−117, +26]» es la **config de producción XFA** (MGC, 3 micros, 364/364, `alternate` histórico, flatten 14:30 CT, 488 días, sin slippage, colchón 9,000, comisión $1.92). **No** es la que pasa el Combine (MES nc 40, TP 32). Mismo cálculo para cada candidata XFA en la sección 3.
8. **FOMC (J8.3):** con n = 16 días FOMC, el P&L medio de 3×364 LARGO en esos días fue −$178 vs −$28 en el resto (p = 0.48: **no distinguible**); la dispersión sube (|P&L| +$179, p = 0.11; 3×728: +$387, p = 0.02). Único indicio fuerte: **3 de 16 FOMC tuvieron su primer toque de ±364 ticks después de las 13:00 CT, contra 1.3 % en los demás días (p = 0.001)** — con 3 eventos y sin dirección.
9. **Corrección propia:** H4 decía «≈ 80 % de los días de MGC siguen abiertos a las 13:00 CT». Era un error del script (no contaba el SL de 364). **Medido: 57.8 %** (56 % en días FOMC).
10. **Sin suavizar el EV:** con WR ≈ 47.4 % el cobrado esperado por XFA es **$384 [362, 437]** y **75 % de las XFA no pagan nada nunca** (68 % a WR 50 %); restando la activación de $149 y OPS prorrateado el modelo deja ≈ +$230 por XFA (a WR 47.4 %), frente a un WR de equilibrio de la cadena completa de 47.5 % (H1b) ⇒ **EV de la cadena ≈ $0**, y todo depende de supuestos que no se pueden verificar en semanas (ver 5).

## 2. J8.1 — A qué configuración se refiere cada cifra

| cifra citada | configuración | fuente |
|---|---|---|
| «MGC `alternate`, −$48/sesión [−117, +26]» (H0-0, `resultados_H1c.md`) | **XFA / Cerebro 2**: MGC, **3 micros**, SL = TP = **364** ticks, `alternate` = la alternancia que habría tocado en cada fecha histórica (`decide_side(trading_day_index(fecha))`), entrada 7:15 CT (la de producción es 7:13), flatten **14:30 CT**, 488 días, comisión $1.92/micro, slip de entrada 0, stop llenado a 0.5, **colchón 9,000** (sin liquidación por MLL) | `h1c_728_h00.py`, MODELADO |
| «MES `alternate` +$54/sesión [−106, +190]; WR_dec 58.0 %» | **Combine / Cerebro 1**: MES nc 40, TP 32, liquidación por MLL a 40 ticks (el SL de 100 no opera), 9:35 → 14:30 CT | ídem |
| «WR_dec medido 47.4 %» (E, F, H0) | **XFA / MGC 3×364 `alternate`**, 488 días limpios, TP/(TP+SL), FLATTEN fuera | `resultados_H0.md` |
| Todas las cifras de **J8** | XFA / MGC; el slippage de entrada de MGC es la distribución de las 8 observaciones de **MES** (supuesto: MGC no tiene ninguna observación) | este archivo |

El `alternate` histórico (−$48) es peor que LARGO (−$34) y que CORTO (−$20): es la suerte de la paridad con esas fechas, no una propiedad de la regla; el promedio L/C es **−$27 [−33, −20]** por sesión (ver `resultados_J8.md` A). Con colchón inicial de $2,000 la sesión de 3×364 se liquida (toca MLL antes del SL) 0.2–0.4 % de las veces; la de 3×728, **6–10 %** (9.6 % LARGO, 6.1 % CORTO).

## 3. J8.2 — Tabla de decisión para el miércoles 28-oct (primer día XFA = LARGO)

Vidas simuladas hasta la liquidación (60,000 por celda; IC95 = 40 remuestras de bloques de 5 días; diferencias **pareadas**). Slippage de entrada: distribución empírica de 8 obs. (8.ª inferida = 0, **NO VERIFICADA**); OPS $245/año. «Cobrado» = pagos netos (90/10, tope $2,000, 5 días ≥ $150), sin descontar la activación de $149.

**WR 50 % (deriva 0 sobre la historia real)**

| política | ¿desplegable el mié 28 sin código? | cobrado por XFA [IC95] | Δ vs 3×364 [IC95] | ¿distinguible? | P(≥ 1 pago) | P(muerte ≤ 3 días) [IC95] | P(muerte día 1) |
|---|---|---|---|---|---|---|---|
| **3×364 `alternate` (producción)** | sí | $618 [592, 698] | — | — | 32.2 % | 18.4 % [16.3, 20.9] | 0.4 % |
| 1 micro SOLO el día 1, luego 3 | sí (`GLITCH_PI_NC_MAX=1`, luego 3) | $614 [588, 683] | −$4 [−25, +14] | **NO** | 33.4 % | 9.8 % [8.2, 11.2] | 0.0 % |
| No operar el día 1, luego 3 | sí (arrancar en vivo el jueves) | $619 [593, 680] | +$1 [−24, +28] | **NO** | 32.3 % | 7.4 % [5.9, 8.7] | 0.0 % |
| 1 micro la 1.ª semana (5 días), luego 3 | sí | $582 [561, 646] | −$36 [−56, −1] | SÍ (−) | 40.2 % | 0.0 % | 0.0 % |
| 1 micro toda la vida | sí | $356 [343, 384] | −$262 [−314, −237] | SÍ (−) | 63.6 % | 0.0 % | 0.0 % |
| 3×728 | **no** (código de `CANDIDATES`; RTP) | $798 [730, 869] | +$180 [+125, +253] | SÍ (+) | 28.0 % | 30.7 % [27.6, 35.1] | 9.1 % |
| 4→1 micros | **no** (Pi rechaza `nc` > 3; código; RTP) | $715 [671, 770] | +$97 [+58, +122] | SÍ (+) | 32.1 % | 34.8 % [32.7, 37.8] | 0.6 % |
| 3×364 siempre LARGO | no (sin respaldo OOS) | $574 [321, 908] | −$44 [−285, +257] | **NO** | 32.1 % | 19.7 % | 0.4 % |
| 3×364 siempre CORTO | no (sin respaldo OOS) | $689 [470, 1,441] | +$70 [−186, +829] | **NO** | 33.0 % | 15.9 % | 0.0 % |
| 3×364, flatten 12:00 CT | no (Pi: flatten fijo 14:30; parche J4-b) | $615 [574, 665] | −$3 [−78, +51] | **NO** | 33.6 % | 15.7 % | 0.4 % |
| 3×364, flatten 10:30 CT | no | $612 [574, 663] | −$6 [−80, +39] | **NO** | 35.6 % | 13.3 % | 0.4 % |

**WR 47.4 % (≈ el medido):** 3×364 **$384 [362, 437]**, P(≥ 1 pago) 25.0 %, P(muerte ≤ 3 d) 20.8 %. 3×728 +$65 [+20, +105] (SÍ); 4→1 +$89 [+72, +109] (SÍ); 1 micro toda la vida −$170 (SÍ); 1 micro la 1.ª semana −$13 [−31, +13] (NO); 1 micro día 1 −$3 [−14, +12] (NO); no operar día 1 +$1 [−13, +24] (NO); flatten 12:00 −$29 [−91, +18] (NO); flatten 10:30 **−$64 [−124, −16] (SÍ, peor)**; siempre LARGO/CORTO NO distinguibles. Si la activación consume un día y el primer día es el **jueves (CORTO)**, las cifras cambian en ≤ $25 y las conclusiones no (`resultados_J8.md`, tercera tabla).

**Lectura, sin adornos**
- **Qué es estadísticamente distinguible:** (i) 3×728 y 4→1 pagan más en el modelo, por estructura de pagos (ver `REPORTE_H1b.md` §5), no por mejor puntería; (ii) 1 micro todo el tiempo paga mucho menos; (iii) la caída del riesgo de muerte temprana al reducir o saltar el día 1.
- **Qué NO es distinguible:** todo lo demás, incluido operar 3×364, 1 micro o nada el miércoles *en cobrado esperado*; flatten 12:00 vs 14:30 (a WR 50); LARGO vs CORTO.
- **Qué no cubre el IC:** el WR verdadero (47.4 vs 50 mueve el cobrado de $384 a $618), el slippage real de MGC (no medido), el cambio de régimen, y que `xfa_engine` reproduzca fielmente las reglas de Topstep (no contrastado con ninguna XFA viva).

## 4. J8.3 — Efecto FOMC (mié 28-oct, 1:00 PM CT = 2:00 PM ET)

Muestra: **16** días FOMC dentro de la historia de MGC (6-sep-2024 → 4-sep-2026), geometría de producción, entrada 7:15, flatten 14:30, colchón inicial $2,000.

| geometría (lado = mié 28) | grupo | n | P&L medio/sesión | TP % | SL+LIQ % | FLATTEN % | \|P&L\| medio | peor sesión |
|---|---|---|---|---|---|---|---|---|
| 3×364 LARGO | FOMC | 16 | −$178 | 25 | 38 | 38 | $877 | −$1,342 |
| 3×364 LARGO | resto | 472 | −$28 | 20 | 23 | 57 | $698 | −$2,000 |
| 1 micro LARGO | FOMC | 16 | −$59 | 25 | 38 | 38 | $292 | −$447 |
| 1 micro LARGO | resto | 472 | −$10 | 20 | 23 | 57 | $233 | −$801 |
| 3×728 LARGO | FOMC | 16 | −$297 | 12 | 19 | 69 | $1,146 | −$2,000 |
| 3×728 LARGO | resto | 472 | +$4 | 5 | 9 | 86 | $759 | −$2,000 |

- **Media (FOMC − resto), 3×364 LARGO: −$151, p de permutación 0.48** → no distinguible de cero. **Dispersión (|P&L|): +$179, p = 0.11** (3×364) y **+$387, p = 0.02** (3×728).
- **Exposición al anuncio:** **57.8 %** de los días siguen sin resolver a las 13:00 CT (56 % en FOMC): la posición de las 7:13 normalmente sigue abierta cuando sale el comunicado. **3 de esos 9 días FOMC abiertos** (2024-12-18, 2025-09-17, 2025-12-10) tocaron ±364 después de la publicación, contra 6 de 472 (1.3 %) en el resto: P(≥ 3 de 16 | tasa base) = **0.001**. Direcciones: 1 abajo, 2 arriba (para un LARGO: 1 SL, 2 TP) → **el FOMC aumenta la probabilidad de resolver, no dice hacia dónde**.
- **Efecto sobre la vida de la XFA (día 1 sorteado de los FOMC; WR 50 %):** 3×364 → cobrado $577, P(muerte ≤ 3 d) 23.4 %; 1 micro el día 1 → $599, 10.8 %; no operar → $619, 7.4 %. Pareado, remuestreando también los 16 días: **1 micro +$23 [−82, +126]**; **no operar +$46 [−103, +209]**; P(muerte ≤ 3 d) **−12.6 pp [−19.7, −6.8]** y **−16.0 pp [−24.9, −8.7]**.

**Recomendación con números:** *reducir* (1 micro). Operar 3×364 normal: P(perder la XFA en 3 días) 23.4 % condicionado a que el día 1 sea FOMC (18.4 % sin condicionar); 1 micro: 10.8 %, y el cobrado esperado no cambia de forma distinguible. No operar el día 1 es equivalente en el modelo (algo más seguro: 7.4 %) pero **pierde la posibilidad de contar un día ganador** (con 1 micro un TP = +$362 ≥ $150; probabilidad de TP en FOMC 25 % en la muestra) y retrasa la cuenta un día. La diferencia entre 1 micro y no operar es de gusto por el riesgo: el modelo no las separa. Operar con tamaño completo no tiene evidencia en contra de su promedio (p = 0.48) pero sí de su varianza.

**Límite:** esto sale de n = 16 días y de 3 eventos; es una razón para reducir el riesgo un día, no una ley del mercado.

## 5. J8.4 — Qué NO se sabe y qué lo cerraría

| DESCONOCIDO | por qué importa | cómo se cierra |
|---|---|---|
| **WR verdadero** del `alternate` en MGC (47.4 medido; IC95 [41, 54]) | mueve el cobrado de $384 a $618 y el signo del EV de la cadena | distinguir 47.4 de 50 % necesita ≈ 2,300 sesiones decididas (≈ 9 años de MGC); **no se cierra en semanas**. Es una fuente de incertidumbre permanente, no un experimento |
| **Slippage real de MGC** (0 observaciones; las 8 son de MES, 7 sin CSV) | entra en todas las tablas; 1 tick MGC = $1 por micro | export de TopstepX desde el 5-oct con precios de entrada/salida y hora; parche C3 (`exec_exit`, tiempos) |
| **Contrato correcto (MGCV6 vs MGCZ6) el miércoles** | operar el vencido es un riesgo de ejecución mayor que cualquier número de arriba | `check_contracts.py` en el Pi (J2, 1.2) |
| **Si el miércoles es realmente el día 1** (la activación manual puede costar un día) | cambia lado (LARGO/CORTO) y el calendario | ver el estado de la cuenta en TopstepX |
| **Efecto FOMC** (n = 16, 3 eventos) | decide 1 micro vs normal | más reuniones FOMC (2021–2024) de MGC/GC: hace falta histórico de barras de 5 min anterior a sep-2024; el plan de Massive del repo no lo garantiza (DESCONOCIDO). Con 32 reuniones el IC seguiría siendo ancho |
| **RTP / «conducta prohibida» / cuentas en paralelo / simultáneos / OCO** | descalifica o habilita 3×728, 4→1 y escalar | las 6 preguntas del ticket a Topstep (`xfa/PREGUNTAS_TOPSTEP.md`, `REPORTE_H.md` §4.3); sin respuesta |
| **Que el motor reproduzca la XFA real** (pagos, MLL intradía, división 90/10) | todo es MODELADO | las primeras 5 sesiones vivas lo contrastan solo parcialmente (n = 5) |
| **La 8.ª observación de slippage** | la inferí como 0 | Eric: ¿cuál fue? |

## 6. Correcciones y límites

- **H4 / `REPORTE_H.md` §2.3:** «≈ 80 % de los días de MGC siguen abiertos a las 13:00 CT» → **57.8 %** (el script de H4 contaba solo el TP; los 16 FOMC: 56 %). La conclusión de H4 («el FOMC es un riesgo de la XFA, no del Combine de MES») se mantiene: en MES solo ≈ 1 % de los días sigue abierto.
- El «WR 47.4 %» de las tablas es una **etiqueta de deriva** calibrada en el bracket 364/364 (misma convención que H1); con 3×728 el WR por sesión no es comparable (ver `REPORTE_H1b.md` §5).
- Todos los IC95 de J8 son de **la muestra de días históricos**; no incluyen cambio de régimen ni errores del modelo.
