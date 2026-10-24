# resultados_H3 — volatilidad ampliada (pre-registro `PREREGISTRO_H3.md`, commit 6e2cd85, antes de estos resultados)


### P1 VIX ^GSPC — VIX (nivel y cambio de t−1) sobre HAR3 + |brecha|, ^GSPC
- R²_OOS sin = 54.67 %, con = 56.42 % ⇒ **ΔR² = +1.74 pp** (8,255 días, 1994–2026); años con mejora: 29/33; p unilateral = 0.0024.

### P2 GVZ GC=F — GVZ (nivel y cambio de t−1) sobre HAR3, GC=F
- R²_OOS sin = 34.56 %, con = 34.88 % ⇒ **ΔR² = +0.31 pp** (3,606 días, 2012–2026); años con mejora: 9/15; p unilateral = 0.2500.

### P3 DOW ^GSPC — día de la semana sobre HAR3 + |brecha|, ^GSPC
- R²_OOS sin = 54.67 %, con = 54.69 % ⇒ **ΔR² = +0.02 pp** (8,255 días, 1994–2026); años con mejora: 19/33; p unilateral = 0.3434.

### P4 DOW GC=F — día de la semana sobre HAR3, GC=F
- R²_OOS sin = 33.56 %, con = 33.63 % ⇒ **ΔR² = +0.07 pp** (4,711 días, 2007–2026); años con mejora: 13/20; p unilateral = 0.3874.

### P5/P6 — hora de entrada en MES (P(pasar) desde cuenta nueva, P0, nc 40, TP 32/liq 40, slip mezcla {1,3}, 15 días)
- 492 días comunes a las 4 horas. P(pasar) [IC95 bootstrap]: 9:35 (base): 20.5 % [19.2, 21.9] (días 1.75) · 10:30: 21.9 % [20.5, 23.2] (días 1.79) · 11:30: 21.5 % [20.5, 23.1] (días 1.85) · 12:30: 20.4 % [19.3, 21.7] (días 1.98)
- **P5 hora 10:30**: Δ P(pasar) = +1.4 pp, IC95 [-0.3, +3.3]; p unilateral (Δ > 0) = 0.065
- **P6 hora 12:30**: Δ P(pasar) = -0.1 pp, IC95 [-1.6, +1.9]; p unilateral (Δ > 0) = 0.535
- 11:30 (solo descriptivo): Δ = +1.0 pp [-0.7, +3.0]

## Dinero: P7 y prueba 8

Base de comparación: 323 días (t ≥ 120 y sin la ventana de oro). Filtro: opera 215 (67 %). ATR: k = 0.802. Tamaño: m = mediana del rango pronosticado = 528 ticks; nc_t ∈ [1, 6], distribución 1: 16, 2: 80, 3: 79, 4: 46, 5: 69, 6: 33.

## Prueba 8. Tres usos del pronóstico bajo escenarios de WR_dec (ventaja por deriva en la XFA; Combine hoy P0 mezcla {1,3}; stop 0.5)

| WR_dec | uso | cobrado por XFA | P(≥1 pago) | mediana de días de calendario al 1.er pago | neto $/año/cuenta | Δ neto vs base |
|---|---|---|---|---|---|---|
| 47.4 % | base | $442 | 23.8 % | 7 | $-491 |  |
| 47.4 % | filtro | $479 | 22.5 % | 9 | $-320 | +172 |
| 47.4 % | ATR | $431 | 27.9 % | 7 | $-621 | -130 |
| 47.4 % | tamaño | $432 | 22.1 % | 7 | $-607 | -116 |
| 48.5 % | base | $528 | 26.6 % | 7 | $385 |  |
| 48.5 % | filtro | $547 | 24.6 % | 9 | $247 | -138 |
| 48.5 % | ATR | $531 | 31.1 % | 7 | $336 | -49 |
| 48.5 % | tamaño | $531 | 24.7 % | 7 | $391 | +6 |
| 50.0 % | base | $634 | 29.1 % | 7 | $1,386 |  |
| 50.0 % | filtro | $622 | 26.2 % | 9 | $828 | -558 |
| 50.0 % | ATR | $671 | 34.9 % | 7 | $1,569 | +182 |
| 50.0 % | tamaño | $673 | 27.5 % | 7 | $1,714 | +328 |
| 52.0 % | base | $842 | 33.3 % | 7 | $3,188 |  |
| 52.0 % | filtro | $760 | 28.8 % | 9 | $1,812 | -1,377 |
| 52.0 % | ATR | $911 | 39.7 % | 7 | $3,457 | +268 |
| 52.0 % | tamaño | $952 | 32.0 % | 7 | $3,978 | +790 |

Ruido de nivel ±$100; las diferencias entre usos del pronóstico en un mismo WR comparten números aleatorios. Piso: +$500/año/cuenta.

### P7 — tamaño por volatilidad en la XFA (WR 50 %): diferencia de cobrado por XFA (tamaño − fijo) media +38, IC95 [-8, +85]; p unilateral (> 0) = 0.070 (100 remuestras, bancos de 8,000).

## Holm sobre las 7 pruebas estadísticas (α = 0.05)

| prueba | p sin ajustar | p Holm (m = 7) | ¿rechaza H₀? |
|---|---|---|---|
| P1 VIX ^GSPC | 0.0024 | 0.017 | **sí** |
| P5 hora 10:30 | 0.0650 | 0.390 | no |
| P7 tamaño | 0.0700 | 0.390 | no |
| P2 GVZ GC=F | 0.2500 | 1.000 | no |
| P3 DOW ^GSPC | 0.3434 | 1.000 | no |
| P4 DOW GC=F | 0.3874 | 1.000 | no |
| P6 hora 12:30 | 0.5350 | 1.000 | no |

**Lectura.** Solo **P1 (VIX mejora el pronóstico del rango de índices, ΔR² = +1.7 pp)** sobrevive a Holm. GVZ no mejora el del oro (+0.3 pp, p = 0.25), el día de la semana no aporta (≈ 0), la hora de entrada no cambia P(pasar) de forma distinguible (10:30: +1.4 pp, IC [−0.3, +3.3]; 12:30: −0.1 pp) y el tamaño por volatilidad en la XFA (p = 0.07) no es significativo. En la prueba de dinero (WR 47.4 / 48.5 / 50 / 52 %): **filtro** −$558 a WR 50 y −$1,377 a 52 % (solo +$172 a 47.4 %, dentro del ruido); **ATR** −$130 / −$49 / +$182 / +$268; **tamaño** −$116 / +$6 / +$328 / +$790. **Ningún uso del pronóstico supera +$500/año/cuenta en el escenario central (WR 50 %); el tamaño por volatilidad solo lo supera si existiera un WR ≥ 52 %** (donde cualquier palanca se amplifica porque la ventaja ya existe). Objetivo declarado (subir la fracción decidida sin subir el equilibrio): el filtro la sube +44 pp pero **sube el costo por saltar días y baja P(≥1 pago)**; ATR/tamaño la mantienen ≈ constante.

**Estacionalidad intradía (descriptiva):** ver `resultados_H2.md` §2 (patrón en U de rango y volumen; proxy de costo; 40 contratos = 0.2–0.7 % de la barra en MES).