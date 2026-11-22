# PLAN_SEMANA_23NOV_B — XFA de MGC, semana del 23 al 27-nov-2026, configuración B (500/250, 12 micros, cobro a $500) — NEEDS HUMAN REVIEW

**Decisión de Eric (21-nov):** iniciar la semana con **B**. Este plan no la cambia: la ejecuta, la verifica y dice qué hacer en cada escenario. **Nota de nombre:** «500/200» no existe en los estudios; se usa **500/250** (SL 500, TP 250) y el código rechaza 500/200. Etiquetas: MOD modelado (`LUNES17.md`, `LUNES18.md`), V verificado, NV no verificado. Horas: **CT = Monterrey** desde el 1-nov.

## 0. En 10 líneas
1. B = 500/250, 12 micros mientras el saldo < $500, pedir el cobro al llegar a $500, después 1 micro con la misma geometría (el resto de la configuración está en `ACTIVAR_LUNES_500_250.md`).
2. **La semana se decide el lunes** (MOD, realista): se pide el cobro 37 %, la cuenta muere 50 %, sigue viva sin cobrar 13 %. Martes a viernes agregan solo 4 puntos de cobro y 9 de muertes; el viernes ya no aporta.
3. Resultado de la semana: cobra 41 % / 45 % (realista / optimista); muere sin cobrar 59 % / 55 %; casi no hay caso intermedio (viva sin cobrar al viernes ≈ 0 %).
4. Si cobra el lunes: cobro neto mediano **$1,347** con el 50 % (o $112 con el mínimo), colchón que queda **$1,497** (o ~$2,868), 3 balas de 1 micro.
5. **Cambia solo en el Pi al cobrar:** contratos 12 → 1 (regla `12:500:1` más candado de cobro hecho), con aviso `[CANDADO COBRO]`. No cambian solos: la geometría, la dirección, el monto del cobro ni el segundo cobro (manuales).
6. Probado con pruebas ejecutables (`TestPlanBWeek`, 7 pruebas; suite completa verde).
7. Dirección: alternar pone el **lunes en LONG**; el lado del lunes pesa casi todo (§5). Decide Eric el domingo en la tarde.
8. Decisiones que siguen abiertas: **monto del primer cobro** (máximo o $125), **dirección del lunes**.
9. Si el lunes liquida la cuenta, se detiene el Pi y se documenta (§7); no se reabre la cuenta con otra configuración sin una decisión nueva en el registro.
10. Sin verificar: valor actual de `GLITCH_PI_NC_MAX` y `GLITCH_PI_MLL_GUARD` en el Pi, rama de Railway, comportamiento del Pi con una cuenta liquidada, calendario macro.

## 1. Salida (sábado y domingo)
Orden y comandos en `ACTIVAR_LUNES_500_250.md`. Lista de salida:
- [ ] PR revisado y mezclado a `main` (rama `feat/xfa-lunes-500-250`, 829 pruebas verdes).
- [ ] Railway (servicio MGC): `GLITCH_XFA_BRACKET_TICKS=500`, `GLITCH_XFA_TP_TICKS=250`; confirmar de qué rama despliega (NV).
- [ ] Pi (`~/.glitch_pi.env`), con la cuenta plana y reiniciando: `GLITCH_PI_XFA_SIZE_RULE=12:500:1`, `GLITCH_PI_XFA_START_BALANCE_USD=0`; **quitar** `GLITCH_PI_NC_MAX` (o 12); `GLITCH_PI_MLL_GUARD` no en `si`; no poner `GLITCH_PI_XFA_LASTDAY`.
- [ ] Comandos de verificación del runbook (el Pi imprime `(12, 500.0, 1) None 1 None 0.0`; el scheduler imprime `500 250 alternate`). Si imprime `364 364` hay un error de dedo en la geometría.
- [ ] `pi/ops/check_contracts.py`: contrato activo del lunes (corte del repo hacia MGCG7 el 26-nov).
- [ ] La API muestra el saldo +$28.28 (TopstepX igual).
- [ ] Domingo en la tarde (apertura de Asia): decidir la dirección (§5) y, si es override, poner `GLITCH_XFA_DIRECTION` y `GLITCH_XFA_DIRECTION_UNTIL` antes de las 07:00 CT del lunes.
- [ ] Decidir el monto del primer cobro (§4) para no decidirlo con prisa el lunes.

