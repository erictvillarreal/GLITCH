# ACTIVAR_GEOMETRIA_XFA — TP independiente del SL en la XFA de MGC (2-nov-2026) — NEEDS HUMAN REVIEW (CLAUDE.md regla 4)

**Estado:** código listo, **apagado por defecto** (sin variables nuevas la señal sale igual que hoy). Rama `feat/xfa-geometria-tp`, 765 pruebas verdes (745 + 20 nuevas). Nada se aplica hasta que Eric revise el diff, mezcle el PR y ponga las variables.
**Qué cambia:** `GLITCH_XFA_TP_TICKS` (junto con `GLITCH_XFA_BRACKET_TICKS`, que sigue siendo el SL) permite un objetivo distinto del stop, **solo** para estas geometrías modeladas (SL, TP en ticks de MGC): **(364, 364)** y **(728, 728)** (las de hoy), **(364, 728)** (variante C «equilibrada») y **(120, 360)** (variante D «defensiva»). Cualquier otra combinación se ignora, se registra un error en el log y la señal conserva la geometría actual. El Pi ya acepta SL y TP independientes (hasta 4× lo configurado).

## Variables por variante (hoy en producción: Railway `GLITCH_XFA_BRACKET_TICKS=728`; Pi regla `5:1500:1`, tope `GLITCH_PI_NC_MAX=1` hasta la sesión 5)
| variante | Railway (servicio MGC) | Pi (`~/.glitch_pi.env`) |
|---|---|---|
| **C · equilibrada** (SL 364 / TP 728, **2 micros fijos**) | `GLITCH_XFA_BRACKET_TICKS=364` y `GLITCH_XFA_TP_TICKS=728` | **quitar** `GLITCH_PI_XFA_SIZE_RULE` (si no, sube a 5 micros) y poner `GLITCH_PI_NC_MAX=2` |
| **D · defensiva** (SL 120 / TP 360, 3 micros hasta $1,500 de saldo, luego 1) | `GLITCH_XFA_BRACKET_TICKS=120` y `GLITCH_XFA_TP_TICKS=360` | `GLITCH_PI_XFA_SIZE_RULE=3:1500:1` y `GLITCH_PI_NC_MAX=9` |
| **Volver a hoy (A)** | `GLITCH_XFA_BRACKET_TICKS=728` y **quitar** `GLITCH_XFA_TP_TICKS` | `GLITCH_PI_XFA_SIZE_RULE=5:1500:1`; `GLITCH_PI_NC_MAX=1` hasta la sesión 5, luego `9` |
`GLITCH_PI_XFA_START_BALANCE_USD=0` se queda igual. Nada de `GLITCH_PI_MLL_GUARD=si`.

## Cómo aplicarlo sin riesgo (cuando Eric decida)
1. Revisar el diff (`strategies/sizing_pure.py`, `scheduler/geometry_mgc_scheduler.py`, pruebas) y mezclar el PR a `main`. Railway redespliega con las variables viejas: la señal NO cambia.
2. Cambiar variables **entre sesiones**, nunca con una posición abierta: primero Railway (el servicio corre al día siguiente), luego el Pi (reinicio solo con la cuenta plana).
3. En la primera sesión revisar el Telegram `[SEÑAL ENVIADA AL PI]` (debe decir los SL/TP nuevos) y el log del Pi (contratos operados y brackets colocados).
4. Anotar la fecha y la sesión del cambio para separar los datos reales por variante.

## Lo que el modelo dice (MODELADO, lado al azar; ver `experimentos/estructura/`)
C: cobra 47 de cada 100 (A: 34), el primer pago llega en la sesión 10 mediana (≈ 2 semanas de operación) y la que cobra se lleva ≈ $1,585 (A: $2,538); cubrir $345 pasa de 33 % a 38 %, y $720 de 30 % a 27 %. Costo en cobrado medio contra A: −$71 [−$160, +$59] (no se distingue de cero). **No cumplió el criterio estricto preregistrado en un tercio de los datos** y nunca se ha probado en vivo.

## Despliegue elegido por Eric (15-nov-2026): SL 364 / TP 728 con 1 micro — NEEDS HUMAN REVIEW (CLAUDE.md regla 4)
**Qué cambia en producción:** solo dos variables en Railway (servicio MGC). **El Pi NO se toca** (sigue con su tope local de 1 micro y su regla actual). El Pi ya coloca el TP y el SL con distancias independientes (`pi_executor.py`, precios de TP y SL calculados con `signal["tp_ticks"]` y `signal["sl_ticks"]`) y acepta hasta 4× los ticks de CFG, así que 364/728 pasa su validación.
**Verificación hecha antes de pedir el merge:** rama `feat/xfa-geometria-tp` = 1 commit sobre `origin/main` (0 atrás, 1 adelante, sin conflictos); `tests/test_sizing_pure.py` 70 pasan; suite completa **765 pasan**.
**Pasos (los hace Eric, entre sesiones y con la cuenta plana; nunca con una posición abierta):**
1. Revisar el diff **contra `origin/main`** (la rama local `main` de la carpeta orphaned es otra línea de historia y no comparte base): `git diff origin/main...feat/xfa-geometria-tp --stat` (4 archivos: guía, scheduler, `sizing_pure.py`, pruebas).
2. `git push -u origin feat/xfa-geometria-tp`, abrir el PR hacia `main`, revisar y mezclar. Railway redespliega con las variables viejas: la señal NO cambia.
3. Con el servicio ya estable, en Railway (MGC): poner `GLITCH_XFA_TP_TICKS=728` y cambiar `GLITCH_XFA_BRACKET_TICKS` de `728` a `364`. Hacerlo antes de las 11:00 UTC (5:00 CT) para no tocar el servicio cerca de la señal de las 12:00 UTC.
4. Primera sesión: el Telegram `[SEÑAL ENVIADA AL PI]` debe decir `SL/TP: 364/728 ticks`; el `[OPEN]` del Pi debe mostrar SL ≈ 36.4 puntos y TP ≈ 72.8 puntos de la entrada, `Contracts: 1`. Si en el log de Railway aparece `no es una geometria modelada`, la variable está mal escrita y la señal conserva el bracket anterior.
5. Anotar fecha y sesión del cambio.
**Volver atrás:** `GLITCH_XFA_BRACKET_TICKS=728` y **quitar** `GLITCH_XFA_TP_TICKS` (entre sesiones). **Qué esperar (MODELADO, desde saldo −$745 y 3 días ganadores):** `experimentos/estructura/SEMANA_ESPERADA.md` y `HITOS.md` en la rama `experimentos-research`.
