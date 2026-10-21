# resultados_A2 (N=4000; semilla 20261020)

## Manana (miercoles 21-oct, SHORT por paridad, day_index=1775). Colchon = $2,000.0
Costo por contrato de un SL completo con slip entrada 3 + slip salida 3 (supuesto): (100+3+3) ticks x $1.25 + $1.22 = **$133.72** -> nc maximo que hace IMPOSIBLE liquidar en un dia = floor(2000/133.72) = **14**, margen = **$127.92**.
Chequeo empirico (replay de 492 dias reales, SHORT, slip 3/3): mayor nc sin ninguna liquidacion = 6.

| nc hoy | P(TP) | P(SL) | P(LIQUIDA) | P(flatten) | P&L esp. dia | neto TP (slip1 / slip3) | perdida SL (tope=colchon) | P(pase) total con continuacion OPTIMA (DP) | costo de bolsillo esp. hasta pasar (DP) | idem con $8/dia de demora (DP) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 72.4% | 18.7% | 0.0% | 8.9% | -3 | +38 / +35 | -134 | 52.4% | $101 | $157 |
| 2 | 72.4% | 18.7% | 0.0% | 8.9% | -6 | +75 / +70 | -267 | 52.1% | $101 | $158 |
| 3 | 72.4% | 18.7% | 0.0% | 8.9% | -9 | +113 / +105 | -401 | 51.9% | $101 | $156 |
| 5 | 72.4% | 18.7% | 0.0% | 8.9% | -15 | +188 / +175 | -669 | 51.3% | $101 | $157 |
| 8 | 72.4% | 18.5% | 0.2% | 8.9% | -26 | +300 / +280 | -1,070 | 50.0% | $103 | $157 |
| 10 | 72.4% | 18.3% | 0.4% | 8.9% | -32 | +375 / +350 | -1,337 | 49.8% | $104 | $159 |
| 12 | 72.4% | 17.9% | 0.8% | 8.9% | -39 | +450 / +420 | -1,605 | 49.5% | $104 | $160 |
| 14 | 72.4% | 14.9% | 3.8% | 8.9% | -47 | +525 / +490 | -1,872 | 49.3% | $104 | $159 |
| 15 | 72.4% | 5.0% | 13.7% | 8.9% | -45 | +563 / +525 | -2,000 | 49.4% | $105 | $157 |
| 18 | 71.2% | 0.0% | 21.3% | 7.4% | -28 | +676 / +631 | -2,000 | 50.2% | $103 | $154 |
| 20 | 70.5% | 0.0% | 24.0% | 5.5% | -15 | +751 / +701 | -2,000 | 51.1% | $100 | $150 |
| 25 | 66.4% | 0.0% | 30.9% | 2.7% | -38 | +938 / +876 | -2,000 | 50.8% | $99 | $146 |
| 30 | 62.4% | 0.0% | 36.2% | 1.4% | -55 | +1,126 / +1,051 | -2,000 | 51.2% | $100 | $147 |
| 35 | 58.6% | 0.0% | 40.9% | 0.5% | -77 | +1,314 / +1,226 | -2,000 | 51.5% | $99 | $143 |
| 40 | 55.4% | 0.0% | 44.2% | 0.4% | -84 | +1,501 / +1,401 | -2,000 | 52.2% | $96 | $139 |

P(pase) optima DP (cualquier nc hoy) = 52.7%, nc optimo hoy = 39; costo optimo = $95 (nc optimo hoy 39); techo teorico 55.6%.
Costo esperado de bolsillo desde una cuenta NUEVA (50,000/50,000): $140 (empieza SHORT) / $141 (empieza LONG).

