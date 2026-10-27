# J4 — Parches propuestos (todos **NEEDS HUMAN REVIEW**, ninguno aplicado)

Lunes 26-oct-2026 · BORRADOR. CLAUDE.md regla 4: todo cambio a lógica que toca capital real (`pi_executor.py`, schedulers de ejecución, sizing/riesgo) requiere revisión humana antes de merge; yo propongo el diff, no lo apruebo ni lo mergeo. **Nada se empujó; nada toca `main`, el Pi ni Railway.** Los parches están hechos **sobre la rama candidata de J1** (`golive/cerebro2-mgc-candidate`, `2d45c71`), porque necesitan `execution/session_calendar.py` y las reglas de roll, que solo existen en `cerebro2-dev`.

## 1. Cuadro

| id | qué hace | archivos | estado por defecto | pruebas nuevas | efecto modelado | riesgo |
|---|---|---|---|---|---|---|
| **b** | flatten del Pi y del scheduler MES según el calendario de cierres anticipados de Topstep (26-nov 11:15, 27-nov y 24-dic 11:30 CT) en vez de 14:30 fijo | `pi/pi_executor.py`, `scheduler/geometry_scheduler.py` | **encendido** (en días normales no cambia nada: 14:30) | 10 | n/a (evita que Topstep liquide la posición antes que el Pi) | bajo en días normales; las fechas y la hora exacta de «cerrar por» vienen de Topstep Help (ver 3) |
| **f** | si la API no trae `activeContract`, el Pi aplica la regla de roll del oro (descarta contratos a ≤ 2 días hábiles de su aviso de entrega) en vez de «el vencimiento más cercano»; `ROLL_RULES` pasa a un módulo puro `execution/roll_rules.py` | `pi/pi_executor.py`, `execution/roll_rules.py` (nuevo), `execution/contracts.py` (re-exporta) | **encendido**; la marca de la API sigue mandando si viene | 9 (2 de ellas verifican que el Pi arranca sin `MASSIVE_API_KEY`) | evita operar **MGCV6** (vence ~28-oct) si falta el campo | bajo; ver 2 (hallazgo) |
| **a** | guardia de colchón del MLL: limita los contratos a los que caben con su pérdida máxima dentro del colchón y bloquea si no cabe ni uno | `pi/pi_executor.py`, `execution/mll_guard.py` (nuevo) | **APAGADO** (`GLITCH_PI_MLL_GUARD=si` la enciende; falla cerrado) | 15 | **negativo** (ver 4): baja el cobrado esperado | medio: depende de un piso que mantiene el operador |
| **c** | el scheduler MES en modo real deja de enviar señales cuando el intento más alto ya cruzó la meta del Combine, hasta que el operador lo reconoce (`GLITCH_ACK_PASE_INTENTO=<n>`) | `scheduler/geometry_scheduler.py` | **encendido** solo en modo real (`DRY_RUN=false`); no afecta paper | 8 | n/a | medio: falso positivo en el primer día de un intento nuevo si el anterior terminó en PASE (hay que reconocerlo una vez) |
| **d** | C3: tiempos de ejecución y slippage de entrada/salida (`exec_exit`) al historial, para cualquier producto incl. MGC; es el parche C3 del 24-oct rebasado sobre la pila | `pi/pi_executor.py`, `pi/slippage_pure.py` (nuevo) | encendido (solo agrega campos al log) | 23 | n/a (mide el slippage, DESCONOCIDO hoy) | bajo; ver `parteF/LEEME.md` |
| **e** | cron tras el cambio de hora | (solo configuración; sin código) | — | — | — | ver 6 |

**Resultado de pruebas (MEDIDO):** candidata 618 → con la pila **683 verdes, 0 fallos** (+65 = 10 de b + 9 de f + 15 de a + 8 de c + 23 de d; lista completa en `J4_resultado_pruebas.txt`). La pila se aplicó con `git am` sobre una copia limpia de la candidata y repitió 683. Aplicación **en orden**: `0001` (b) y `0004` (c) aplican solos sobre la candidata; `0002` (f), `0003` (a) y `0005` (d) dependen de la pila (comparten líneas de `pi_executor.py`). Archivos: `j4-patches/0001…0005-*.patch`.

