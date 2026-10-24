# resultados_H2 — ejecución ampliada: demoras, hora del día, salidas y plan de medición

## 1. Ruido de precio durante una demora (media cero ⇒ no es costo esperado; sí es dispersión del fill respecto de la referencia)

σ de un cambio de precio en τ segundos ≈ σ(5 min) × √(τ/300), con σ(5 min) = desvío de los cambios de cierre a cierre de barras de 5 min **en la franja de entrada** (supuesto de caminata aleatoria dentro de la barra; **no hay ticks**). En ticks y en dólares de la posición (MES: 40 contratos, $50/tick; MGC: 3 micros, $3/tick).

| producto | franja | σ(5 min) ticks | τ = 1 s | 3 s | 10 s | 30 s | 60 s | 120 s (sondeo del Pi) |
|---|---|---|---|---|---|---|---|---|
| MES | 9:35–10:05 CT | 23.9 | 1.4 t ($69) | 2.4 t ($120) | 4.4 t ($218) | 7.6 t ($378) | 10.7 t ($535) | 15.1 t ($756) |
| MGC | 7:15–7:45 CT | 54.3 | 3.1 t ($9) | 5.4 t ($16) | 9.9 t ($30) | 17.2 t ($52) | 24.3 t ($73) | 34.3 t ($103) |

Lectura (corregida tras ver la tabla): con σ(5 min) ≈ 24 ticks en la franja de entrada, **una demora de 1–3 s ya implica una dispersión de ±1.4–2.4 ticks (1σ) y 10 s ±4.4**; el sondeo de 120 s (±15 ticks) **no se paga en el slippage** porque la referencia se toma cuando el Pi actúa (solo desplaza la hora). Los +1 y +3 ticks observados son del orden de 1σ de una demora de 1–3 s: **son compatibles con ruido puro, sin costo sistemático**; la probabilidad de que dos fills salgan los dos adversos con media cero es 25 %. Con N = 2 no se separa ruido de costo (**sin potencia**), pero el orden de magnitud dice que **la dispersión por demora (≈ ±2 ticks) es mayor que el costo sistemático esperado (≈ 0.5 tick de medio spread: SUPUESTO)**: el slippage que mueve P(pasar) es, sobre todo, aleatorio.

## 2. Hora del día (proxy; no hay libro de órdenes)

Rango mediano de una barra de 5 min, volumen mediano por barra, proxy de costo de Corwin-Schultz (**estimado con H/L de barras de 5 min; sobreestima y es ruidoso: sirve para el perfil relativo en U, no para el nivel**) y qué parte de la barra serían nuestros contratos.

**MES** (40 contratos)

| franja CT | rango 5 min (ticks) | volumen por barra | proxy de costo CS (ticks) | nuestros contratos / volumen de la barra |
|---|---|---|---|---|
| 8:30–9:30 | 34.0 | 17,706 | 5.80 | 0.23 % |
| 9:30–10:30 | 26.0 | 11,667 | 4.83 | 0.34 % |
| 10:30–11:30 | 22.0 | 8,291 | 3.97 | 0.48 % |
| 11:30–12:30 | 20.0 | 6,726 | 3.59 | 0.59 % |
| 12:30–13:30 | 19.0 | 6,315 | 3.90 | 0.63 % |
| 13:30–14:30 | 18.0 | 6,019 | 3.86 | 0.66 % |
| 14:30–15:30 | 24.0 | 9,495 | 4.88 | 0.42 % |

**MGC** (3 contratos)

| franja CT | rango 5 min (ticks) | volumen por barra | proxy de costo CS (ticks) | nuestros contratos / volumen de la barra |
|---|---|---|---|---|
| 7:00–8:00 | 44.0 | 1,037 | 5.39 | 0.29 % |
| 8:00–9:00 | 53.0 | 1,506 | 7.79 | 0.20 % |
| 9:00–10:00 | 51.0 | 1,495 | 7.29 | 0.20 % |
| 10:00–11:00 | 39.0 | 936 | 6.55 | 0.32 % |
| 11:00–12:00 | 31.0 | 640 | 4.16 | 0.47 % |
| 12:00–13:00 | 27.0 | 520 | 3.95 | 0.58 % |
| 13:00–14:00 | 24.0 | 398 | 3.04 | 0.75 % |
| 14:00–15:00 | 24.0 | 406 | 2.84 | 0.74 % |

Lectura: el patrón en U se ve en volumen y rango (alto en la apertura, bajo al mediodía). El proxy de costo es mayor cuando el volumen es bajo. **Elegir otra hora de entrada no es una palanca de costo medible con estos datos** (la Parte A y P5/P6 de H3 tampoco encuentran efecto en P(pasar)).

## 3. Salidas y liquidación (lo que se sabe y lo que no)

