# resultados_F3_slippage — slippage de entrada en MES (nc 40, TP 32 desde la REFERENCIA, SL 100, liquidación a 40 ticks del fill por el MLL de $2,000)

492 días reales (ventana 9:30 → 14:30 CT). Convención: slip > 0 = fill peor que la referencia (adverso); slip < 0 = fill mejor (a favor). Salida del SL con 3 ticks de gap (convención de las partes A–D). Cada tick por contrato vale $1.25; con 40 contratos, **1 tick = $50**.

## 1. Aritmética exacta (sin simulación)

| slip (ticks) | TP medido desde el fill | $ neto por TP (40 ctr.) | ¿2 TP alcanzan $3,000? | P(TP antes que liquidación) si el precio fuera martingala desde el fill = 40/(40 + TP) |
|---|---|---|---|---|
| -2 | 34 | $1,651.20 | sí (2 TP = $3,302.4) | 54.1 % |
| -1 | 33 | $1,601.20 | sí (2 TP = $3,202.4) | 54.8 % |
| +0 | 32 | $1,551.20 | sí (2 TP = $3,102.4) | 55.6 % |
| +1 | 31 | $1,501.20 | sí (2 TP = $3,002.4) | 56.3 % |
| +2 | 30 | $1,451.20 | no (2 TP = $2,902.4) | 57.1 % |
| +3 | 29 | $1,401.20 | no (2 TP = $2,802.4) | 58.0 % |
| +4 | 28 | $1,351.20 | no (2 TP = $2,702.4) | 58.8 % |

Lectura: el slippage adverso **acorta** la distancia al TP (más probable tocarlo) y **reduce** lo que paga; con la liquidación a 40 ticks del fill, la probabilidad de TP sube ≈ +0.8 pp por tick, y el dólar por TP baja $50 por tick. Con ≥ 2 ticks adversos, dos TP ya no suman $3,000 (acantilado: hacen falta tres).

## 2. Días reales, dos modelos del slippage (motor de las Partes A–D)

**M1 — el precio SE MOVIÓ antes del fill (ruido de precio, media cero):** el camino real sigue desde el fill; el TP queda a 32 − s ticks del fill, la liquidación a 40. **M2 — costo de ejecución puro:** el camino real no cambia (empieza en la referencia), el fill es s ticks peor: el TP sigue a 32 desde la referencia pero paga 32 − s, y la liquidación queda a 40 − s de la referencia.

| slip | M1: TP % | M1: P&L/día (L / C) | M1: P(pasar) | M2: TP % | M2: P&L/día (L / C) | M2: P(pasar) |
|---|---|---|---|---|---|---|
| -2 | 53.4 | $-137 / $+38 | 28.3 % | 55.8 | $-33 / $+112 | 31.0 % |
| -1 | 53.8 | $-141 / $+17 | 28.8 % | 55.5 | $-68 / $+69 | 30.7 % |
| +0 | 54.8 | $-123 / $+18 | 29.9 % | 54.8 | $-123 / $+18 | 29.9 % |
| +1 | 56.0 | $-114 / $+40 | 31.3 % | 54.0 | $-185 / $-32 | 29.0 % |
| +2 | 56.5 | $-113 / $+18 | 21.0 % | 53.5 | $-225 / $-81 | 18.0 % |
| +3 | 57.0 | $-127 / $+6 | 21.1 % | 52.7 | $-272 / $-137 | 17.2 % |
| +4 | 57.5 | $-134 / $-10 | 21.3 % | 51.9 | $-324 / $-191 | 16.1 % |

Entre 0 y 3 ticks adversos, por tick: **M1** P(TP) +0.75 pp, P&L medio/día -2.5 $, P(pasar) -2.9 pp · **M2** P(TP) -0.68 pp, P&L medio/día -50.5 $, P(pasar) -4.2 pp.

## 3. Cómo se interpreta (hechos vs supuestos)

- **Hecho (resultado):** los **dólares por TP bajan $50 por tick adverso en ambos modelos** (parte de tu hipótesis, confirmada). **P(TP) sube con el slippage adverso solo en M1** (el precio se movió y el TP quedó más cerca del fill) y **baja en M2** (costo puro: la liquidación queda más cerca y el camino no cambia). Así que ‘sube P(TP)’ es cierto para el slippage que es movimiento de precio y falso para el que es costo de ejecución. Para el lado favorable es simétrico.
- **Qué es el slippage observado (3 ticks el martes 20-oct, ≈ 1 el lunes 19):** el Pi toma como referencia el cierre de la última barra de ProjectX de los últimos 15 min (`_reference_price`) y el fill ocurre segundos después. Parte de la diferencia es **movimiento del precio** (media cero, p. ej. 1 minuto de volatilidad a las 9:35) y parte es **costo de ejecución** (medio spread + impacto de 40 contratos, > 0). **No está medida la mezcla**: con N = 2 no se puede separar (NO VERIFICADO). Si fuera solo ruido de precio, el EV por trade no cambia y solo cambia la forma del pago (acantilado); si fuera costo, cada tick adverso cuesta ≈ $50 por trade.
- **Orden límite ‘marketable’ / tolerancia (tope de k ticks adversos; si no llena, no hay trade ese día):** convierte la distribución de slippage en una truncada. Ventaja: nunca se opera con TP efectivo < 32 − k (con k = 1 siempre alcanzan 2 TP, $3,002.4 > $3,000). Costo: días sin operar (el Combine cuesta ≈ $49/mes, no hay límite de días) y el riesgo de no llenar justo en los días de movimiento fuerte a favor del lado jugado. **No se puede cuantificar sin la distribución de slippage**: falta el registro (parche C3).
- **Prioridad:** (1) **C3** (registro de `ref_price`, `fill_price`, `slip_ticks` por sesión): sin 20–30 sesiones no hay ni la media ni la dispersión. (2) Solo después decidir entre tolerancia / límite / anclar el bracket al fill. Anclar al fill (colocar TP/SL tras conocer el fill) elimina el acantilado pero deja una ventana sin protección de segundos: la propia regla de diseño del Pi (‘entrada y protección juntas’) lo impide; requiere revisión humana.