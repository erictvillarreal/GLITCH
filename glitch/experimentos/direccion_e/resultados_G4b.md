# resultados_G4b — escala con costos operativos por cuenta (API) y compartidos (Railway)

**Fuentes y estado.** Los montos (API $174 por cuenta y año, Railway ≈ $65, mensualidad del Combine $49) los dio Eric en el chat: **SUPUESTO / NO VERIFICADO con facturas** (escenario C pendiente). Escenario A: costos = $66 compartidos + $174 × N. Escenario B: $66 + ($174 + $587) × N (la mensualidad del Combine por cuenta, aparte del reset de $49 por intento que ya está en el modelo; **si el reset ya incluye la mensualidad, B cuenta doble**: pregunta para Eric). Para N = 1 dan $240 y $827. **Escenario C:** el ingreso total baja exactamente $1 por cada $1 de costos: con costos por cuenta c y compartidos s, ingreso(N) = ingreso_A(N) − [(c − 174)·N + (s − 66)].

Marginal de una cuenta (ops = 0) con slippage de entrada **empírico de 7 observaciones**; la sensibilidad con la mezcla {1,3} está al final de cada bloque. Dependencia entre cuentas: ρ = 1 (mismos trades), 0.5 (**supuesto ilustrativo**), 0 (independientes; el ρ de retornos MES–MGC medido es 0.17, no el de resultados). La dependencia **no se simuló día a día**.


## Escenario A — hoy (P0, 3×364): una cuenta sin costos operativos $2,913/año; con costos $240: $2,673

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $2,639 | $-2,556 | 32 % | 32 % | 40 % | $240 | $1,879 |
| 2 | 1.0 | $5,385 | $-5,037 | 32 % | 32 % | 54 % | $414 | $3,804 |
| 2 | 0.5 | $5,420 | $-3,731 | 27 % | 16 % | 57 % | $414 | $3,911 |
| 2 | 0.0 | $5,404 | $-2,240 | 21 % | 10 % | 61 % | $414 | $3,816 |
| 3 | 1.0 | $8,194 | $-7,573 | 31 % | 31 % | 59 % | $588 | $5,828 |
| 3 | 0.5 | $8,184 | $-4,889 | 25 % | 11 % | 64 % | $588 | $5,747 |
| 3 | 0.0 | $8,143 | $-1,494 | 15 % | 3 % | 73 % | $588 | $5,783 |
| 4 | 1.0 | $11,016 | $-10,056 | 31 % | 31 % | 62 % | $762 | $7,725 |
| 4 | 0.5 | $10,963 | $-6,065 | 24 % | 8 % | 68 % | $762 | $7,773 |
| 4 | 0.0 | $10,825 | $-314 | 11 % | 1 % | 80 % | $762 | $7,739 |
| 5 | 1.0 | $13,599 | $-12,533 | 31 % | 31 % | 63 % | $936 | $9,639 |
| 5 | 0.5 | $13,572 | $-6,984 | 23 % | 6 % | 70 % | $936 | $9,859 |
| 5 | 0.0 | $13,664 | $1,047 | 8 % | 0 % | 85 % | $936 | $9,699 |

## Escenario A — + finish-line (P3, 3×364): una cuenta sin costos operativos $3,387/año; con costos $240: $3,147

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $3,153 | $-2,146 | 27 % | 27 % | 45 % | $240 | $2,859 |
| 2 | 1.0 | $6,348 | $-4,335 | 27 % | 27 % | 59 % | $414 | $5,833 |
| 2 | 0.5 | $6,302 | $-3,063 | 23 % | 14 % | 62 % | $414 | $5,762 |
| 2 | 0.0 | $6,337 | $-1,503 | 16 % | 7 % | 67 % | $414 | $5,735 |
| 3 | 1.0 | $9,511 | $-6,483 | 27 % | 27 % | 64 % | $588 | $8,666 |
| 3 | 0.5 | $9,561 | $-3,750 | 21 % | 9 % | 69 % | $588 | $8,721 |
| 3 | 0.0 | $9,502 | $-329 | 11 % | 2 % | 78 % | $588 | $8,709 |
| 4 | 1.0 | $12,927 | $-8,718 | 27 % | 27 % | 66 % | $762 | $11,704 |
| 4 | 0.5 | $12,792 | $-4,447 | 20 % | 6 % | 73 % | $762 | $11,652 |
| 4 | 0.0 | $12,750 | $1,353 | 7 % | 1 % | 86 % | $762 | $11,647 |
| 5 | 1.0 | $15,875 | $-10,736 | 27 % | 27 % | 67 % | $936 | $14,837 |
| 5 | 0.5 | $16,134 | $-5,004 | 19 % | 4 % | 75 % | $936 | $14,582 |
| 5 | 0.0 | $15,986 | $3,184 | 5 % | 0 % | 90 % | $936 | $14,562 |

