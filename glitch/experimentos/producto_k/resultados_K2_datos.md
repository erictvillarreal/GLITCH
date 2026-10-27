# resultados_K2_datos — universo de productos con los datos locales (2 años, 5 min, 9:35 → 14:25 CT)

**Fuente y estado.** MODELADO sobre las barras locales (MEDIDO en el sentido de que son precios reales; el resultado del trade es simulado). Comisiones: página de Topstep del 26-oct-2026 (`help.topstep.com/…/8284213`, extracción automática); ticks y valores: `strategies/geometry_pure.py::SPECS` salvo MNQ y MBT (especificación de CME, no re-verificada). **MYM no tiene datos locales.** Los días son los que tienen cobertura completa de la ventana.

## A. Tamaño del movimiento y fricción (1 contrato)

| producto | días | rango de la sesión, mediana (ticks) | mediana ($/contrato) | p10 – p90 ($) | comisión RT | comisión / rango mediano | SL = TP común (½ mediana, ticks) | SL en $ por contrato |
|---|---|---|---|---|---|---|---|---|
| MES | 496 | 167 | $209 | $112 – $433 | $1.22 | 0.58 % | 84 | $105 |
| MNQ | 487 | 832 | $416 | $226 – $837 | $1.22 | 0.29 % | 416 | $208 |
| M2K | 496 | 242 | $121 | $70 – $234 | $1.22 | 1.01 % | 121 | $60 |
| MGC | 490 | 275 | $275 | $115 – $660 | $1.92 | 0.70 % | 138 | $138 |
| MCL | 476 | 108 | $108 | $61 – $275 | $1.72 | 1.60 % | 54 | $54 |
| M6E | 508 | 31 | $39 | $23 – $75 | $1.00 | 2.58 % | 16 | $20 |
| ZN | 483 | 15 | $234 | $141 – $450 | $2.62 | 1.12 % | 8 | $125 |
| ZC | 454 | 17 | $212 | $125 – $350 | $5.28 | 2.48 % | 8 | $100 |
| MBT | 213 | 235 | $118 | $55 – $248 | — | — | 118 | $59 |

## B. Trade de deriva cero: resultado diario por producto (SL = TP = ½ rango mediano; 1 contrato; mismo lado en todos los productos cada fecha)

| producto | n | P&L neto medio/día | desvío ($) | TP % | SL % | FLATTEN % | WR_dec |
|---|---|---|---|---|---|---|---|
| MES | 496 | $-1.7 | $99 | 41 | 38 | 22 | 51.7 % |
| MNQ | 487 | $-4.5 | $196 | 40 | 38 | 22 | 51.2 % |
| M2K | 496 | $-1.2 | $57 | 42 | 39 | 20 | 51.8 % |
| MGC | 490 | $-13.3 | $128 | 32 | 36 | 32 | 47.3 % |
| MCL | 476 | $-5.4 | $53 | 38 | 38 | 24 | 50.0 % |
| M6E | 508 | $-0.5 | $19 | 41 | 36 | 23 | 53.4 % |
| ZN | 483 | $-5.7 | $118 | 40 | 40 | 19 | 50.1 % |
| ZC | 454 | $-15.4 | $101 | 39 | 45 | 16 | 46.5 % |

## C. Correlación de los RESULTADOS DIARIOS de ese trade (Pearson, fechas comunes)

403 fechas comunes.

