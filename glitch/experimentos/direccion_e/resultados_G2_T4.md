# resultados_G2_T4 — barreras escaladas por ATR en MGC (V3)

k = 0.802 (= 364 / mediana de la media de 20 rangos = 454 ticks). W_t en [200, 800] a pasos de 50; nc_t = clip(round(1092/W_t), 1, 6). Distribución de W: 200: 87, 250: 91, 300: 37, 350: 25, 400: 14, 450: 38, 500: 59, 550: 30, 600: 21, 650: 11, 700: 4, 750: 10, 800: 41.

## Fracción decidida (TP o SL) por bloque cronológico (4)

- Fijo 3×364: 15 % · 27 % · 79 % · 68 % (DE entre bloques = 27.2 pp)
- ATR:        43 % · 44 % · 41 % · 36 % (DE entre bloques = 3.3 pp) → cambio de la DE: **-88 %** (predicción: ≤ −30 %).

## Prueba de dinero (W2: sin la ventana de oro; stop 0.5; Combine hoy P0 mezcla {1,3}; bancos de 60000)

| | cobrado por XFA | P(≥1 pago) | vida media (días) | neto $/año/cuenta |
|---|---|---|---|---|
| fijo 3×364 | $636 | 32.2 % | 9.7 | $1,304 |
| ATR | $669 | 35.4 % | 10.4 | $1,566 |

Diferencia ATR − fijo: cobrado +33 por XFA; **neto +262 $/año/cuenta** (piso +$500; ruido de nivel ±$100).
- Bootstrap pareado de días (100 remuestras de la historia, bancos de 8,000): diferencia de cobrado media +25, IC95 [-10, +69]; **p unilateral (ATR > fijo) = 0.110** (resolución mínima 1/100).

## Equilibrio (ventaja solo en la XFA, misma deriva en ticks/día para ambas geometrías)

- fijo 3×364: 47 %: $-1,157 · 48 %: $-312 · 49 %: $509 · 50 %: $1,246 → equilibrio ≈ 48.4 %
- ATR: 47 %: $-1,326 · 48 %: $-323 · 49 %: $562 · 50 %: $1,468 → equilibrio ≈ 48.4 %

Cambio del equilibrio: -0.0 pp (rechazo si > +0.3 pp).