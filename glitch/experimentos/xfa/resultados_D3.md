# resultados_D3 (DP de (tamano, cobro); N=50000 vidas de validacion; semilla 20261020; reglas base SIN la regla de ganancia desde el ultimo pago)

Estados en rejilla de $50; transicion = distribucion empirica de W2 (MGC limpio SIN oro, ambos lados mezclados); acciones nc en (1, 2, 3, 4, 5, 6, 8) y pedir/esperar el pago maximo cuando wd = 5.

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| DP SL=TP=364: V0 de la DP = $931 (253 barridos, delta 0.020); MC del motor completo: | $996 ± 17 | $0 | $0 / $3,286 | 34.6 % | 65.4 % | 15 | 65.4 % | 0.70 | 15.6 |
|   referencia: nc 3 fijo, SL=TP=364, cobro al maximo (mismo motor y reglas) | $738 ± 15 | $0 | $0 / $2,184 | 35.9 % | 64.1 % | 8 | 64.1 % | 0.61 | 10.7 |
  nc optimo (indice -> nc) al inicio (b=0, wd=0): 8; wd=4, b=900 post: 1; wd=5 b=1500 post: 1, pedir pago: False; wd=5 b=3000: pedir False
| DP SL=TP=550: V0 de la DP = $913 (265 barridos, delta 0.020); MC del motor completo: | $940 ± 16 | $0 | $0 / $3,200 | 33.7 % | 66.3 % | 14 | 66.3 % | 0.70 | 16.6 |
|   referencia: nc 3 fijo, SL=TP=550, cobro al maximo (mismo motor y reglas) | $803 ± 18 | $0 | $0 / $2,376 | 30.2 % | 69.8 % | 8 | 69.8 % | 0.57 | 10.3 |
  nc optimo (indice -> nc) al inicio (b=0, wd=0): 5; wd=4, b=900 post: 3; wd=5 b=1500 post: 1, pedir pago: False; wd=5 b=3000: pedir False
| DP SL=TP=728: V0 de la DP = $910 (273 barridos, delta 0.020); MC del motor completo: | $956 ± 17 | $0 | $0 / $3,298 | 33.0 % | 67.0 % | 14 | 67.0 % | 0.69 | 16.5 |
|   referencia: nc 3 fijo, SL=TP=728, cobro al maximo (mismo motor y reglas) | $844 ± 20 | $0 | $0 / $2,434 | 28.6 % | 71.4 % | 8 | 71.4 % | 0.57 | 10.1 |
  nc optimo (indice -> nc) al inicio (b=0, wd=0): 4; wd=4, b=900 post: 3; wd=5 b=1500 post: 3, pedir pago: False; wd=5 b=3000: pedir False

## Fuera de muestra (la DP se entrena SOLO con los dias de entrenamiento; el motor completo evalua en otros dias/mundos)

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| DP entrenada en W2, SL=TP=364, evaluada en W1 con oro (incluye dias de entrenamiento) | $979 ± 16 | $0 | $0 / $3,222 | 34.1 % | 65.9 % | 15 | 65.9 % | 0.69 | 14.9 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +260 ± 18 | $719 ± 15 | $0 | $0 / $2,085 | 34.4 % | 65.6 % | 8 | 65.6 % | 0.58 | 10.3 |
| DP entrenada en W2, SL=TP=364, evaluada en W3 Browniano | $972 ± 16 | $0 | $0 / $3,213 | 34.0 % | 66.0 % | 15 | 66.0 % | 0.69 | 15.9 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +239 ± 18 | $732 ± 15 | $0 | $0 / $2,158 | 35.0 % | 65.0 % | 9 | 65.0 % | 0.59 | 11.1 |
| DP entrenada en H1, SL=TP=364, evaluada en H2 | $1,046 ± 16 | $0 | $0 / $3,436 | 38.0 % | 62.0 % | 13 | 62.0 % | 0.81 | 14.2 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +280 ± 19 | $766 ± 17 | $0 | $0 / $2,278 | 29.2 % | 70.8 % | 8 | 70.8 % | 0.53 | 9.2 |
| DP entrenada en H2, SL=TP=364, evaluada en H1 | $886 ± 15 | $0 | $0 / $2,994 | 33.7 % | 66.3 % | 18 | 66.3 % | 0.67 | 20.7 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +220 ± 15 | $667 ± 12 | $0 | $0 / $1,951 | 46.7 % | 53.3 % | 9 | 53.3 % | 0.73 | 13.1 |
| DP entrenada en W2, SL=TP=728, evaluada en W1 con oro (incluye dias de entrenamiento) | $935 ± 17 | $0 | $0 / $3,216 | 32.1 % | 67.8 % | 14 | 67.8 % | 0.67 | 16.1 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +112 ± 18 | $822 ± 20 | $0 | $0 / $2,219 | 27.7 % | 72.3 % | 8 | 72.3 % | 0.55 | 9.8 |
| DP entrenada en W2, SL=TP=728, evaluada en W3 Browniano | $907 ± 17 | $0 | $0 / $3,208 | 30.4 % | 69.6 % | 14 | 69.6 % | 0.64 | 15.9 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +64 ± 19 | $843 ± 22 | $0 | $0 / $2,163 | 25.8 % | 74.2 % | 9 | 74.2 % | 0.54 | 10.2 |
| DP entrenada en H1, SL=TP=728, evaluada en H2 | $1,267 ± 22 | $0 | $0 / $4,855 | 29.9 % | 70.1 % | 12 | 70.1 % | 0.82 | 14.6 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +357 ± 27 | $910 ± 26 | $0 | $0 / $1,800 | 21.7 % | 78.3 % | 8 | 78.3 % | 0.54 | 9.1 |
| DP entrenada en H2, SL=TP=728, evaluada en H1 | $784 ± 13 | $0 | $0 / $2,581 | 35.1 % | 64.9 % | 17 | 64.9 % | 0.70 | 24.2 |
|   vs nc 3 fijo (mismo mundo): diferencia pareada +78 ± 12 | $705 ± 13 | $0 | $0 / $2,086 | 44.5 % | 55.5 % | 9 | 55.5 % | 0.71 | 12.7 |

(tiempo 992s)