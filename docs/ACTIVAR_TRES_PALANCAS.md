# ACTIVAR_TRES_PALANCAS — finish-line + bracket 728 + regla de tamaño (29-oct-2026)

NEEDS HUMAN REVIEW (CLAUDE.md regla 4). Nada de esto está en `main`, en Railway ni en el Pi: es la rama local `golive/cerebro1-finish-line` (commit `3a65a48`, encima de `golive/cerebro2-mgc-candidate-k1` = 073dd54). 745 pruebas verdes (695 de la pila + 50 nuevas; `tests/test_sizing_pure.py`). Entrega: `0001-Tres-palancas-...patch` y `golive-cerebro1-finish-line.bundle` (misma carpeta). Estado de producción real (Railway/Pi): **NO VERIFICADO** — esta sesión no los alcanza; lo que dice el repo es 40 contratos fijos (MES) y MGC 3×364 (XFA).

## Qué cambia y cómo se enciende (los tres interruptores están APAGADOS por defecto)

| palanca | dónde | variable de entorno | valor | qué hace |
|---|---|---|---|---|
| **Finish-line** (Combine, MES) | servicio Railway de GEOMETRY-MES | `GLITCH_ADAPTIVE_NC` | `finish_line` | achica contratos cuando un TP ya cubre el faltante; el faltante usa la consistencia de Topstep: `max($3,000, mejor_día/0.55) − P&L del intento`. Solo reduce, nunca pasa de 40. |
| **Bracket 728** (XFA, MGC) | servicio Railway de MGC en modo real | `GLITCH_XFA_BRACKET_TICKS` | `728` | la señal sale con SL = TP = 728 ticks (hoy 364). Solo se aceptan 364 y 728. |
| **Regla de tamaño** (XFA, MGC) | Pi (`~/.glitch_pi.env`) | `GLITCH_PI_XFA_SIZE_RULE` | `5:1500:1` | 5 micros mientras (balance de la API − 50,000) < $1,500; después 1. Opcional: `GLITCH_PI_XFA_START_BALANCE_USD` (50000). |

Revertir = quitar la variable (o ponerla en `fixed` / `364` / vacía) y reiniciar el servicio. Valores mal escritos se ignoran y se registran en el log (no tumban el arranque).

## Condiciones antes de encender (las que importan)

1. **No combinar la regla de tamaño con `GLITCH_PI_MLL_GUARD=si`** si el bracket es 728: la guardia limita los contratos a los que caben con su *stop* dentro del colchón (728 ticks × $1 por micro) y recortaría o bloquearía la entrada. Hoy está apagada por defecto.
2. **`GLITCH_PI_NC_MAX`** debe estar sin definir o ≥ 5; si no, el tope local manda y la regla no sube a 5 (diseño: el tope siempre gana).
3. **El Pi debe leer el balance de la XFA por la API** (`get_accounts().balance`). Que ese campo sea el saldo real de la XFA después de un pago: **NO VERIFICADO en vivo**. Si falta, el Pi conserva el tamaño de la señal (3) y lo registra; no bloquea. Primer día: comparar la línea `regla de tamaño XFA … saldo $X` del log del Pi con el saldo que muestra TopstepX.
4. **El saldo de la regla es el de la XFA actual de Eric**: si ya está sobre +$1,500, la regla opera 1 micro (no 5). Dime el balance/colchón para recalcular el valor esperado en tu estado.
5. El finish-line **no mejora la XFA ya fondeada**; sirve para las *próximas* Combines.

## Lo que Topstep Support contestó (28-oct) y lo que NO

- Cambiar el tamaño de un día al otro según el saldo o la distancia a la meta **no** figura como conducta prohibida ni como disparador del RTP; stop mayor que el MLL permitido; brackets no prohibidos (solo el abuso de SIM con brackets ajustados/auto-breakeven). Consistencia: mejor día ≤ 55 % de la meta original; si se excede, la meta sube. Pase mínimo 2 días; el día se bloquea a las 4:00 PM CT; el MLL se vigila en tiempo real con P&L no realizado.
- **No contestó:** umbrales numéricos del RTP (no publicados; salir del RTP exige Live Funded + $10,000 netos + apelación); si el piso del MLL sube con el pico intradía o con el cierre del día (**el motor supone cierre del día**; si fuera intradía, los números de abajo bajan); P6–P10 del ticket.

## Cifras (MODELADO, no auditado) — de dónde sale «$2,425»

`optimo/resultados_OPT_CADENA.md`: neto anual por cuenta, WR 47.4 %, costos $245/año, finish-line + regla 5→1 @ $1,500 + bracket 728 = **$2,425** (con costos $290: $2,380; con $640: **$2,030**). Para comparar: hoy (40 fijos + 3×364) = $19 a ese WR. A WR 50 %: $5,713 vs $2,733.

Por qué leerlo como techo indicativo y no como promesa:
- La regla (5 / $1,500 / 1) se **eligió en el 60 % viejo** de los datos; fuera de muestra (40 % reciente, `resultados_OPT_XFA_ROBUSTEZ.md`) la ganancia por XFA fue **+$72 a +$257**, no el valor de entrenamiento. La cadena usa un solo conjunto de bancos.
- WR 47.4 % es el medido con IC95 [41, 54]; cada punto de WR vale ≈ $1.0k/año/cuenta.
- 12 XFAs alcanzadas al año y el costo de $245/año son SUPUESTOS (los $640 recurrentes de Eric están sin ver estados de cuenta).
- Con 728 y 5 micros el MLL ($2,000 / 5 micros) te liquida a ≈ 400 ticks en contra: una sola racha mala acaba la cuenta; ya está en el modelo (vida media 8.3 días) pero la varianza por cuenta es alta.
- Slippage: 8 observaciones de MES, la 8.ª inferida = 0 (NO VERIFICADA).
