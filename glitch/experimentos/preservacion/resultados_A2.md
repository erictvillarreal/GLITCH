# resultados_A2 (N=30000; semilla 20261020)

DP lado-especifica (referencia, hoy SHORT con los datos reales): P(pase) optima = 52.7% (nc hoy 39); DP lado-neutral (principal) = 50.3% (nc hoy 0).

## Manana (miercoles 21-oct, SHORT por paridad, day_index=1775). Colchon = $2,000.0
Costo por contrato de un SL completo con slip entrada 3 + slip salida 3 (supuesto): (100+3+3) ticks x $1.25 + $1.22 = **$133.72** -> nc maximo que hace IMPOSIBLE liquidar en un dia = floor(2000/133.72) = **14**, margen = **$127.92**.
Chequeo empirico (replay de 492 dias reales, SHORT, slip 3/3): mayor nc sin ninguna liquidacion = 14.

| nc hoy | P(TP) | P(SL) | P(LIQUIDA) | P(flatten) | P&L esp. dia | neto TP (slip1 / slip3) | perdida SL (tope=colchon) | P(pase) total con continuacion OPTIMA (DP) | costo de bolsillo esp. hasta pasar (DP) | idem con $8/dia de demora (DP) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 72.4% | 18.7% | 0.0% | 8.9% | -3 | +38 / +35 | -134 | 49.9% | $72 | $150 |
| 2 | 72.4% | 18.7% | 0.0% | 8.9% | -6 | +75 / +70 | -267 | 49.6% | $73 | $153 |
| 3 | 72.4% | 18.7% | 0.0% | 8.9% | -9 | +113 / +105 | -401 | 49.4% | $73 | $151 |
| 5 | 72.4% | 18.7% | 0.0% | 8.9% | -15 | +188 / +175 | -669 | 48.7% | $73 | $151 |
| 8 | 72.4% | 18.7% | 0.0% | 8.9% | -24 | +300 / +280 | -1,070 | 47.5% | $72 | $151 |
| 10 | 72.4% | 18.7% | 0.0% | 8.9% | -30 | +375 / +350 | -1,337 | 46.8% | $72 | $152 |
| 12 | 72.4% | 18.7% | 0.0% | 8.9% | -36 | +450 / +420 | -1,605 | 46.6% | $72 | $154 |
| 14 | 72.4% | 18.7% | 0.0% | 8.9% | -41 | +525 / +490 | -1,872 | 46.5% | $74 | $155 |
| 15 | 72.4% | 9.3% | 9.3% | 8.9% | -44 | +563 / +525 | -2,000 | 46.6% | $77 | $154 |
| 18 | 71.2% | 0.0% | 21.3% | 7.4% | -28 | +676 / +631 | -2,000 | 47.5% | $76 | $151 |
| 20 | 70.5% | 0.0% | 24.0% | 5.5% | -15 | +751 / +701 | -2,000 | 47.9% | $75 | $145 |
| 25 | 66.4% | 0.0% | 30.9% | 2.7% | -38 | +938 / +876 | -2,000 | 48.3% | $77 | $143 |
| 30 | 62.4% | 0.0% | 36.2% | 1.4% | -55 | +1,126 / +1,051 | -2,000 | 48.4% | $79 | $147 |
| 35 | 58.6% | 0.0% | 40.9% | 0.5% | -77 | +1,314 / +1,226 | -2,000 | 48.9% | $80 | $143 |
| 40 | 55.4% | 0.0% | 44.2% | 0.4% | -84 | +1,501 / +1,401 | -2,000 | 49.8% | $79 | $142 |

P(pase) optima DP (cualquier nc hoy) = 50.3%, nc optimo hoy = 0; costo optimo = $71 (nc optimo hoy 11); techo teorico 55.6%.
Costo esperado de bolsillo desde una cuenta NUEVA (50,000/50,000): $103 (empieza SHORT) / $103 (empieza LONG).