## 2. Hallazgo de ingeniería que condiciona la forma de (f)

`execution/contracts.py` **exige `MASSIVE_API_KEY` al importarse** (lo tiene Railway; el Pi **no**: `pi_executor.py` lo dice en su encabezado). La primera versión de (f) importaba `apply_roll_rule` desde `contracts.py`: pasaba toda la suite (el `conftest` pone la variable) pero **habría tumbado el Pi en el arranque**. Lo vi al correr las pruebas nuevas en aislamiento. Por eso (f) mueve `ROLL_RULES` y sus funciones puras a `execution/roll_rules.py` (sin red ni variables de entorno) y `contracts.py` las re-exporta con los mismos nombres; hay una prueba que importa `pi.pi_executor` en un subproceso **sin** `MASSIVE_API_KEY`. Si Eric prefiere el cambio mínimo, la alternativa es no aplicar (f) y exigir el resultado de `check_contracts.py` (J2, 1.2) antes de operar.

(f) también cambió una prueba existente (`test_t4_pi_mgc.py::test_falls_back_to_nearest_with_warning_when_no_flag`): su expectativa («sin la marca, el más cercano = MGCV6») es justo la conducta peligrosa; ahora la prueba fija el reloj al 1-sep-2026 (antes de la ventana de roll) para conservar su sentido, y las nuevas cubren el 26/28-oct.

## 3. (b) Flatten por calendario

- Hoy el Pi aplana a las **14:30 CT fijo**; el calendario existía solo en el scheduler MGC de `cerebro2-dev` para decidir si enviar la señal. En un cierre anticipado, Topstep liquida las posiciones abiertas a la hora publicada; el flatten de las 14:30 llegaría tarde y el resultado quedaría mal registrado.
- Fechas en `execution/session_calendar.py` (fuente: Topstep Help, *holiday trading hours*, 13350348, según el propio archivo): 26-nov 11:45, 27-nov 12:00, 24-dic 12:00 CT = hora «cerrar posiciones por»; el flatten se hace 30 minutos antes (11:15 / 11:30). **No verifiqué esa página en esta sesión** (la cita viene del código de `cerebro2-dev`): ESTADO = reproducido del repo, NO VERIFICADO por mí. El propio archivo reconoce una ambigüedad: «cerrar por 12:00» vs «cierre a las 12:00 con posiciones planas a las 11:45»; el margen de 30 min es conservador para ambas lecturas.
- Cubre también el scheduler MES (modo real: «llegó después del cierre» y el flatten del paper). **No cubre** el calendario de EQUITY INDEX de CME (el cierre del 27-nov del S&P es 12:15 CT según CME, DESCONOCIDO aquí): el margen de 30 min lo absorbe.
- No toca el 28-oct ni los días normales (pruebas: 14:30 en un día normal; 11:31 el 27-nov aplana; 11:31 un día normal no aplana).

## 4. (a) Guardia de colchón del MLL — resultado del modelo: **negativo**

Simulé la política «contratos = ⌊colchón / $369⌋, máx 3, no operar si < $369» contra la de producción (`resultados_J4a.md`; 443 días reales de MGC, slippage empírico de 8 obs., 30 remuestras, diferencias pareadas):

| política | cobrado por XFA, WR 50 % [IC95] | Δ vs producción | P(muerte ≤ 3 días) | neto anual por cuenta (WR 50 / 47.4 %) |
|---|---|---|---|---|
| producción 3×364 | $633 [581, 651] | — | 17.5 % | $2,398 / −$244 |
| guardia | $517 [477, 545] | −$116 [−133, −85] (SÍ) | 2.5 % | $445 / −$600 |
| guardia estricta (< $800 no opera) | $406 | −$226 (SÍ) | 1.9 % | −$99 / −$948 |
| guardia «solo 1 micro» | $477 | −$156 (SÍ) | 1.1 % | $265 / −$695 |