## 2. Calendario de la semana
| día | qué ocurre | qué hacer |
|---|---|---|
| Dom 22 tarde | abre Asia | decidir dirección; poner variables; verificar con el comando |
| Lun 23 | 07:13 señal; 07:15 entrada con 12 micros; flatten 14:20 | 06:30 revisar el log del Pi; 07:13 revisar el Telegram (`SL/TP: 500/250`, dirección) y el `[OPEN]` (`Contracts: 12`); **16:00 CT: aplicar la tabla de §3 al saldo de cierre** |
| Mar 24 | señal y entrada si la cuenta sigue viva y no cobró (con saldo >= $500 sin cobro: 1 micro; con cobro hecho: 1 micro) | revisar `[CANDADO COBRO]` y el `nc` del `[OPEN]`; 16:00 aplicar §3 |
| Mié 25 | igual | igual |
| Jue 26 | Thanksgiving, sin señal | revisión semanal; anotar en el registro (§8) |
| Vie 27 | cierre anticipado: flatten 11:30 CT; roll hacia MGCG7 según el repo | revisar contrato; 16:00 aplicar §3; cierre de la semana |

## 3. Escenarios y qué hacer (con la decisión de cada día a las 16:00 CT)
**Árbol del lunes (MOD, realista, 12 micros y lado según calendario):** liquida 46-50 %; **gran ganancia** (un TP, >= +$2,000) 29-33 %; **ganancia media** (+$472 a +$2,000) 7-10 %; **continúa** (pérdida parcial o ganancia chica) 11-14 %.

| escenario | prob. aprox. | estado al cierre | Pi | qué hace Eric |
|---|---|---|---|---|
| **S1 un TP el lunes** | 29-33 % | saldo ≈ $2,993 | pasa a 1 micro (regla, saldo >= $500) | **pedir el cobro** (máximo: neto ≈ $1,347 y quedan $1,497; mínimo: neto $112 y quedan ≈ $2,868); mañana debe llegar `[CANDADO COBRO]` |
| **S2 ganancia media** | 7-10 % | saldo $500 a $2,000 | 1 micro | pedir el cobro. Con el máximo el colchón queda en **$250 a $1,000** (de 0.5 a 2 balas de SL 500): evaluar el monto parcial para dejar al menos $500 (regla práctica NO modelada) |
| **S3 continúa** | 11-14 % | saldo < $500 (pérdida parcial) | sigue en 12 micros: el MLL decide el colchón, no el Pi | no pedir; revisar el saldo y el piso en TopstepX; seguir el plan |
| **S4 liquidada el lunes** | 46-50 % | cuenta cerrada | no hay cuenta activa (NV: cómo se comporta el Pi) | detener el Pi y el scheduler MGC para evitar señales sin cuenta; anotar en §8; decisión nueva antes de otra cuenta |
| **S5 cobra martes a viernes** | 5 puntos en total | saldo >= $500 tras una sesión | igual a S1/S2 | igual a S1/S2 |
| **S6 muere martes a viernes** | 9 puntos en total | cuenta cerrada | igual a S4 | igual a S4 |
Acumulado de la semana (MOD): cobro 41 % / 45 %; muere 59 % / 55 %; viva sin cobrar al viernes ≈ 0 %.
Después del primer cobro la semana sigue con S7-S9 de §6 (el segundo cobro necesita 5 días nuevos de al menos $150, así que no cae esta semana).

## 4. Qué cambia solo en el Pi cuando cobramos
Orden en el Pi: validar la señal (3 micros) → regla de tamaño y candado → tope `NC_MAX` → guardia de MLL (apagada). Probado en `tests/test_sizing_pure.py::TestPlanBWeek`.

