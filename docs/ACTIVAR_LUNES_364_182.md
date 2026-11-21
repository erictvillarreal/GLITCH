# ACTIVAR_LUNES_364_182 — XFA de MGC: SL 364 / TP 182, 4 micros, 12 el viernes, candado de cobro (20-nov-2026) — NEEDS HUMAN REVIEW (CLAUDE.md regla 4)

**Estado:** código listo, **apagado por defecto** (sin las variables nuevas todo se comporta como hoy). Rama local `feat/xfa-lunes-364-182`, 1 commit sobre `origin/main` (aa7b76d), **810 pruebas verdes** (770 + 40 nuevas). Nada se aplica hasta que Eric revise, mezcle y cambie las variables. Un agente propone el diff; no lo aprueba ni lo mezcla.

## Qué cambia en el código (4 cosas, todas con funciones puras en `strategies/sizing_pure.py`)
1. **Geometría 364/182** (SL 364, TP 182) se agrega a `XFA_GEOMETRIES`. Las demás combinaciones siguen rechazándose.
2. **Dirección con expiración** (scheduler MGC): `GLITCH_XFA_DIRECTION=always_short|always_long|alternate` **solo se aplica si** `GLITCH_XFA_DIRECTION_UNTIL=AAAA-MM-DD` (inclusive) es una fecha válida; pasada la fecha vuelve sola a `alternate`. Sin fecha válida se ignora y se registra. Solo cuenta real MGC (`DRY_RUN=false`).
3. **Palanca del viernes** (Pi): `GLITCH_PI_XFA_LASTDAY=2026-11-27:12` → ese día (hora de Chicago) se operan 12 micros si todavía no se llegó a U ni se cobró. Solo actúa con `GLITCH_PI_XFA_SIZE_RULE` puesta.
4. **Candado de cobro hecho** (Pi): el Pi guarda en disco `saldo previo + P&L` tras cada cierre (`~/.glitch_pi_xfa_latch_mgc.json`, en el directorio de estado del Pi). Si al día siguiente el saldo está **más de $100 por debajo** del esperado, lo toma como cobro hecho, avisa por Telegram (`[CANDADO COBRO]`) y opera `GLITCH_PI_XFA_POST_PAYOUT_NC` micros (1 por defecto). `GLITCH_PI_XFA_PAYOUT_DONE=si` lo fuerza a mano. Un archivo ilegible se trata como cobro hecho (falla seguro). Un falso positivo solo achica el tamaño.

## Variables para el lunes 23-nov (MODELADO: 364/182, 4 micros L-X, 12 el viernes, cobrar a $250, después 1 micro)
| dónde | variable | valor |
|---|---|---|
| Railway (servicio MGC) | `GLITCH_XFA_BRACKET_TICKS` | `364` |
| Railway (servicio MGC) | `GLITCH_XFA_TP_TICKS` | `182` (hoy `728`) |
| Railway, **solo si Eric decide el override** | `GLITCH_XFA_DIRECTION` + `GLITCH_XFA_DIRECTION_UNTIL` | `always_short` + `2026-11-27` (toda la semana) o `2026-11-23` (solo el lunes) |
| Pi (`~/.glitch_pi.env`) | `GLITCH_PI_XFA_SIZE_RULE` | `4:250:1` (4 micros mientras el saldo < $250; 1 micro desde $250 hasta que se pida el cobro) |
| Pi | `GLITCH_PI_XFA_START_BALANCE_USD` | `0` (verificar contra TopstepX: la API debe mostrar +$28.28 el lunes) |
| Pi | `GLITCH_PI_XFA_LASTDAY` | `2026-11-27:12` |
| Pi | `GLITCH_PI_XFA_POST_PAYOUT_NC` | `1` (es el default) |
| Pi | `GLITCH_PI_NC_MAX` | **quitar** (o `12`). Hoy está en `1` según el runbook del 15-nov: el tope se aplica ANTES y DESPUÉS de la regla de tamaño y dejaría todo en 1 micro |
| Pi | `GLITCH_PI_MLL_GUARD` | no ponerlo en `si` (con 12 micros y SL 364 reduciría o bloquearía la entrada) |