## Escenario A — + finish-line + 728×3: una cuenta sin costos operativos $4,945/año; con costos $240: $4,705

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $4,702 | $-2,151 | 23 % | 23 % | 55 % | $240 | $4,341 |
| 2 | 1.0 | $9,512 | $-4,066 | 23 % | 23 % | 66 % | $414 | $8,726 |
| 2 | 0.5 | $9,429 | $-2,612 | 18 % | 11 % | 70 % | $414 | $8,731 |
| 2 | 0.0 | $9,507 | $-607 | 12 % | 5 % | 76 % | $414 | $8,768 |
| 3 | 1.0 | $14,079 | $-6,321 | 23 % | 23 % | 70 % | $588 | $13,198 |
| 3 | 0.5 | $14,234 | $-2,788 | 16 % | 6 % | 76 % | $588 | $13,197 |
| 3 | 0.0 | $14,302 | $1,660 | 7 % | 1 % | 87 % | $588 | $13,188 |
| 4 | 1.0 | $19,222 | $-8,200 | 23 % | 23 % | 72 % | $762 | $17,558 |
| 4 | 0.5 | $19,052 | $-3,192 | 15 % | 4 % | 80 % | $762 | $17,750 |
| 4 | 0.0 | $19,048 | $4,407 | 4 % | 0 % | 92 % | $762 | $17,511 |
| 5 | 1.0 | $23,651 | $-10,509 | 23 % | 23 % | 73 % | $936 | $21,976 |
| 5 | 0.5 | $23,764 | $-3,377 | 14 % | 3 % | 81 % | $936 | $21,947 |
| 5 | 0.0 | $23,708 | $7,347 | 2 % | 0 % | 95 % | $936 | $22,108 |

## Escenario B — hoy (P0, 3×364): una cuenta sin costos operativos $2,913/año; con costos $827: $2,086

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $2,123 | $-3,142 | 37 % | 37 % | 36 % | $827 | $1,307 |
| 2 | 1.0 | $4,242 | $-6,235 | 37 % | 37 % | 49 % | $1,588 | $2,681 |
| 2 | 0.5 | $4,240 | $-4,985 | 33 % | 21 % | 51 % | $1,588 | $2,705 |
| 2 | 0.0 | $4,259 | $-3,469 | 28 % | 14 % | 53 % | $1,588 | $2,692 |
| 3 | 1.0 | $6,321 | $-9,391 | 37 % | 37 % | 53 % | $2,349 | $4,020 |
| 3 | 0.5 | $6,406 | $-6,509 | 31 % | 14 % | 57 % | $2,349 | $4,068 |
| 3 | 0.0 | $6,348 | $-3,240 | 22 % | 5 % | 63 % | $2,349 | $3,984 |
| 4 | 1.0 | $8,476 | $-12,500 | 37 % | 37 % | 56 % | $3,110 | $5,554 |
| 4 | 0.5 | $8,358 | $-8,543 | 31 % | 11 % | 60 % | $3,110 | $5,363 |
| 4 | 0.0 | $8,612 | $-2,617 | 18 % | 2 % | 71 % | $3,110 | $5,368 |
| 5 | 1.0 | $10,523 | $-15,452 | 37 % | 37 % | 57 % | $3,871 | $6,766 |
| 5 | 0.5 | $10,716 | $-10,053 | 30 % | 9 % | 63 % | $3,871 | $6,806 |
| 5 | 0.0 | $10,695 | $-1,815 | 14 % | 1 % | 76 % | $3,871 | $6,772 |

