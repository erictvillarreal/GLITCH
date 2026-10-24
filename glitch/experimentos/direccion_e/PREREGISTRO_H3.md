# PREREGISTRO_H3 — volatilidad ampliada (Parte H, H3) — 24-oct-2026

**G0.** Se commitea **antes de calcular ningún resultado de H3**. Ya conocidos de G2 (no se re-prueban como hipótesis): los pronosticadores HAR de rango funcionan (R²_OOS oro 33.5 %, S&P 54.7 %), el filtro de MGC subió la fracción decidida +44 pp pero **restó $559/año** y las barreras por ATR dieron +$262/año (p = 0.11). **Máx. 8 pruebas; 7 estadísticas con Holm α = 0.05 sobre las 7** (familia propia) **y 1 prueba de dinero descriptiva.** Parámetros FIJOS, sin barridos. Enmiendas fechadas al final.

**Datos nuevos:** `^VIX` (1990 →) y `^GVZ` (2008-06 →, volatilidad implícita del oro) de Yahoo (descargados el 24-oct, CSV crudo). **No aplicables y se declaran:** rangos de las sesiones de Asia y Londres (no hay intradía nocturno limpio; E6 ya se omitió), eventos distintos de FOMC (sin calendario verificado; ver H4).

## Pruebas estadísticas (7; mismo método que T1/T2 de G2: ajuste MCO expansivo re-ajustado cada 1 de enero, mínimo 756 días, bootstrap de bloques de 20 días, 5,000 remuestras, semilla 20261024)
**P1 — VIX en índices.** ΔR²_OOS = R²(HAR3 + |brecha| + ln VIX_{t−1} + Δln VIX_{t−1}) − R²(HAR3 + |brecha|), sobre `ln(H/L)` de ^GSPC. Rechazo de H₀ (ΔR² ≤ 0) con Holm α/7.
**P2 — GVZ en oro.** ΔR²_OOS al añadir ln GVZ_{t−1} y Δln GVZ_{t−1} al HAR3 de `ln(H/L)` de GC=F (2008 →).
**P3 — día de la semana en índices.** ΔR²_OOS al añadir 4 dummies (lun–jue; viernes base) al modelo de P1 sin VIX.
**P4 — día de la semana en oro.** Igual sobre GC=F.
**P5 — hora de entrada, MES 10:30 CT.** Δ P(pasar el Combine desde cuenta nueva) = P(10:30) − P(9:35), nc 40 fijo, TP 32, liquidación a 40, slip de entrada mezcla {1,3} (SUPUESTO), 15 días; referencia = cierre de la barra de las 10:25 CT (9:30 en la base). p unilateral (H₀: Δ ≤ 0) por bootstrap de bloques de 5 días (≥ 200 remuestras de la historia, bancos de 20,000), Holm α/7.
**P6 — hora de entrada, MES 12:30 CT.** Igual (referencia = barra de las 12:25 CT). (No se prueba 11:30 ni otras horas: máximo 4 horas candidatas contando la base — 9:35, 10:30, 11:30 y 12:30 — y 11:30 se reporta **solo descriptivo**.)
**P7 — tamaño por volatilidad en la XFA de MGC (prueba de dinero con estadística).** nc_t = clip(round(3 × m / F_t), 1, 6) con F_t = pronóstico de rango del día (mismo modelo que T3 de G2, ex ante) y m = mediana de F; barreras fijas SL = TP = 364. Diferencia pareada de **cobrado medio por XFA** contra 3 micros fijos (WR 50 %, W2, stop 0.5); bootstrap de días ≥ 100 remuestras; p unilateral > 0, Holm α/7.

## Prueba 8 (descriptiva, sin Holm): los tres usos del pronóstico bajo escenarios de WR
Filtro (k = 1 sobre exp(F_t) ≥ 364), barreras por ATR y tamaño por volatilidad, **cada uno con prueba de dinero (cadena Combine → XFA) en WR_dec = 47.4 / 48.5 / 50 / 52 %** (ventaja por deriva en la XFA de MGC; Combine hoy P0, mezcla {1,3}), reportando cobrado por XFA, P(≥ 1 pago), días de calendario al primer pago y $/año/cuenta, **incluido el costo de saltar días** (duraciones reescaladas por 1/fracción operada; la mensualidad y los intentos se pagan igual). Objetivo declarado: subir la fracción decidida desde ≈ 44 % **sin subir el equilibrio**.

## Descriptivo (sin prueba): estacionalidad intradía
Rango mediano, volumen y un **proxy** de costo (estimador de spread de Corwin-Schultz con H/L de barras de 5 min; **no es spread observado**) por franja de 30 min, para MES y MGC; 40 contratos como % del volumen de la barra por franja. No hay datos de libro de órdenes: no se inventan.

## Gates y declaraciones
G1 datos (truncamiento ≤ t−1 en cada predictor; VIX/GVZ del cierre de t−1); G2 = Holm sobre 7; G3 = ≥ $500/año/cuenta con IC en la prueba de dinero; G4 = paper en sombra ≥ 30 días + kill-switch + aprobación (capital: regla 4). «Sin potencia» donde n lo exija (P5/P6/P7 con ~490 días).
## Enmiendas
(ninguna al momento de escribir)