La guardia reduce casi a cero la muerte temprana, pero **una cuenta viva que no puede operar no cobra**: el cobrado esperado cae 12–35 % y el neto anual de la cadena cae más (el motor cierra la cuenta «zombi» tras 30 días sin operar; un operador la abandonaría antes, así que el número es conservador contra la guardia). **No recomiendo encenderla.** Se entrega apagada y falla cerrada para que Eric decida si alguna vez prioriza la supervivencia de la cuenta sobre el cobro. Limitación de diseño: el piso del MLL lo mantiene el operador (`GLITCH_PI_MLL_FLOOR_USD`, absoluto en USD); la API de ProjectX no lo entrega (DESCONOCIDO si algún endpoint lo da), y calcular el máximo de balances de cierre dentro del Pi habría agregado estado a `_finalize_cycle`, que no quise tocar sin revisión.

## 5. (c) Guardia de PASE

- El scheduler MES solo incrementaba la etiqueta `intento` al cruzar la meta ($3,000) y seguía enviando señales; con la Combine cerrada el Pi fallaba después («la cuenta no está entre las activas», ya cubierto por el Pi). Ahora, en modo real, si el intento **más alto** del historial acumula ≥ la meta (con el piso trailing), el scheduler **no envía** y manda «PASE DETECTADO» a Telegram cada día hasta que Eric lo reconozca con `GLITCH_ACK_PASE_INTENTO=<n>`.
- Es una **alerta conservadora**, no una declaración de PASE: no verifica consistencia ni días mínimos de Topstep; Eric lo confirma en TopstepX.
- Falso positivo conocido: si el último intento del historial (p. ej. de la época de paper) ya terminó en PASE, el primer día de un intento nuevo queda bloqueado hasta reconocerlo una vez.
- Efecto sobre el Pi: ninguno (ya rechazaba cuentas no activas). Lo que sí hace falta, por separado, es **detener el cron de GEOMETRY (MES)** en Railway tras el PASE si no se comprará otra Combine (J2, 3.1).

## 6. (e) Cron tras el cambio de hora (sin código)

Los crons de Railway son UTC fijo. Estados Unidos termina el horario de verano el **domingo 1-nov-2026**: hasta el sábado 31-oct CT = UTC−5 (CDT); desde el domingo UTC−6 (CST). Monterrey es UTC−6 todo el año.

| servicio | hasta el vie 30-oct (CDT) | desde el lun 2-nov (CST) | hora CT objetivo |
|---|---|---|---|
| GEOMETRY-MGC | `0 12 * * 1-5` | `0 13 * * 1-5` | 7:00 CT (el scheduler espera hasta 7:13) |
| GEOMETRY (MES) | `25 14 * * 1-5` | `25 15 * * 1-5` | 9:25 CT (espera hasta 9:35) |

El valor actual del cron de cada servicio: **DESCONOCIDO** (Railway; Eric). **Cuál es el error caro:** como los schedulers esperan por reloj CT hasta su compuerta de entrada, un cron **demasiado temprano** es inofensivo (solo espera más); uno **demasiado tarde** pierde el día (el Pi descarta señales después de `GLITCH_PI_ENTRY_DEADLINE_CT`: 08:00 en la instancia MGC). Por eso: **no adelantar al horario nuevo antes de que cambie la hora** (p. ej. dejar `0 13` el jueves 29 = 8:00 CT ⇒ señal descartada). Hacer el cambio el **domingo 1-nov** o el lunes 2-nov antes de las 6:00 CT; si se olvida, el horario viejo (`0 12` = 6:00 CST) sigue funcionando.

## 7. No hecho / pendiente

- (a) y (b) se probaron con un cliente de prueba (`FakeClient`), no contra ProjectX; el comportamiento real (campos de la cuenta, `balance`) es DESCONOCIDO hasta la primera sesión.
- No agregué la señal de «entrada después del flatten del día» en el Pi (el scheduler MGC y el límite `GLITCH_PI_ENTRY_DEADLINE_CT` ya la cubren en la práctica).
- Cierres anticipados posteriores al 24-dic y 2027: Topstep solo había publicado 2026 y el 1-ene-2027 (según el archivo).
