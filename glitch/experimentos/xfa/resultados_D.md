# resultados_D (generado por run_partD.py; N=50000 vidas por celda; semilla 20261020)

MGC limpio: 488 dias (443 sin la ventana de oro); MGC contaminado (como el codigo previo): 498 dias. Browniano W3: sigma_dia=500 ticks, s=0.8; objetivo TP/SL/FLAT (364/364, W2) [0.21 0.21 0.58], ajuste [0.212 0.212 0.575].


## W1 MGC limpio CON oro: reglas base del RULEBOOK, slip de entrada 0

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| a  plan actual 3×364/364 | $721 ± 15 | $0 | $0 / $2,034 | 34.4 % | 65.6 % | 8 | 65.6 % | 0.57 | 10.5 |
| b  728×3 (stop = piso) | $817 ± 21 | $0 | $0 / $1,800 | 27.7 % | 72.3 % | 8 | 72.3 % | 0.54 | 10.5 |
| c  1 micro 5 días y luego plan | $670 ± 14 | $0 | $0 / $1,726 | 42.6 % | 57.4 % | 10 | 57.4 % | 0.64 | 13.4 |
| e1 TP 60 / SL 364 (3 micros) | $328 ± 4 | $164 | $0 / $948 | 67.6 % | 32.4 % | 6 | 32.4 % | 0.93 | 10.7 |
| e2 TP 70 / SL 250 (3 micros) | $340 ± 5 | $136 | $0 / $860 | 71.0 % | 29.0 % | 6 | 29.0 % | 0.98 | 11.6 |
| f  payout-first (1 micro con ≥4 días ganadores) | $698 ± 14 | $0 | $0 / $2,040 | 40.1 % | 59.9 % | 9 | 59.9 % | 0.63 | 11.8 |
| H4b cobro mínimo ($125) | $157 ± 4 | $0 | $0 / $338 | 34.4 % | 65.6 % | 8 | 65.6 % | 1.39 | 38.9 |

## W2 MGC limpio SIN oro: reglas base del RULEBOOK, slip de entrada 0

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| a  plan actual 3×364/364 | $736 ± 15 | $0 | $0 / $2,159 | 35.9 % | 64.1 % | 8 | 64.1 % | 0.59 | 10.8 |
| b  728×3 (stop = piso) | $838 ± 21 | $0 | $0 / $2,204 | 28.6 % | 71.4 % | 8 | 71.4 % | 0.55 | 10.8 |
| c  1 micro 5 días y luego plan | $680 ± 13 | $0 | $0 / $1,798 | 43.9 % | 56.1 % | 10 | 56.1 % | 0.66 | 13.7 |
| e1 TP 60 / SL 364 (3 micros) | $328 ± 5 | $164 | $0 / $920 | 67.7 % | 32.3 % | 6 | 32.3 % | 0.94 | 10.9 |
| e2 TP 70 / SL 250 (3 micros) | $349 ± 5 | $146 | $0 / $910 | 71.8 % | 28.2 % | 6 | 28.2 % | 1.00 | 11.8 |
| f  payout-first (1 micro con ≥4 días ganadores) | $715 ± 14 | $0 | $0 / $2,131 | 41.5 % | 58.5 % | 9 | 58.5 % | 0.66 | 12.3 |
| H4b cobro mínimo ($125) | $165 ± 4 | $0 | $0 / $338 | 35.9 % | 64.1 % | 8 | 64.1 % | 1.47 | 41.3 |