## Escenario B — + finish-line (P3, 3×364): una cuenta sin costos operativos $3,387/año; con costos $827: $2,560

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $2,563 | $-2,722 | 33 % | 33 % | 40 % | $827 | $2,277 |
| 2 | 1.0 | $5,121 | $-5,474 | 33 % | 33 % | 53 % | $1,588 | $4,718 |
| 2 | 0.5 | $5,196 | $-4,187 | 29 % | 18 % | 56 % | $1,588 | $4,577 |
| 2 | 0.0 | $5,156 | $-2,625 | 23 % | 10 % | 59 % | $1,588 | $4,643 |
| 3 | 1.0 | $7,778 | $-8,117 | 33 % | 33 % | 58 % | $2,349 | $6,915 |
| 3 | 0.5 | $7,800 | $-5,561 | 27 % | 12 % | 63 % | $2,349 | $6,983 |
| 3 | 0.0 | $7,888 | $-1,920 | 16 % | 3 % | 71 % | $2,349 | $7,010 |
| 4 | 1.0 | $10,324 | $-10,902 | 33 % | 33 % | 60 % | $3,110 | $9,386 |
| 4 | 0.5 | $10,483 | $-6,709 | 25 % | 8 % | 66 % | $3,110 | $9,311 |
| 4 | 0.0 | $10,463 | $-882 | 12 % | 1 % | 78 % | $3,110 | $9,312 |
| 5 | 1.0 | $13,055 | $-13,570 | 32 % | 32 % | 62 % | $3,871 | $11,732 |
| 5 | 0.5 | $13,019 | $-8,163 | 25 % | 7 % | 68 % | $3,871 | $11,697 |
| 5 | 0.0 | $13,132 | $290 | 9 % | 0 % | 83 % | $3,871 | $11,575 |

## Escenario B — + finish-line + 728×3: una cuenta sin costos operativos $4,945/año; con costos $827: $4,118

| N | ρ | ingreso anual esperado | p10 | P(total < 0) | P(todas pierden) | P(total ≥ $3k) | costos operativos totales | mezcla {1,3}: ingreso esperado |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $4,110 | $-2,700 | 27 % | 27 % | 51 % | $827 | $3,747 |
| 2 | 1.0 | $8,286 | $-5,360 | 27 % | 27 % | 62 % | $1,588 | $7,720 |
| 2 | 0.5 | $8,315 | $-3,702 | 22 % | 14 % | 66 % | $1,588 | $7,642 |
| 2 | 0.0 | $8,317 | $-1,812 | 16 % | 7 % | 71 % | $1,588 | $7,600 |
| 3 | 1.0 | $12,570 | $-7,926 | 27 % | 27 % | 66 % | $2,349 | $11,494 |
| 3 | 0.5 | $12,600 | $-4,543 | 20 % | 8 % | 72 % | $2,349 | $11,376 |
| 3 | 0.0 | $12,453 | $-168 | 10 % | 2 % | 82 % | $2,349 | $11,471 |
| 4 | 1.0 | $16,580 | $-10,736 | 27 % | 27 % | 67 % | $3,110 | $15,159 |
| 4 | 0.5 | $16,689 | $-5,463 | 19 % | 6 % | 75 % | $3,110 | $15,344 |
| 4 | 0.0 | $16,635 | $1,894 | 7 % | 1 % | 88 % | $3,110 | $15,256 |
| 5 | 1.0 | $20,639 | $-13,266 | 27 % | 27 % | 69 % | $3,871 | $19,154 |
| 5 | 0.5 | $20,937 | $-6,276 | 19 % | 4 % | 77 % | $3,871 | $19,057 |
| 5 | 0.0 | $20,848 | $4,445 | 5 % | 0 % | 92 % | $3,871 | $19,196 |

**Lectura.** (1) Con la API por cuenta el ingreso sigue siendo lineal en N pero cada cuenta cuesta $174 (A) o $761 (B) al año en lugar de absorber una cuota compartida: a N = 5 los costos operativos son $936 (A) o $3,871 (B), no $714. (2) El slippage empírico (media +1.0, con −1 y 0 en 3 de 7 casos) da una cuenta mejor que la mezcla {1,3} en +$0.76k/año (hoy, 40 fijos), +$0.29k (con finish-line) y +$0.36k (finish-line + 728×3) — comparación de la fila N = 1, costos A; ambos slippage son **N = 7 / supuesto**. (3) Todas las probabilidades de riesgo dependen de ρ, que no se estimó; mismos trades en todas las cuentas es además el patrón que Topstep cita como motivo de RTP.