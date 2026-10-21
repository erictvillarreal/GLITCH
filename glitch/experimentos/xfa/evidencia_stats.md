# evidencia_stats (generado por evidencia_stats.py)

## 1. El día real de Cerebro 2 (bracket 364/364, 3 micros, ref 7:15 CT, flatten 14:30, comisión $1.92, sin slippage); lado = `alternate` por fecha real

| serie | días | TP | SL | FLATTEN | WR = TP/(TP+SL) [IC95] | pnl medio por trade | P(día ≥ $150 neto) | P(día ≤ −$150) |
|---|---|---|---|---|---|---|---|---|
| CONTAMINADA (como el código previo) | 498 | 23.9 % | 26.5 % | 49.6 % | 47.4 % [41.3, 53.6] | $-30.5 | 43.2 % | 44.4 % |
| limpia, todos los días | 488 | 20.9 % | 23.2 % | 55.9 % | 47.4 % [40.9, 54.1] | $-25.5 | 43.0 % | 43.2 % |
| limpia, SIN ventana de oro | 443 | 19.2 % | 22.8 % | 58.0 % | 45.7 % [38.7, 52.9] | $-41.9 | 41.8 % | 43.6 % |

Días FLATTEN (limpia, todos): pnl medio $+3, sd $422; P(FLATTEN ≥ +$150) 39.6 %, P(FLATTEN ≤ −$150) 35.9 %. De todos los días: 43.0 % son 'días ganadores' de la regla (≥ $150 neto): 49 % de ellos son TP y el resto son FLATTEN positivos.

## 2. WR por bloques cronológicos (limpia, 4 bloques; la serie contiene la ventana de oro 14-nov-2025 → 26-ene-2026)

| bloque | fechas | TP | SL | FLATTEN | WR [IC95] |
|---|---|---|---|---|---|
| 1 | 2024-09-06 → 2025-03-10 | 5.7 % | 4.1 % | 90.2 % | 58.3 % [32.0, 80.7] |
| 2 | 2025-03-11 → 2025-09-05 | 11.5 % | 15.6 % | 73.0 % | 42.4 % [27.2, 59.2] |
| 3 | 2025-09-08 → 2026-03-10 | 32.0 % | 35.2 % | 32.8 % | 47.6 % [37.1, 58.2] |
| 4 | 2026-03-11 → 2026-09-04 | 34.4 % | 37.7 % | 27.9 % | 47.7 % [37.6, 58.0] |

## 3. ¿Cuántas sesiones hacen falta para distinguir el WR? (decisiones TP/SL; solo 44 % de las sesiones terminan en TP o SL — el resto es FLATTEN)

Prueba binomial exacta de una cola al 5 %, potencia 80 %: **n de operaciones decididas** y **sesiones** (÷ 0.44) para rechazar WR = 50 % cuando el verdadero es 45 % o 55 %, y para decidir entre 45 % y 55 % con errores de 5 % en ambos sentidos.

| pregunta | trades decididos | sesiones |
|---|---|---|
| WR 50 % vs 45 % (¿es peor que 50?) | 620 | 1410 |
| WR 50 % vs 55 % (¿es mejor que 50?) | 620 | 1410 |
| decidir entre 45 % y 55 % (umbral 50 %, error 5 % en ambos) | 271 | 616 |

Con las 3 sesiones vivas (SL, FLATTEN, FLATTEN) hay **1 trade decidido**: ninguna inferencia posible sobre el WR. Ni siquiera las 488 sesiones históricas limpias (≈ 215 decididas) bastan para separar 50 % de 45 % con potencia 80 %.