## A $100 de la meta (peak = bal >= 52,000 -> piso congelado en 50,000; colchon = bal - 50,000). Promedio de empezar SHORT y LONG.
| balance | politica | P(pase) [IC] | P(liquidar antes de pasar) | abierto a 60 dias | dias a pase (mediana) |
|---|---|---|---|---|---|
| 52,700 (faltan 300) | 40 fijo | 60.8% [56.6,65.0] | 39.2% | 0.0% | 1 |
| 52,700 (faltan 300) | 20 fijo | 75.4% [72.5,78.2] | 24.6% | 0.0% | 1 |
| 52,700 (faltan 300) | 10 fijo | 83.3% [81.5,84.9] | 16.7% | 0.0% | 1 |
| 52,700 (faltan 300) | 5 fijo | 78.6% [77.2,79.9] | 20.0% | 1.4% | 2 |
| 52,700 (faltan 300) | 3 fijo | 70.3% [68.2,72.3] | 13.9% | 15.8% | 3 |
| 52,700 (faltan 300) | 1 fijo | 35.6% [33.9,37.3] | 0.0% | 64.4% | 20 |
| 52,700 (faltan 300) | P3 finish-line | 86.0% [84.3,87.6] | 14.0% | 0.0% | 1 |
| 52,700 (faltan 300) | **DP optima** (nc hoy SHORT=4, LONG=0) | 88.7% | 11.3% (incl. abiertas) | - | - |
| 52,800 (faltan 200) | 40 fijo | 61.8% [57.6,66.0] | 38.2% | 0.0% | 1 |
| 52,800 (faltan 200) | 20 fijo | 75.9% [73.0,78.7] | 24.1% | 0.0% | 1 |
| 52,800 (faltan 200) | 10 fijo | 84.0% [82.2,85.6] | 16.1% | 0.0% | 1 |
| 52,800 (faltan 200) | 5 fijo | 81.2% [79.9,82.4] | 17.7% | 1.1% | 2 |
| 52,800 (faltan 200) | 3 fijo | 78.8% [77.5,80.1] | 9.9% | 11.3% | 2 |
| 52,800 (faltan 200) | 1 fijo | 50.3% [48.7,51.9] | 0.0% | 49.7% | 12 |
| 52,800 (faltan 200) | P3 finish-line | 90.6% [89.0,92.0] | 9.4% | 0.0% | 1 |
| 52,800 (faltan 200) | **DP optima** (nc hoy SHORT=5, LONG=0) | 92.2% | 7.8% (incl. abiertas) | - | - |
| 52,900 (faltan 100) | 40 fijo | 62.5% [58.6,66.4] | 37.5% | 0.0% | 1 |
| 52,900 (faltan 100) | 20 fijo | 76.5% [73.7,79.3] | 23.5% | 0.0% | 1 |
| 52,900 (faltan 100) | 10 fijo | 85.3% [83.4,87.0] | 14.7% | 0.0% | 1 |
| 52,900 (faltan 100) | 5 fijo | 89.2% [87.5,90.8] | 10.2% | 0.6% | 1 |
| 52,900 (faltan 100) | 3 fijo | 89.0% [87.3,90.6] | 5.3% | 5.7% | 1 |
| 52,900 (faltan 100) | 1 fijo | 70.3% [68.2,72.3] | 0.0% | 29.7% | 3 |
| 52,900 (faltan 100) | P3 finish-line | 94.4% [93.3,95.4] | 5.6% | 0.0% | 1 |
| 52,900 (faltan 100) | **DP optima** (nc hoy SHORT=1, LONG=0) | 95.9% | 4.1% (incl. abiertas) | - | - |
| 52,950 (faltan 50) | 40 fijo | 63.2% [59.0,67.2] | 36.8% | 0.0% | 1 |
| 52,950 (faltan 50) | 20 fijo | 76.8% [74.0,79.6] | 23.2% | 0.0% | 1 |
| 52,950 (faltan 50) | 10 fijo | 85.8% [83.9,87.6] | 14.2% | 0.0% | 1 |
| 52,950 (faltan 50) | 5 fijo | 89.9% [88.1,91.6] | 9.5% | 0.6% | 1 |
| 52,950 (faltan 50) | 3 fijo | 89.9% [88.2,91.4] | 4.8% | 5.3% | 1 |
| 52,950 (faltan 50) | 1 fijo | 80.9% [79.4,82.2] | 0.0% | 19.1% | 2 |
| 52,950 (faltan 50) | P3 finish-line | 96.6% [95.9,97.2] | 3.4% | 0.0% | 1 |
| 52,950 (faltan 50) | **DP optima** (nc hoy SHORT=1, LONG=0) | 97.7% | 2.3% (incl. abiertas) | - | - |

## Sensibilidades (P(pase) %, n=4000 por celda; estado de partida; politicas P0=40 fijo, P2=SL-safe, P3=finish-line, P4=min(P2,P3), P4b=40 hoy y luego P4)
| escenario | P0 40 fijo | P2 SL-safe | P3 finish-line | P4 min(P2,P3) | P4b 40 hoy+P4 |
|---|---|---|---|---|---|
| BASE (M2 iid, slip {1,3}, salida 3, TP 32) | 34.2 | 42.8 | 51.9 | 44.5 | 51.5 |
| M1 sigma x0.8 (sigma_dia=96) | 34.8 | 40.1 | 50.1 | 42.5 | 49.6 |
| M1 sigma x1.2 (sigma_dia=144) | 33.7 | 39.9 | 50.7 | 41.4 | 50.1 |
| deriva a favor -2 ticks/dia (M3) | 32.9 | 39.8 | 50.6 | 41.7 | 50.1 |
| deriva a favor +2 ticks/dia (M3) | 35.0 | 43.5 | 52.9 | 45.5 | 52.4 |
| deriva a favor +5 ticks/dia (M3) | 35.5 | 44.4 | 53.4 | 46.5 | 53.0 |
| slip entrada fijo 0 | 36.4 | 45.0 | 55.6 | 47.1 | 55.6 |
| slip entrada fijo 1 | 35.4 | 44.4 | 54.0 | 45.9 | 53.9 |
| slip entrada fijo 3 | 33.1 | 34.4 | 50.3 | 43.2 | 49.3 |
| slip entrada fijo 5 | 31.4 | 32.8 | 45.1 | 39.0 | 44.7 |
| slip salida SL 0 | 34.2 | 43.1 | 52.0 | 45.0 | 51.6 |
| slip salida SL 1 | 34.2 | 43.1 | 52.0 | 45.0 | 51.6 |
| slip salida SL 5 | 34.2 | 42.8 | 51.8 | 44.5 | 51.4 |
| TP efectivo 31 ticks | 35.2 | 37.7 | 52.0 | 44.1 | 51.4 |
| TP efectivo 33 ticks | 33.2 | 41.4 | 51.7 | 42.6 | 51.3 |
| orden intra-barra OHLC (en vez de adverso primero) | 34.7 | 43.0 | 52.7 | 44.9 | 52.3 |
| sin ratchet (piso = pico - 2000 siempre) | 29.1 | 34.8 | 50.5 | 41.8 | 50.1 |
| sin comision | 34.5 | 44.3 | 53.0 | 45.8 | 52.8 |
| bloques de 5 dias (vs iid) | 33.1 | 42.2 | 52.3 | 44.1 | 51.8 |