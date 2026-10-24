# resultados_F2 — MGC con datos limpios vs mezclados (3 micros, SL = TP = 364 ticks, entrada 7:15 CT, flatten 14:30 CT, comisión $1.92/micro, slip 0)

## Definiciones de WR (una línea cada una; el reporte usa **WR_dec** salvo que diga otra cosa)

- **WR_dec = TP / (TP + SL)** entre los días que tocan TP o SL; FLATTEN (cierre a las 14:30 CT sin tocar barrera) queda **fuera** del denominador. Es la WR del modelo de valor (la deriva se calibra para fijarla).
- **WR_todos = TP / n** (FLATTEN cuenta como no-ganador). **WR_signo = P(cierre del flatten > referencia en el lado jugado)** (exactitud de dirección, E1–E5). **WR_pnl = días con P&L neto > 0 / días con P&L ≠ 0** (FLATTEN cuenta por su signo; es lo que mira el ‘día ganador ≥ $150’ del pago).


## limpio (contrato dominante): 488 días

| regla | TP % | SL % | FLATTEN % | WR_dec [IC95] | WR_todos | WR_signo | WR_pnl | P&L neto medio/día [IC95] |
|---|---|---|---|---|---|---|---|---|
| alternate | 20.9 | 23.2 | 55.9 | **47.4 %** [41.0, 54.1] (215 dec.) | 20.9 % | 50.0 % | 49.2 % | $-25.5 [-92.1, +43.6] |
| siempre LARGO | 20.3 | 23.8 | 55.9 | **46.0 %** [39.6, 52.6] (215 dec.) | 20.3 % | 52.5 % | 50.8 % | $-7.0 [-72.6, +60.5] |
| siempre CORTO | 23.8 | 20.3 | 55.9 | **54.0 %** [47.4, 60.4] (215 dec.) | 23.8 % | 47.5 % | 48.8 % | $-4.5 [-72.0, +61.1] |

Sin la ventana de oro (14-nov-2025 → 26-ene-2026), `alternate`: 443 días; TP 19.2 %, SL 22.8 %, FLATTEN 58.0 %; WR_dec = 45.7 %.

## mezclado (cargador anterior): 498 días

| regla | TP % | SL % | FLATTEN % | WR_dec [IC95] | WR_todos | WR_signo | WR_pnl | P&L neto medio/día [IC95] |
|---|---|---|---|---|---|---|---|---|
| alternate | 23.9 | 26.5 | 49.6 | **47.4 %** [41.4, 53.5] (251 dec.) | 23.9 % | 49.4 % | 49.0 % | $-30.5 [-101.1, +41.2] |
| siempre LARGO | 21.7 | 28.7 | 49.6 | **43.0 %** [36.8, 49.2] (251 dec.) | 21.7 % | 53.0 % | 51.0 % | $-27.9 [-99.9, +45.0] |
| siempre CORTO | 28.7 | 21.7 | 49.6 | **57.0 %** [50.8, 63.2] (251 dec.) | 28.7 % | 47.0 % | 48.6 % | $+16.4 [-56.5, +88.3] |

## Cómo se trata FLATTEN
En el modelo del XFA, un FLATTEN es un día cerrado a precio de mercado con P&L continuo (media ≈ $0, desvío ≈ $420): entra al P&L, al contador de días ≥ $150 y al MLL, pero **no** a WR_dec. 56 % de los días son FLATTEN con la geometría de hoy, por lo que WR_dec descansa en solo ≈ 215 días decididos (IC95 ±6.6 pp); WR_signo (n ≈ 480) es la medida con más potencia (±4.5 pp) y WR_pnl es la que ve el pago.