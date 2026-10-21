# resultados_D6: estructura de la politica optima (DP, W2, reglas base sin la regla de ganancia desde el ultimo pago)


## SL = TP = 364  (V0 = $931)

nc optimo en la fase POST (piso = $0 o ya pagado), por balance b (columnas) y dias ganadores wd (filas):

| wd \ b | $250 | $500 | $750 | $1,000 | $1,500 | $2,000 | $3,000 | $4,000 | $6,000 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 6 | 1 | 3 | 4 | 6 | 1 | 1 | 1 | 1 |
| 1 | 6 | 1 | 3 | 4 | 6 | 1 | 1 | 1 | 1 |
| 2 | 6 | 1 | 3 | 4 | 6 | 1 | 1 | 1 | 1 |
| 3 | 6 | 1 | 3 | 4 | 6 | 1 | 1 | 1 | 1 |
| 4 | 6 | 1 | 1 | 1 | 6 | 1 | 1 | 1 | 1 |
| 5 | 6 | 1 | 1* | 1 | 1 | 1 | 1 | 1 | 1* |

(* = pedir el pago maximo en ese estado). nc optimo en la fase PRE-lock (piso < 0): filas = pico de balance, columnas = balance, wd = 0:

| pico \ b | $-1,000 | $-500 | $0 | $500 | $1,000 | $1,500 |
|---|---|---|---|---|---|---|
| $0 | 2 | 1 | 8 | - | - | - |
| $500 | 1 | 2 | 1 | 8 | - | - |
| $1,000 | - | 1 | 2 | 6 | 6 | - |
| $1,500 | - | - | 1 | 2 | 6 | 6 |

Con wd = 5 en fase POST, el primer balance en el que conviene PEDIR el pago maximo: 300

## SL = TP = 728  (V0 = $910)

nc optimo en la fase POST (piso = $0 o ya pagado), por balance b (columnas) y dias ganadores wd (filas):

| wd \ b | $250 | $500 | $750 | $1,000 | $1,500 | $2,000 | $3,000 | $4,000 | $6,000 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| 1 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| 2 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| 3 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| 4 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| 5 | 1 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 1* |

(* = pedir el pago maximo en ese estado). nc optimo en la fase PRE-lock (piso < 0): filas = pico de balance, columnas = balance, wd = 0:

| pico \ b | $-1,000 | $-500 | $0 | $500 | $1,000 | $1,500 |
|---|---|---|---|---|---|---|
| $0 | 1 | 3 | 4 | - | - | - |
| $500 | 2 | 1 | 3 | 4 | - | - |
| $1,000 | - | 2 | 1 | 3 | 4 | - |
| $1,500 | - | - | 2 | 1 | 3 | 4 |

Con wd = 5 en fase POST, el primer balance en el que conviene PEDIR el pago maximo: 350