| elemento | antes del cobro | después del cobro | ¿automático? | cómo | cómo verificarlo |
|---|---|---|---|---|---|
| **contratos** | 12 mientras el saldo < $500; 1 con saldo >= $500 mientras no se pida el cobro | **1 siempre** | **sí** | regla `12:500:1` + candado: `min(base, 1)`; detecta el cobro si el saldo baja más de $100 frente al esperado (saldo previo + P&L del trade) | Telegram `[CANDADO COBRO]`; log `cobro hecho (candado): 1 micros`; archivo `~/.glitch_pi_xfa_latch_mgc.json` con `latched: true` |
| saldo restante < $500 tras el cobro (cobro medio de un saldo de $500 a $1,000) | la regla sola daría 12 | 1 | sí (el candado) | prueba `test_small_win_then_payout_below_u...` | igual |
| otro cobro (el segundo) | — | sigue en 1 | sí: el candado no se reinicia solo | — | `latched: true` |
| geometría SL/TP | 500/250 | **500/250** (no cambia) | no cambia | LUNES16: misma geometría con 1 micro rinde más ($754) que 120/360 ($735, vive 91 %) | Telegram de la señal |
| dirección | alternar u override con fecha | igual; el override expira solo | automático | `GLITCH_XFA_DIRECTION_UNTIL` | `_direction_mode` |
| monto del cobro | — | — | **manual** | TopstepX | — |
| MLL | piso `min($0, pico − $2,000)` | **piso $0**: el colchón es el saldo restante | lo aplica Topstep | — | TopstepX |
| contador de días ganadores | 5 cumplidos | **0**: hacen falta 5 nuevos de >= $150 | lo aplica Topstep | — | TopstepX |
| segundo cobro | — | elegible con 5 días nuevos, saldo >= $250 y saldo > el que quedó tras el cobro | **manual** pedirlo | — | TopstepX |
| reiniciar el candado | — | solo manual | manual | borrar el archivo y reiniciar el Pi | — |
**Monto del primer cobro (decisión pendiente; manual en TopstepX).** En 60 sesiones desde el cobro, 1 micro (MOD, realista / optimista, entre quienes cobraron):
| monto | viva a 10 / 20 / 40 ses. | 2.º cobro a 20 / 40 / 60 ses. | sesiones hasta el 2.º cobro (mediana) | dinero a 60 ses. (cobro + extra) |
|---|---|---|---|---|
| **máximo 50 %** (neto ≈ $1,347) | 75 / 45 / 10 % · 80 / 55 / 18 % | 48 / 53 / 54 % · 60 / 65 / 66 % | 11 | $1,347 + $706 = **≈ $2,053** · $1,347 + $1,050 |
| **mínimo $125** (neto $112) | 91 / 77 / 38 % · 93 / 82 / 46 % | 52 / 61 / 63 % · 64 / 73 / 76 % | 12 | $112 + $1,324 = **≈ $1,436** · $112 + $1,882 |
El máximo da más dinero; el mínimo da más vida de la cuenta y más probabilidad de segundo cobro a 40-60 sesiones. Con 2 micros después del cobro todo empeora (viva a 40 sesiones 2 %; 2.º cobro 39 %).

## 5. Dirección (decide Eric el domingo)
Alternar da **lunes LONG**, martes SHORT, miércoles LONG y viernes LONG. Con B el lunes pesa casi todo.
| muestra (MOD, realista) | Lunes LONG: liquida / un TP | Lunes SHORT: liquida / un TP |
|---|---|---|
| histórico completo | 50 % / 29 % | 46 % / 33 % |
| últimas 126 sesiones | 65 % / 33 % | 52 % / 46 % |
| 19 sesiones reales | 79 % / 21 % | 47 % / 47 % |
| cobra en la semana: alternar / solo short / solo long | histórico 41 / 45 / 44 % | últimas 126: 33 / 46 / 33 %; reales: 27 / 59 / 27 % |
Después de una caída de 20 sesiones (151 días) el short no rinde más (44 contra 45 %): sin persistencia en 440 sesiones; la ventaja del short aparece en las sesiones recientes (en retrospectiva). El short no tiene ventaja demostrada (0 de 23 pruebas): es una apuesta direccional de Eric.
**Tres planes:** (a) alternar (default, no tocar nada); (b) solo el lunes en short: `GLITCH_XFA_DIRECTION=always_short` + `GLITCH_XFA_DIRECTION_UNTIL=2026-11-23` (de martes en adelante vuelve a alternar solo); (c) toda la semana short: `_UNTIL=2026-11-27`. El override se ve en el Telegram del lunes y se verifica con el comando del runbook.