- **SL (orden stop):** se convierte en orden de mercado al tocarse; el slippage de salida **no está medido** (SUPUESTO 3 ticks en las Partes A–G). En MES con nc 40 el SL de 100 ticks **nunca se alcanza**: la liquidación por MLL ocurre a 40 ticks (hecho de la simulación: SL 0.0 %, LIQ 43–49 % de los días, `resultados_H0.md`).
- **TP (orden límite):** se llena si el precio lo toca; fills parciales o espera en cola: **DESCONOCIDO** (no hay un solo TP con detalle de fill en este repo). Modelo: llena al precio de la orden.
- **FLATTEN 14:30 CT (`closeContract`, mercado):** MES casi no lo usa (0.2 % de los días); en MGC 56 %. Slippage de salida **no medido**; su media es ≈ costo de medio spread.
- **Liquidación por MLL en tiempo real:** Topstep liquida con órdenes de mercado y «el slippage de salida no lo deshace» (`RULEBOOK_XFA.md` 1.3, hecho leído el 20-oct). El sobreimpulso (cuánto más allá del piso se cierra) **no cuesta efectivo**: la cuenta se cierra de todos modos (en el motor la pérdida es exactamente el colchón); solo importaría para una XFA con saldo sobre el piso. **Caso real del 19-oct: no tengo el precio de salida; DESCONOCIDO** — hace falta el historial de operaciones de TopstepX (precio y hora de la salida) para medir el sobreimpulso.
- **Parche:** `c3_slippage_timing.patch` (actualizado en la Parte H) registra también `exec_exit` (precio de salida frente al disparador, en ticks adversos).

## 5. ¿Cuánto vale anclar al fill si el slippage es sobre todo ruido? (M1: el precio se movió; media cero; σ de la tabla 1)

| σ del slippage aleatorio (ticks) | política | E[P(pasar)] hoy (anclado a la referencia) | E[P(pasar)] anclado al fill (= slip 0) | E[neto $/año] hoy | E[neto $/año] anclado | **valor del anclaje $/año/cuenta** |
|---|---|---|---|---|---|---|
| 1.4 | P0 | 28.5 % | 29.9 % | $2,663 | $2,900 | **+237** |
| 1.4 | P3 | 29.9 % | 29.9 % | $2,846 | $2,902 | **+55** |
| 2.4 | P0 | 27.0 % | 29.9 % | $2,427 | $2,900 | **+472** |
| 2.4 | P3 | 29.4 % | 29.9 % | $2,749 | $2,902 | **+153** |
| 4.4 | P0 | 25.9 % | 29.9 % | $2,243 | $2,900 | **+657** |
| 4.4 | P3 | 28.7 % | 29.9 % | $2,598 | $2,902 | **+304** |

(σ = 1.4 ≈ demora de 1 s; 2.4 ≈ 3 s; 4.4 ≈ 10 s.) **Estado: MODELADO con σ derivada de volatilidad de 5 min, no de fills; SUPUESTO de media cero.** Si el slippage es sobre todo ruido de media cero, anclar al fill (envío del TP/SL tras conocer el fill, o brackets nativos con ticks desde el fill) vale **$55–$657/año/cuenta según σ y política**: cruza el piso de $500 solo con σ ≥ 2.4 ticks y sin finish-line; con finish-line vale $55–$304. **Corrige a la baja** el +$1.5k de G1c, que suponía slippage adverso FIJO de 2–3 ticks (sistemático); el valor real depende de cuánto del slippage sea sistemático (C3 lo mide). Hace falta C3 para confirmar la σ real.

## 6. Plan de medición (qué registrar y cuántos fills)

| objetivo | qué registrar | σ supuesta (ticks) | fills para IC95 de ±0.5 tick en la media | estado |
|---|---|---|---|---|
| media del slippage de entrada | `ref_price`, `fill_price`, `slip_ticks`, `t_ref_bar`, `t_send`, `t_fill`, `nc` | 1 | 16 | σ es SUPUESTO (N = 2) |
| media del slippage de entrada | `ref_price`, `fill_price`, `slip_ticks`, `t_ref_bar`, `t_send`, `t_fill`, `nc` | 2 | 62 | σ es SUPUESTO (N = 2) |
| media del slippage de entrada | `ref_price`, `fill_price`, `slip_ticks`, `t_ref_bar`, `t_send`, `t_fill`, `nc` | 3 | 139 | σ es SUPUESTO (N = 2) |
| separar sistemático de aleatorio | lo anterior en **tamaños distintos** (nc 10 vs 40) y la dispersión vs `lat_ref_to_send_ms` | — | ≥ 30 por tamaño (≈ 60 sesiones en total) | sin datos de nc 10 en mano (Eric los tiene en TopstepX) |
| slippage de salida (SL/FLATTEN/liquidación) | `exec_exit` (precio de salida, disparador, tipo) | 2–4 (supuesto) | 60–250 por tipo (los SL y las liquidaciones son raros: ≈ 1 de cada 2 días en MES) | `exec_exit` es nuevo en el parche |

A ≈ 1 entrada por día hábil, 62 fills son ≈ 3 meses de calendario (4 meses con el calendario de feriados); 138 fills ≈ 6–7 meses. **La fuente más rápida es el historial de TopstepX que Eric exporte (MES nc 10 y 40, MEStest, MGC desde el 5-oct) cruzado con los `[OPEN]` de Telegram.**