| | MES | MNQ | M2K | MGC | MCL | M6E | ZN | ZC |
|---|---|---|---|---|---|---|---|---|
| **MES** | 1.00 | 0.85 | 0.66 | 0.19 | -0.03 | 0.07 | 0.03 | -0.10 |
| **MNQ** | 0.85 | 1.00 | 0.58 | 0.18 | 0.01 | 0.00 | -0.01 | -0.07 |
| **M2K** | 0.66 | 0.58 | 1.00 | 0.17 | -0.01 | 0.10 | 0.01 | -0.13 |
| **MGC** | 0.19 | 0.18 | 0.17 | 1.00 | -0.04 | 0.18 | 0.19 | -0.03 |
| **MCL** | -0.03 | 0.01 | -0.01 | -0.04 | 1.00 | -0.10 | -0.15 | 0.12 |
| **M6E** | 0.07 | 0.00 | 0.10 | 0.18 | -0.10 | 1.00 | 0.14 | -0.02 |
| **ZN** | 0.03 | -0.01 | 0.01 | 0.19 | -0.15 | 0.14 | 1.00 | -0.12 |
| **ZC** | -0.10 | -0.07 | -0.13 | -0.03 | 0.12 | -0.02 | -0.12 | 1.00 |

Para comparar, correlación del **rendimiento de la ventana** (cierre 14:25 / referencia 9:35) entre productos:

| | MES | MNQ | M2K | MGC | MCL | M6E | ZN | ZC | MBT |
|---|---|---|---|---|---|---|---|---|---|
| **MES** | 1.00 | 0.94 | 0.80 | 0.39 | -0.25 | 0.39 | 0.25 | -0.04 | 0.41 |
| **MNQ** | 0.94 | 1.00 | 0.74 | 0.40 | -0.22 | 0.37 | 0.20 | -0.01 | 0.40 |
| **M2K** | 0.80 | 0.74 | 1.00 | 0.40 | -0.30 | 0.43 | 0.34 | -0.11 | 0.41 |
| **MGC** | 0.39 | 0.40 | 0.40 | 1.00 | -0.29 | 0.58 | 0.42 | -0.26 | 0.16 |
| **MCL** | -0.25 | -0.22 | -0.30 | -0.29 | 1.00 | -0.28 | -0.46 | 0.25 | -0.09 |
| **M6E** | 0.39 | 0.37 | 0.43 | 0.58 | -0.28 | 1.00 | 0.51 | -0.24 | 0.25 |
| **ZN** | 0.25 | 0.20 | 0.34 | 0.42 | -0.46 | 0.51 | 1.00 | -0.25 | 0.18 |
| **ZC** | -0.04 | -0.01 | -0.11 | -0.26 | 0.25 | -0.24 | -0.25 | 1.00 | 0.00 |
| **MBT** | 0.41 | 0.40 | 0.41 | 0.16 | -0.09 | 0.25 | 0.18 | 0.00 | 1.00 |

**Correlación media entre resultados diarios de los 8 productos: 0.09** ⇒ k_eff = k / (1 + (k − 1)·ρ̄) = 4.8 trades independientes de 8.
Pares con resultado diario **correlacionado ≥ 0.5** (el mismo trade): MES–MNQ (0.85), MES–M2K (0.66), MNQ–M2K (0.58).
Pares con correlación **< 0.2** (candidatos a trades distintos): MES–MGC (0.19), MES–MCL (-0.03), MES–M6E (0.07), MES–ZN (0.03), MES–ZC (-0.10), MNQ–MGC (0.18), MNQ–MCL (0.01), MNQ–M6E (0.00), MNQ–ZN (-0.01), MNQ–ZC (-0.07), M2K–MGC (0.17), M2K–MCL (-0.01), M2K–M6E (0.10), M2K–ZN (0.01), M2K–ZC (-0.13), MGC–MCL (-0.04), MGC–M6E (0.18), MGC–ZN (0.19), MGC–ZC (-0.03), MCL–M6E (-0.10), MCL–ZN (-0.15), MCL–ZC (0.12), M6E–ZN (0.14), M6E–ZC (-0.02), ZN–ZC (-0.12).

*Limitación:* con SL = TP simétrico y deriva cero el resultado depende sobre todo del signo del movimiento del día; como el lado es el mismo en todos los productos, productos con rendimientos correlacionados darán resultados correlacionados. La correlación de resultados medida en 2 años tiene un error estándar ≈ 0.045 (n ≈ 500).