## W3 Browniano sin deriva: reglas base del RULEBOOK, slip de entrada 0

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| a  plan actual 3×364/364 | $729 ± 15 | $0 | $0 / $2,127 | 35.0 % | 65.0 % | 9 | 65.0 % | 0.58 | 11.3 |
| b  728×3 (stop = piso) | $837 ± 23 | $0 | $0 / $1,800 | 25.8 % | 74.2 % | 9 | 74.2 % | 0.53 | 11.2 |
| c  1 micro 5 días y luego plan | $683 ± 14 | $0 | $0 / $1,795 | 42.5 % | 57.5 % | 11 | 57.5 % | 0.64 | 14.2 |
| e1 TP 60 / SL 364 (3 micros) | $304 ± 4 | $160 | $0 / $832 | 64.9 % | 35.1 % | 6 | 35.1 % | 0.88 | 11.4 |
| e2 TP 70 / SL 250 (3 micros) | $297 ± 4 | $136 | $0 / $762 | 65.9 % | 34.1 % | 6 | 34.1 % | 0.89 | 12.5 |
| f  payout-first (1 micro con ≥4 días ganadores) | $716 ± 14 | $0 | $0 / $2,137 | 40.8 % | 59.2 % | 10 | 59.2 % | 0.65 | 12.9 |
| H4b cobro mínimo ($125) | $161 ± 4 | $0 | $0 / $338 | 35.0 % | 65.0 % | 9 | 65.0 % | 1.43 | 41.6 |

## W0 MGC CONTAMINADO (codigo previo): reglas base del RULEBOOK, slip de entrada 0

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| a  plan actual 3×364/364 | $707 ± 15 | $0 | $0 / $1,840 | 32.0 % | 68.0 % | 8 | 68.0 % | 0.54 | 9.9 |
| b  728×3 (stop = piso) | $789 ± 21 | $0 | $0 / $1,800 | 25.7 % | 74.3 % | 8 | 74.3 % | 0.50 | 10.1 |
| c  1 micro 5 días y luego plan | $673 ± 14 | $0 | $0 / $1,730 | 41.3 % | 58.7 % | 10 | 58.7 % | 0.62 | 12.9 |
| e1 TP 60 / SL 364 (3 micros) | $311 ± 4 | $155 | $0 / $847 | 65.6 % | 34.4 % | 6 | 34.4 % | 0.88 | 10.1 |
| e2 TP 70 / SL 250 (3 micros) | $291 ± 4 | $119 | $0 / $721 | 66.8 % | 33.2 % | 6 | 33.2 % | 0.88 | 10.9 |
| f  payout-first (1 micro con ≥4 días ganadores) | $696 ± 14 | $0 | $0 / $2,019 | 37.7 % | 62.3 % | 9 | 62.3 % | 0.60 | 11.1 |
| H4b cobro mínimo ($125) | $151 ± 4 | $0 | $0 / $338 | 32.0 % | 68.0 % | 8 | 68.0 % | 1.34 | 37.6 |

## W4 pesimista (MGC limpio SIN oro con deriva calibrada a WR): reglas base, slip 0

| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |
|---|---|---|---|---|---|---|---|---|---|
| a plan actual, WR 50 % (deriva +0.0 ticks/dia) | $736 ± 15 | $0 | $0 / $2,159 | 35.9 % | 64.1 % | 8 | 64.1 % | 0.59 | 10.8 |
| a plan actual, WR 45 % (deriva -57.3 ticks/dia) | $270 ± 7 | $0 | $0 / $1,067 | 19.8 % | 80.2 % | 9 | 80.2 % | 0.25 | 7.6 |

## Diferencia pareada de lo cobrado respecto al plan actual (a): media ± IC95, por mundo

| candidato | W1 MGC limpio CON oro | W2 MGC limpio SIN oro | W3 Browniano sin deriva | W0 MGC CONTAMINADO (codigo previo) |
|---|---|---|---|---|
| b  728×3 (stop = piso) | +97 ± 19 | +102 ± 19 | +107 ± 21 | +82 ± 20 |
| c  1 micro 5 días y luego plan | -51 ± 13 | -56 ± 13 | -47 ± 13 | -34 ± 13 |
| e1 TP 60 / SL 364 (3 micros) | -392 ± 15 | -408 ± 15 | -425 ± 15 | -396 ± 15 |
| e2 TP 70 / SL 250 (3 micros) | -381 ± 15 | -387 ± 15 | -433 ± 15 | -416 ± 15 |
| f  payout-first (1 micro con ≥4 días ganadores) | -22 ± 9 | -21 ± 9 | -13 ± 9 | -11 ± 9 |
| H4b cobro mínimo ($125) | -564 ± 13 | -571 ± 13 | -568 ± 13 | -556 ± 13 |

(tiempo 340s)