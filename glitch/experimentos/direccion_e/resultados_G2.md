# resultados_G2 — volatilidad en lugar de dirección (pre-registro `PREREGISTRO_G2.md`, commit 5ca5252, antes de estos resultados)

Datos: GC=F 5,512 días con volumen (de 6,560); ^GSPC 9,268 días.

### T1 GC=F — oro (GC=F), log-rango H/L diario, HAR de 3 términos
- R²_OOS agrupado = **33.50 %** (4,711 días, 2007–2026); años con R² > 0: **100 %** (20/20); p unilateral (bloques de 20 d) = 0.0000.
- Coeficientes del último ajuste (const=+0.002, l1=+0.147, m5=+0.276, m20=+0.407).
- R²_OOS por año: 2007: 13 % · 2008: 39 % · 2009: 26 % · 2010: 7 % · 2011: 29 % · 2012: 12 % · 2013: 15 % · 2014: 15 % · 2015: 6 % · 2016: 4 % · 2017: 60 % · 2018: 55 % · 2019: 44 % · 2020: 35 % · 2021: 9 % · 2022: 21 % · 2023: 12 % · 2024: 12 % · 2025: 47 % · 2026: 55 %

### T2 ^GSPC — ^GSPC RTH, log-rango H/L diario, HAR + |brecha|
- R²_OOS agrupado = **54.71 %** (8,255 días, 1994–2026); años con R² > 0: **100 %** (33/33); p unilateral (bloques de 20 d) = 0.0000.
- Coeficientes del último ajuste (const=+0.001, l1=+0.174, m5=+0.486, m20=+0.228, ex=+0.258).
- R²_OOS por año: 1994: 20 % · 1995: 31 % · 1996: 8 % · 1997: 32 % · 1998: 51 % · 1999: 38 % · 2000: 43 % · 2001: 43 % · 2002: 64 % · 2003: 29 % · 2004: 45 % · 2005: 58 % · 2006: 57 % · 2007: 26 % · 2008: 72 % · 2009: 64 % · 2010: 28 % · 2011: 49 % · 2012: 31 % · 2013: 59 % · 2014: 62 % · 2015: 36 % · 2016: 58 % · 2017: 85 % · 2018: 39 % · 2019: 47 % · 2020: 69 % · 2021: 41 % · 2022: 45 % · 2023: 34 % · 2024: 43 % · 2025: 45 % · 2026: 34 %

### T5 FOMC ^GSPC — ^GSPC (RTH), días de anuncio 2021–2026
- 46 días FOMC de 1456; log-rango medio 0.0161 vs 0.0113: diferencia **+0.0048** (cociente de rangos medios ≈ ×1.43); IC95 [+0.0024, +0.0074]; p unilateral = 0.0000.

### T6 FOMC GC=F — oro (GC=F), días de anuncio 2021–2026
- 45 días FOMC de 1451; log-rango medio 0.0200 vs 0.0164: diferencia **+0.0036** (cociente de rangos medios ≈ ×1.22); IC95 [+0.0011, +0.0061]; p unilateral = 0.0017.

### T3 — V2 en MGC intradía (filtro: operar si exp(F_t) ≥ 364)
- Días de prueba (t ≥ 120): 368; **operados 260 (71 %)**, saltados 108. Correlación (ln R pronosticado, ln R real) = 0.65; R² fuera de muestra vs media fija de los primeros 120 días = 78.1 % (inflado por el cambio de régimen de volatilidad) y **vs media expansiva = 58.7 %** (la comparación justa).
- Fracción decidida (TP o SL): **operados 68.1 %** vs saltados 24.1 % vs todos 55.2 %. Diferencia = **+44.0 pp** [IC95 +32.0, +54.2]; p unilateral = 0.0000. FLATTEN: operados 31.9 % vs todos 44.8 %.
- Fracción decidida entre operados por bloque cronológico (4): 38 % · 62 % · 82 % · 66 %.

### Prueba de dinero de T3 (W2: sin la ventana de oro; 323 días base, 215 operados = 67 %; duraciones reescaladas por 1/0.67)
| | cobrado por XFA | P(≥1 pago) | mediana de días de calendario al 1.er pago | vida media (días cal.) | neto $/año/cuenta |
|---|---|---|---|---|---|
| sin filtro | $637 | 29.3 % | 7 | 8.9 | $1,424 |
| con filtro | $627 | 26.2 % | 9 | 12.8 | $865 |

Diferencia en $/año/cuenta: **-559** (piso: +$500). Ruido de nivel ±$100; pruebas pareadas por bootstrap de días no corridas aquí (la muestra de operados es pequeña: IC ancho).