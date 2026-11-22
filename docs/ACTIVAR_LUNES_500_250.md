# ACTIVAR_LUNES_500_250 — XFA de MGC: SL 500 / TP 250, 12 micros, pedir el cobro a $500 (21-nov-2026) — NEEDS HUMAN REVIEW (CLAUDE.md regla 4)

**Estado:** código listo, **apagado por defecto**. Rama local `feat/xfa-lunes-500-250` = rama `feat/xfa-lunes-364-182` (geometría 364/182, dirección con expiración, palanca del último día, candado de cobro hecho) **más** un commit que agrega **(500, 250)** a `XFA_GEOMETRIES`. **822 pruebas verdes.** Una sola rama permite activar cualquiera de las dos configuraciones con variables (ver `ACTIVAR_LUNES_364_182.md` para A). Esta configuración es la **B** de `PLAYBOOK_XFA_DECISIONES.md` §7 y es una **propuesta pendiente de confirmación** (D-09).

**Nombre de la geometría:** la lista cerrada solo acepta 500/250. **«500/200» no está modelada** y se rechaza: la señal conserva la geometría de hoy y el log dice `no es una geometria modelada`. Si el Telegram del lunes no dice `SL/TP: 500/250`, hay un error de dedo.

## Variables
| dónde | variable | valor |
|---|---|---|
| Railway (servicio MGC) | `GLITCH_XFA_BRACKET_TICKS` | `500` |
| Railway (servicio MGC) | `GLITCH_XFA_TP_TICKS` | `250` |
| Railway, solo si Eric decide el override | `GLITCH_XFA_DIRECTION` + `GLITCH_XFA_DIRECTION_UNTIL` | `always_short` + fecha (`2026-11-23` solo el lunes, `2026-11-27` la semana) |
| Pi (`~/.glitch_pi.env`) | `GLITCH_PI_XFA_SIZE_RULE` | `12:500:1` (12 micros mientras el saldo < $500; 1 micro desde $500 hasta que se pida el cobro) |
| Pi | `GLITCH_PI_XFA_START_BALANCE_USD` | `0` (la API debe mostrar +$28.28 el lunes) |
| Pi | `GLITCH_PI_XFA_POST_PAYOUT_NC` | `1` (default) |
| Pi | `GLITCH_PI_XFA_LASTDAY` | **no ponerla** (con 12 micros ya no aporta) |
| Pi | `GLITCH_PI_NC_MAX` | **quitar** o `12` (hoy está en `1` según el runbook del 15-nov) |
| Pi | `GLITCH_PI_MLL_GUARD` | no ponerlo en `si` (con 12 micros la guardia reduciría o bloquearía la entrada) |

## Cómo funciona (qué esperar; MODELADO, realista / optimista)
- **Un solo golpe:** 12 micros × TP de 250 ticks ≈ +$3,000 en un día ganador. El MLL liquida a ~167 ticks en contra (2,000 / 12), mucho antes del SL de 500. El primer día: ~48 % llega a la meta y ~51 % liquida la cuenta.
- **Resultado de la semana:** pide el cobro antes del cierre del viernes 41 % / 45 %; la cuenta muere sin cobrar 59 % / 55 %.
- **Si cobra:** cobro neto mediano $1,347 con el máximo del 50 %; colchón tras el cobro ~$1,497 (3 balas de 1 micro con SL de 500); cuenta viva 10 sesiones después 75 %; 2.º cobro 54 % si cobró el primero (22 % / 30 % incondicional).
- **Dinero total (cobro + fase 2 a 100 sesiones):** $754 / $987.

## Decisión pendiente: monto del primer cobro (se hace a mano en TopstepX)
| monto | cobra | dinero total | 2.º cobro | viva 10 ses. |
|---|---|---|---|---|
| **máximo (50 %)** | 41 / 45 % | $754 / $987 | 22 / 30 % | 75 % |
| 20 % del saldo | 41 / 45 % | $666 / $974 | 26 / 34 % | 89 % |
| **mínimo $125** | 41 / 45 % | $619 / $961 | 27 / 35 % | 91 % |
Con el cobro parcial el colchón queda casi intacto (~$2,850 con el mínimo) y la cuenta casi no muere; se paga con dinero inmediato (cobro neto de $112). El segundo cobro después siempre es hasta el 50 % del saldo.

## Pasos (los hace Eric; entre sesiones y con la cuenta plana; nunca con una posición abierta)
1. Revisar: `git diff origin/main...feat/xfa-lunes-500-250 --stat`. Empujar la rama, abrir el PR y mezclar a `main`. Confirmar de qué rama despliega Railway (NV; debería ser `main`).
2. Poner las variables de arriba (Railway antes de las 11:00 UTC; el Pi con la cuenta plana y reiniciarlo).
3. Verificación sin mercado (entorno del servicio):
   - `python -c "import pi.pi_executor as p; print(p.XFA_SIZE_RULE, p.XFA_LASTDAY, p.XFA_POST_NC, p.NC_MAX, p.XFA_START_BALANCE)"` → `(12, 500.0, 1) None 1 None 0.0`
   - `python -c "import scheduler.geometry_mgc_scheduler as m, datetime as dt; print(m.REAL_CFG.sl_ticks, m.REAL_CFG.tp_ticks, m._direction_mode(dt.date(2026,11,23)))"` con `DRY_RUN=false GLITCH_PRODUCT=MGC` → `500 250 alternate` (o `always_short` con override).
4. **Lunes:** el Telegram `[SEÑAL ENVIADA AL PI]` debe decir `SL/TP: 500/250`; el `[OPEN]` debe decir `Contracts: 12`, SL ≈ 50 puntos y TP ≈ 25 puntos. Log: `regla de tamaño XFA: saldo $28.28 -> 12 micros`.
5. **Cuando el saldo llegue a $500 o más:** pedir el cobro ese día al cierre (4:00 PM CT) con el monto elegido. Al día siguiente debe llegar `[CANDADO COBRO]`; si el saldo restante es >= $500 la regla ya baja sola a 1 micro. Si no llega y el Pi muestra 12 micros con saldo restante menor a $500: `GLITCH_PI_XFA_PAYOUT_DONE=si` o `GLITCH_PI_NC_MAX=1` y reiniciar con la cuenta plana.
6. Anotar fecha y sesión de cada cambio.

**Volver atrás:** Railway `GLITCH_XFA_BRACKET_TICKS=364`, `GLITCH_XFA_TP_TICKS=182` (o `728`); Pi `GLITCH_PI_XFA_SIZE_RULE=4:250:1` y `GLITCH_PI_NC_MAX=1`.

## Riesgos conocidos
- **RTP por tamaño máximo:** 12 micros en TODAS las sesiones y TP menor que SL. Los dos son motivos citados; los umbrales no están publicados. En A solo el viernes opera a 12 micros.
- **La cuenta muere sin cobrar 59 % / 55 % de las veces** (A: 30 % / 26 %); en el real de las 19 sesiones, 39 % de cobrar la semana.
- **Un solo golpe:** no hay colchón intermedio; el primer SL o el MLL en contra liquida.
- Wire de $30; aprobación 1-3 días hábiles y desembolso 7-10 más; la fase 2 usa todos los días del histórico (sin validación cruzada).
- Estados sin verificar: `GLITCH_PI_NC_MAX`, `GLITCH_PI_MLL_GUARD`, rama de Railway; el parche no se probó en vivo.
