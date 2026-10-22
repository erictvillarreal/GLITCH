# resultados_E_desglose — reconciliación del equilibrio y desglose por etapa (plan 3×364, stop 0.5, Combine hoy P0 con mezcla de slip {1,3})

σ de la sesión: MGC 373 ticks, MES 167 ticks. Bancos de 200000, 40000 trayectorias, semillas fijas.

## 1. Neto anual vs WR según DÓNDE se aplica la ventaja

(a) solo en la XFA (convención de la Parte D, `resultados_D9.md`: el Combine queda sin deriva); (b) en las dos etapas (convención de §4 de la Parte E); (c) = (a) con slippage de entrada de MGC de 3 ticks (no medido; los demás cuadros lo suponen 0).

| WR | cobrado por XFA | (a) ventaja solo en XFA | (b) ventaja en Combine y XFA | (c) = (a) con slip MGC 3 |
|---|---|---|---|---|
| 45.0 % | $245 | $-2,611 | $-2,886 | $-2,813 |
| 46.0 % | $298 | $-2,010 | $-2,284 | $-2,255 |
| 47.0 % | $379 | $-1,153 | $-1,395 | $-1,443 |
| 47.4 % | $404 | $-902 | $-1,135 | $-1,212 |
| 48.0 % | $462 | $-322 | $-538 | $-660 |
| 49.0 % | $554 | $554 | $361 | $176 |
| 50.0 % | $641 | $1,331 | $1,331 | $894 |
| 51.0 % | $746 | $2,234 | $2,433 | $1,737 |

**Puntos de equilibrio (interpolación lineal en la malla de arriba):** por XFA (cobrado = $365, punto medio de $317–$446 de `EVIDENCIA_CEREBRO2.md` §4): **46.8 %** · anual con la ventaja solo en la XFA (a): **48.4 %** · en las dos etapas (b): **48.6 %** · (a) con slip MGC 3: **48.8 %**.

## 2. Desglose por etapa de una ventaja estandarizada z = μ/σ (misma z en MES y MGC cuando aplica)

| z | ≈ WR (tabla A) | solo Combine de MES | solo XFA de MGC | ambas | pasa el Combine (solo Combine) |
|---|---|---|---|---|---|
| 0.020 | 51 % | +180 | +975 | +1,175 | 21.6 % (base 20.5 %) |
| 0.024 | ≈51 % | +182 | +1,130 | +1,336 | 21.6 % (base 20.5 %) |
| 0.049 | 52 % | +225 | +2,207 | +2,475 | 21.9 % (base 20.5 %) |
| 0.081 | 53 % | +294 | +3,938 | +4,343 | 22.4 % (base 20.5 %) |

Base (sin ventaja): $1,331/año por cuenta. Las columnas son la diferencia contra la base.

## 3. La cuenta de ‘siempre LARGO’ en el Combine de MES, paso a paso

- μ/σ de ^GSPC apertura→cierre (1990–2026) = +0.024 (media +2.46 pb/día, σ 1.04 %). Sesión de MES: σ = 167 ticks ⇒ deriva = 0.024 × 167 = **4.0 ticks/día** a favor del lado LARGO.
- Bruto si cobrara toda la deriva: 4.0 ticks × $1.25 × 40 contratos = **$200/día de operación**.
- Con el bracket real (TP 32 / piso $2,000, slip 1, salida 3): P&L medio por día de LARGO **$-185** sin deriva → **$-136** con ella (**+50 $/día**); TP 51.8 % → 53.3 %, liquidación/SL 48.2 % → 46.7 %.
- Esa ganancia por día solo existe mientras el Combine está abierto (≈ 10–20 días por intento); el valor anual sale de que cambie P(pasar) y por tanto cuántas XFA se obtienen (tabla 2, columna «solo Combine»).