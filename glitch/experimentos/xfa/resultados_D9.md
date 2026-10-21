# resultados_D9 (cadena anual; 50000 trayectorias; bancos de 200000; reglas verificadas; MGC sin la ventana de oro; slip de entrada MGC 0)

## A. WR como palanca: neto anual por cuenta (media / mediana / p10–p90 / P(<0)); stop llenado a 0.5 (convención C1)

| Combine | WR | candidato | cobrado por XFA | neto anual |
|---|---|---|---|---|
| P0 slip mezcla {1,3} (hoy) | 45 % | a plan 3×364 | $245 | $-2,612 / $-3,098 / $-5,387–$708 / 86 % |
| P3 slip mezcla {1,3} (finish-line) | 45 % | a plan 3×364 | $245 | $-2,133 / $-2,595 / $-5,043–$1,368 / 81 % |
| P0 slip 1 | 45 % | a plan 3×364 | $245 | $-2,076 / $-2,541 / $-5,133–$1,602 / 80 % |
| P0 slip mezcla {1,3} (hoy) | 45 % | b 728×3 | $244 | $-2,728 / $-3,381 / $-5,783–$1,007 / 85 % |
| P3 slip mezcla {1,3} (finish-line) | 45 % | b 728×3 | $244 | $-2,246 / $-2,763 / $-5,640–$1,731 / 80 % |
| P0 slip 1 | 45 % | b 728×3 | $244 | $-2,198 / $-2,714 / $-5,742–$1,936 / 79 % |
| P0 slip mezcla {1,3} (hoy) | 50 % | a plan 3×364 | $641 | $1,311 / $507 / $-3,567–$7,218 / 45 % |
| P3 slip mezcla {1,3} (finish-line) | 50 % | a plan 3×364 | $641 | $2,288 / $1,541 / $-2,860–$8,414 / 35 % |
| P0 slip 1 | 50 % | a plan 3×364 | $641 | $2,748 / $2,031 / $-2,627–$9,119 / 31 % |
| P0 slip mezcla {1,3} (hoy) | 50 % | b 728×3 | $809 | $2,613 / $1,523 / $-3,732–$10,433 / 38 % |
| P3 slip mezcla {1,3} (finish-line) | 50 % | b 728×3 | $809 | $3,777 / $2,787 / $-2,823–$11,765 / 29 % |
| P0 slip 1 | 50 % | b 728×3 | $809 | $4,371 / $3,440 / $-2,553–$12,614 / 26 % |
| P0 slip mezcla {1,3} (hoy) | 55 % | a plan 3×364 | $1,900 | $9,779 / $8,645 / $323–$21,573 / 9 % |
| P3 slip mezcla {1,3} (finish-line) | 55 % | a plan 3×364 | $1,900 | $11,488 / $10,600 / $1,945–$22,717 / 5 % |
| P0 slip 1 | 55 % | a plan 3×364 | $1,900 | $12,492 / $11,732 / $2,830–$23,352 / 3 % |
| P0 slip mezcla {1,3} (hoy) | 55 % | b 728×3 | $3,210 | $14,483 / $14,874 / $1,901–$24,745 / 6 % |
| P3 slip mezcla {1,3} (finish-line) | 55 % | b 728×3 | $3,210 | $16,325 / $17,314 / $4,225–$25,623 / 3 % |
| P0 slip 1 | 55 % | b 728×3 | $3,210 | $17,369 / $18,761 / $5,539–$26,306 / 2 % |

## B. Política DP (entrenada en W2, stop exacto, slip 0) evaluada con fricciones — cobrado por XFA

| bracket | mundo / fricción | DP | nc 3 fijo | diferencia pareada |
|---|---|---|---|---|
| SL=TP=364 | stop exacto, slip 0 | $996 | $738 | +258 ± 18 |
| SL=TP=364 | stop 0.5, slip 0 | $937 | $650 | +287 ± 16 |
| SL=TP=364 | stop 0.5, slip 3 ticks | $863 | $601 | +263 ± 15 |
| SL=TP=364 | stop 0.5, slip 10 ticks | $721 | $499 | +223 ± 13 |
| SL=TP=728 | stop exacto, slip 0 | $956 | $844 | +112 ± 17 |
| SL=TP=728 | stop 0.5, slip 0 | $942 | $826 | +117 ± 17 |
| SL=TP=728 | stop 0.5, slip 3 ticks | $881 | $766 | +115 ± 16 |
| SL=TP=728 | stop 0.5, slip 10 ticks | $750 | $651 | +99 ± 14 |

(tiempo 134s)