## 6. Después del primer cobro: qué esperar (MOD, realista, 1 micro, máximo)
| escenario | probabilidad / tiempo | qué hacer |
|---|---|---|
| S7 sigue operando 1 micro, sin eventos | cuenta viva 88 % a 5 ses., 75 % a 10, 45 % a 20, 10 % a 40 | nada; el Pi opera solo con 1 micro; revisión diaria breve |
| S8 segundo cobro | acumulado 24 % a 10 ses., 48 % a 20, 53 % a 40; mediana 11 sesiones | cuando TopstepX muestre 5 días nuevos y saldo > saldo tras el cobro: pedirlo (máximo salvo decisión nueva) |
| S9 la cuenta muere antes del 2.º cobro | ≈ 46 % no logra el 2.º cobro en 60 sesiones (la cuenta muere antes) | detener y documentar |
Semana 2 (30-nov a 4-dic): **roll a MGCG7** (corte del repo el 26-nov; verificar `check_contracts.py` el fin de semana y el lunes 30), sin otros cambios. Cuando el saldo vuelva a >= $500 el Pi sigue en 1 micro por el candado: **subir contratos después del cobro es manual** (`GLITCH_PI_XFA_POST_PAYOUT_NC` y `lo` de la regla) y no está respaldado por el modelo (2 micros empeora).

## 7. Contingencias
| situación | qué hacer |
|---|---|
| `[CANDADO COBRO]` no llega tras un cobro y el Pi muestra más de 1 micro | `GLITCH_PI_XFA_PAYOUT_DONE=si` y reiniciar con la cuenta plana (o `GLITCH_PI_NC_MAX=1`) |
| `[CANDADO COBRO]` llega sin cobro (falso positivo) | solo achica el tamaño (seguro); si hay que reiniciar: borrar el archivo del candado y reiniciar el Pi con la cuenta plana |
| «BLOCKED sin barras» al inicio (ocurrió el 20-nov) | el Pi reintenta cada 120 s y avisa una vez por día; revisar el contrato con `check_contracts.py`; la entrada tiene límite a las 10:00 CT |
| resultado `UNKNOWN` en el `[CLOSE]` (liquidación o cierre manual) | no hay detección del cobro al día siguiente: revisar TopstepX; si hubo cobro, `GLITCH_PI_XFA_PAYOUT_DONE=si` |
| cuenta liquidada | detener el Pi y el scheduler MGC; anotar; **no** reabrir con otra configuración sin una decisión nueva en `PLAYBOOK_XFA_DECISIONES.md` §6 |
| Pi caído o reinicio inesperado | reiniciar con la cuenta plana; el marcador at-most-once evita doble entrada |
| geometría equivocada en el Telegram (`364/364`) | error de dedo en Railway; corregir entre sesiones; el scheduler no cambia solo |
| duda sobre el RTP | B opera tamaño máximo en todas las sesiones y tiene TP menor que SL; si Topstep contacta, documentar y detener |

## 8. Registro diario (alimenta el playbook)
Por cada sesión anotar: fecha y lado; `[OPEN]` (contratos, entrada, SL, TP); resultado y P&L; saldo y piso al cierre en TopstepX; qué decidió Eric a las 16:00 y por qué; eventos fuera del plan. Si algo contradice este plan (probabilidad modelada o tabla de §4), abrir una entrada nueva (D-11 en adelante) en `PLAYBOOK_XFA_DECISIONES.md`.

## 9. Pendientes y no verificado
Valor actual de `GLITCH_PI_NC_MAX` y `GLITCH_PI_MLL_GUARD` · rama que despliega Railway MGC · comportamiento del Pi con una cuenta liquidada · calendario macro · umbrales del RTP · el parche no se probó en vivo · la fase 2 usa todos los días del histórico (sin validación cruzada) · el árbol de §3 y las probabilidades son MODELADO con dos escenarios, no intervalos.