## Pasos (los hace Eric; entre sesiones y con la cuenta plana; nunca con una posición abierta)
1. Revisar: `git diff origin/main...feat/xfa-lunes-364-182 --stat` (`sizing_pure.py`, `geometry_mgc_scheduler.py`, `pi_executor.py`, pruebas, este documento). Empujar la rama, abrir el PR y mezclar a `main`.
2. **Confirmar de qué rama despliega Railway (servicio MGC):** el código de `GLITCH_XFA_TP_TICKS` solo existe en `main`, así que debería ser `main`, pero no está verificado. Después, en el Pi: `git pull` de `main` y reiniciar el servicio con la cuenta plana.
3. Poner las variables (arriba). Railway antes de las 11:00 UTC (5:00 CT) para no tocar el servicio mientras corre. La señal del scheduler sale ~07:13 CT; el override de dirección debe estar puesto antes.
4. Verificación sin mercado (en el Pi y en una terminal con el mismo entorno del servicio):
   - `python -c "import pi.pi_executor as p; print(p.XFA_SIZE_RULE, p.XFA_LASTDAY, p.XFA_POST_NC, p.NC_MAX, p.XFA_START_BALANCE)"` → `(4, 250.0, 1) (datetime.date(2026, 11, 27), 12) 1 None 0.0`
   - `python -c "import scheduler.geometry_mgc_scheduler as m, datetime as dt; print(m.REAL_CFG.sl_ticks, m.REAL_CFG.tp_ticks, m._direction_mode(dt.date(2026,11,23)))"` con `DRY_RUN=false GLITCH_PRODUCT=MGC` → `364 182 always_short` (o `alternate` sin override).
5. **Lunes:** el Telegram `[SEÑAL ENVIADA AL PI]` debe decir `SL/TP: 364/182` y la dirección elegida; el `[OPEN]` del Pi debe decir `Contracts: 4`, SL ≈ 36.4 puntos y TP ≈ 18.2 puntos. El log del Pi: `regla de tamaño XFA: saldo $28.28 -> 4 micros (regla 4:250:1: 4 micros)`.
6. **Cuando el saldo llegue a $250 o más (TopstepX):** pedir el cobro ese mismo día al cierre (4:00 PM CT). Mientras no se pida, el Pi opera 1 micro. Al día siguiente debe llegar `[CANDADO COBRO]` y el log `cobro hecho (candado): 1 micros`. **Si no llega y el Pi muestra 4 micros:** poner `GLITCH_PI_XFA_PAYOUT_DONE=si` y reiniciar con la cuenta plana (o `GLITCH_PI_NC_MAX=1`).
7. **Viernes 27-nov:** nada que hacer; si todavía no se cobró, el log debe decir `ultimo dia 2026-11-27: 12 micros`. El Pi sigue cerrando a las 11:30 CT por el cierre anticipado (`execution/session_calendar.py`).
8. Anotar fecha y sesión de cada cambio para separar los datos reales.

**Volver atrás:** Railway `GLITCH_XFA_TP_TICKS=728` y `GLITCH_XFA_BRACKET_TICKS=364`, quitar `GLITCH_XFA_DIRECTION*`; Pi `GLITCH_PI_NC_MAX=1` y quitar `GLITCH_PI_XFA_LASTDAY`.
**Si el parche no está mezclado y desplegado a tiempo (plan B sin código):** 364/364 con `GLITCH_PI_XFA_SIZE_RULE=4:250:1` y, el jueves por la noche, `12:250:1` a mano; el cobro se pide a mano y después `GLITCH_PI_NC_MAX=1` a mano (modelado en LUNES9B: 58 % / 64 % de pedir el cobro en la semana, $373 / $457).

## Riesgos conocidos (leer antes de activar)
- **Perfil TP menor que SL** (364/182): «perdedor mayor que ganador» es motivo citado del RTP; los umbrales no están publicados. Un día de SL con 4 micros pierde $1,456 (la cuenta sigue viva con colchón de $2,000 desde el saldo actual; el segundo SL la liquida).
- **12 micros el viernes:** el MLL liquida a ~167 ticks en contra (2,000 / 12); es el último intento de la semana y se acepta; es 1 trade de los 4.
- **Candado:** la detección usa el P&L del Pi; si el Pi marca un resultado `UNKNOWN` ese día no hay detección y hay que usar `GLITCH_PI_XFA_PAYOUT_DONE=si`. Para reiniciarlo: borrar `~/.glitch_pi_xfa_latch_mgc.json` y reiniciar el Pi.
- **Dirección:** `always_short` es una apuesta direccional, no una ventaja demostrada (0 de 23 pruebas); ver `experimentos/estructura/LUNES12.md` y `LUNES12B.md`.
- Wire de $30 por cobro (no está en el modelo); aprobación 1-3 días hábiles y desembolso 7-10 más.
- Estados sin verificar hoy: `GLITCH_PI_NC_MAX`, `GLITCH_PI_MLL_GUARD` y la rama que despliega Railway.
