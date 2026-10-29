# resultados_OPT_COMBINE_TECHO — ¿cuánto se puede subir P(pasar) con mejor tamaño? (cuenta nueva, Combine 50K, MES)

MODELADO (492 días reales de MES, resultados diarios iid, horizonte 60 días hábiles, rejilla $25). **Techo DP** = máximo P(pasar) alcanzable por CUALQUIER política de tamaño (0–40 contratos por día, adaptativa a saldo y pico). P0 = 40 fijos; P3 = finish-line. Comisión y slippage incluidos; $49 por intento.

| supuesto | TP (ticks) | P0 (40 fijos) | P3 (finish-line) | **techo DP** | techo − P3 | techo − P0 | compras esperadas por pase: P0 / P3 / techo |
|---|---|---|---|---|---|---|---|
| slippage empírico (8 obs.) | 20 | 19.2 % | 23.1 % | **24.4 %** | +1.3 pp | +5.2 pp | 5.21 / 4.33 / 4.09 |
| slippage empírico (8 obs.) | 32 | 25.5 % | 28.8 % | **29.8 %** | +0.9 pp | +4.3 pp | 3.93 / 3.47 / 3.36 |
| slippage empírico (8 obs.) | 48 | 22.1 % | 22.2 % | **31.3 %** | +9.2 pp | +9.2 pp | 4.52 / 4.51 / 3.19 |
| slippage empírico (8 obs.) | 64 | 17.9 % | 18.2 % | **31.1 %** | +12.9 pp | +13.1 pp | 5.57 / 5.49 / 3.22 |
| slippage 0 | 20 | 20.2 % | 25.3 % | **26.8 %** | +1.5 pp | +6.6 pp | 4.95 / 3.95 / 3.74 |
| slippage 0 | 32 | 30.1 % | 30.1 % | **31.4 %** | +1.3 pp | +1.3 pp | 3.33 / 3.33 / 3.19 |
| slippage 0 | 48 | 22.8 % | 22.8 % | **32.6 %** | +9.8 pp | +9.8 pp | 4.39 / 4.38 / 3.07 |
| slippage 0 | 64 | 18.6 % | 18.9 % | **32.1 %** | +13.2 pp | +13.5 pp | 5.38 / 5.30 / 3.11 |

**Cota teórica de referencia (sin ventaja):** con piso que sube en tiempo real el máximo es e^(−1)·(2/3) ≈ 24.5 %; con piso que sube con el saldo de **cierre** (el de Topstep) y una sola decisión de tamaño por día se puede superar esa cota; la tabla dice cuánto.