## A $100 de la meta (peak = bal >= 52,000 -> piso congelado en 50,000; colchon = bal - 50,000). Promedio de empezar SHORT y LONG.
| balance | politica | P(pase) [IC] | P(liquidar antes de pasar) | abierto a 60 dias | dias a pase (mediana) |
|---|---|---|---|---|---|
| 52,700 (faltan 300) | 40 fijo | 61.0% [58.8,63.1] | 39.0% | 0.0% | 1 |
| 52,700 (faltan 300) | 20 fijo | 75.5% [74.3,76.7] | 24.5% | 0.0% | 1 |
| 52,700 (faltan 300) | 10 fijo | 83.9% [83.2,84.6] | 16.1% | 0.0% | 1 |
| 52,700 (faltan 300) | 5 fijo | 79.1% [78.3,79.9] | 19.5% | 1.4% | 2 |
| 52,700 (faltan 300) | 3 fijo | 71.2% [70.4,72.1] | 13.7% | 15.0% | 3 |
| 52,700 (faltan 300) | 1 fijo | 35.4% [34.8,36.0] | 0.0% | 64.6% | 20 |
| 52,700 (faltan 300) | P3 finish-line | 86.4% [86.0,86.8] | 13.6% | 0.0% | 1 |
| 52,700 (faltan 300) | **DP optima** (nc hoy SHORT=0, LONG=0) | 87.4% | 12.6% (incl. abiertas) | - | - |
| 52,800 (faltan 200) | 40 fijo | 62.0% [59.9,64.2] | 38.0% | 0.0% | 1 |
| 52,800 (faltan 200) | 20 fijo | 76.2% [74.9,77.4] | 23.8% | 0.0% | 1 |
| 52,800 (faltan 200) | 10 fijo | 84.7% [84.0,85.4] | 15.3% | 0.0% | 1 |
| 52,800 (faltan 200) | 5 fijo | 81.5% [80.6,82.3] | 17.3% | 1.2% | 2 |
| 52,800 (faltan 200) | 3 fijo | 79.5% [78.6,80.4] | 9.7% | 10.8% | 2 |
| 52,800 (faltan 200) | 1 fijo | 50.6% [49.9,51.4] | 0.0% | 49.4% | 13 |
| 52,800 (faltan 200) | P3 finish-line | 90.6% [90.1,91.2] | 9.4% | 0.0% | 1 |
| 52,800 (faltan 200) | **DP optima** (nc hoy SHORT=0, LONG=0) | 91.2% | 8.8% (incl. abiertas) | - | - |
| 52,900 (faltan 100) | 40 fijo | 62.9% [60.9,64.9] | 37.1% | 0.0% | 1 |
| 52,900 (faltan 100) | 20 fijo | 76.9% [75.8,78.1] | 23.1% | 0.0% | 1 |
| 52,900 (faltan 100) | 10 fijo | 86.0% [85.3,86.6] | 14.0% | 0.0% | 1 |
| 52,900 (faltan 100) | 5 fijo | 89.4% [88.9,89.9] | 9.8% | 0.7% | 1 |
| 52,900 (faltan 100) | 3 fijo | 89.3% [88.9,89.8] | 5.1% | 5.6% | 1 |
| 52,900 (faltan 100) | 1 fijo | 71.2% [70.4,72.1] | 0.0% | 28.8% | 3 |
| 52,900 (faltan 100) | P3 finish-line | 94.7% [94.4,95.0] | 5.3% | 0.0% | 1 |
| 52,900 (faltan 100) | **DP optima** (nc hoy SHORT=0, LONG=0) | 95.1% | 4.9% (incl. abiertas) | - | - |
| 52,950 (faltan 50) | 40 fijo | 63.6% [61.4,65.8] | 36.4% | 0.0% | 1 |
| 52,950 (faltan 50) | 20 fijo | 77.3% [76.1,78.4] | 22.7% | 0.0% | 1 |
| 52,950 (faltan 50) | 10 fijo | 86.4% [85.7,87.0] | 13.6% | 0.0% | 1 |
| 52,950 (faltan 50) | 5 fijo | 90.3% [89.8,90.8] | 9.0% | 0.7% | 1 |
| 52,950 (faltan 50) | 3 fijo | 90.1% [89.6,90.6] | 4.6% | 5.2% | 1 |
| 52,950 (faltan 50) | 1 fijo | 81.2% [80.4,82.1] | 0.0% | 18.8% | 2 |
| 52,950 (faltan 50) | P3 finish-line | 96.5% [96.3,96.8] | 3.5% | 0.0% | 1 |
| 52,950 (faltan 50) | **DP optima** (nc hoy SHORT=0, LONG=0) | 97.3% | 2.7% (incl. abiertas) | - | - |

## Sensibilidades (P(pase) %, n=30000 por celda; estado de partida; politicas P0=40 fijo, P2=SL-safe, P3=finish-line, P4=min(P2,P3), P4b=40 hoy y luego P4)
| escenario | P0 40 fijo | P2 SL-safe | P3 finish-line | P4 min(P2,P3) | P4b 40 hoy+P4 |
|---|---|---|---|---|---|
| BASE (M2 iid, slip {1,3}, salida 3, TP 32) | 33.8 | 41.8 | 51.5 | 44.0 | 51.2 |
| M1 sigma x0.8 (sigma_dia=96) | 34.2 | 39.1 | 50.9 | 41.5 | 50.6 |
| M1 sigma x1.2 (sigma_dia=144) | 33.2 | 40.4 | 50.3 | 42.1 | 50.0 |
| deriva a favor -2 ticks/dia (M3) | 32.8 | 39.2 | 50.3 | 41.3 | 50.0 |
| deriva a favor +2 ticks/dia (M3) | 34.6 | 42.7 | 52.4 | 45.1 | 52.2 |
| deriva a favor +5 ticks/dia (M3) | 35.0 | 43.7 | 52.9 | 46.1 | 52.7 |
| slip entrada fijo 0 | 35.8 | 44.4 | 54.9 | 46.8 | 54.9 |
| slip entrada fijo 1 | 34.8 | 43.6 | 53.3 | 45.5 | 53.3 |
| slip entrada fijo 3 | 32.8 | 33.5 | 49.6 | 42.4 | 49.1 |
| slip entrada fijo 5 | 31.0 | 32.2 | 44.3 | 38.4 | 44.0 |
| slip salida SL 0 | 33.8 | 42.3 | 51.6 | 44.6 | 51.5 |
| slip salida SL 1 | 33.8 | 42.1 | 51.5 | 44.5 | 51.4 |
| slip salida SL 5 | 33.8 | 41.5 | 51.4 | 43.6 | 51.2 |
| TP efectivo 31 ticks | 34.7 | 37.2 | 51.4 | 43.9 | 50.9 |
| TP efectivo 33 ticks | 33.1 | 40.9 | 51.5 | 42.5 | 51.2 |
| orden intra-barra OHLC (en vez de adverso primero) | 34.3 | 42.0 | 52.1 | 44.2 | 51.8 |
| sin ratchet (piso = pico - 2000 siempre) | 28.7 | 34.1 | 50.1 | 41.4 | 49.7 |
| sin comision | 34.0 | 43.5 | 52.5 | 45.4 | 52.4 |
| bloques de 5 dias (vs iid) | 33.0 | 42.0 | 51.5 | 44.0 | 51.2 |