# resultados_G4 — escala: N cuentas (ingreso anual, riesgo de un año malo, costos)

Marginal de UNA cuenta = cadena Combine → XFA → Combine de las Partes A y D (reglas verificadas, sin RTP, sin ventaja direccional, stop 0.5, Combine con mezcla de slip {1,3}), 40000 trayectorias. **La dependencia entre cuentas NO se simuló día a día**: se impone con una cópula gaussiana de correlación ρ sobre el neto anual (**ρ es un supuesto**, no se estimó). Casos: (a) mismo producto y mismos trades ⇒ ρ = 1 (si todas empiezan el mismo día los intentos son idénticos); (b) dos productos distintos ⇒ ρ = 0 (**supuesto**: no hay marginal de un segundo producto; se reutiliza la de MES/MGC); (c) inicios escalonados con el mismo producto ⇒ ρ = 0.5 (**supuesto ilustrativo**: cada día de mercado es común a todas las cuentas, el escalonamiento solo desfasa en qué etapa está cada una).


## hoy (P0, 3×364) — una cuenta: media $1,417/año, P(neto < 0) 44 %, P(sin ningún pago) 1 %

| N | caso | ingreso anual esperado | p10 | P(total < 0) | P(sin ningún pago en ninguna cuenta) | P(todas pierden) | P(total ≥ $3k) | costos medios (mensualidades+activaciones+resets) |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $1,384 | $-3,535 | 44 % | 1 % | 44 % | 30 % | $4,101 |
| 2 | (a) ρ = 1 | $3,523 | $-6,316 | 40 % | 1 % | 44 % | 45 % | $8,197 |
| 2 | (c) ρ = 0.5 | $3,555 | $-5,211 | 36 % | 0 % | 27 % | 47 % | $8,193 |
| 2 | (b) ρ = 0 | $3,573 | $-3,763 | 31 % | 0 % | 19 % | 49 % | $8,191 |
| 3 | (a) ρ = 1 | $5,709 | $-9,187 | 39 % | 1 % | 44 % | 51 % | $12,290 |
| 3 | (c) ρ = 0.5 | $5,697 | $-6,661 | 34 % | 0 % | 20 % | 54 % | $12,289 |
| 3 | (b) ρ = 0 | $5,661 | $-3,494 | 24 % | 0 % | 8 % | 60 % | $12,287 |
| 4 | (a) ρ = 1 | $7,672 | $-12,038 | 38 % | 1 % | 44 % | 54 % | $16,409 |
| 4 | (c) ρ = 0.5 | $7,889 | $-8,284 | 32 % | 0 % | 15 % | 59 % | $16,383 |
| 4 | (b) ρ = 0 | $7,783 | $-2,936 | 19 % | 0 % | 4 % | 68 % | $16,387 |
| 5 | (a) ρ = 1 | $9,959 | $-14,914 | 38 % | 1 % | 44 % | 56 % | $20,479 |
| 5 | (c) ρ = 0.5 | $10,047 | $-9,906 | 31 % | 0 % | 13 % | 61 % | $20,473 |
| 5 | (b) ρ = 0 | $9,913 | $-2,155 | 16 % | 0 % | 2 % | 75 % | $20,486 |

## + finish-line (P3, 3×364) — una cuenta: media $2,396/año, P(neto < 0) 34 %, P(sin ningún pago) 0 %

| N | caso | ingreso anual esperado | p10 | P(total < 0) | P(sin ningún pago en ninguna cuenta) | P(todas pierden) | P(total ≥ $3k) | costos medios (mensualidades+activaciones+resets) |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $2,422 | $-2,811 | 34 % | 0 % | 34 % | 39 % | $3,981 |
| 2 | (a) ρ = 1 | $5,472 | $-4,944 | 31 % | 0 % | 34 % | 55 % | $7,972 |
| 2 | (c) ρ = 0.5 | $5,509 | $-3,697 | 27 % | 0 % | 19 % | 58 % | $7,966 |
| 2 | (b) ρ = 0 | $5,520 | $-2,217 | 21 % | 0 % | 12 % | 61 % | $7,966 |
| 3 | (a) ρ = 1 | $8,647 | $-7,027 | 30 % | 0 % | 34 % | 61 % | $11,956 |
| 3 | (c) ρ = 0.5 | $8,567 | $-4,461 | 23 % | 0 % | 13 % | 65 % | $11,956 |
| 3 | (b) ρ = 0 | $8,637 | $-1,007 | 13 % | 0 % | 4 % | 75 % | $11,948 |
| 4 | (a) ρ = 1 | $11,728 | $-9,233 | 29 % | 1 % | 34 % | 64 % | $15,939 |
| 4 | (c) ρ = 0.5 | $11,707 | $-5,294 | 22 % | 0 % | 10 % | 70 % | $15,932 |
| 4 | (b) ρ = 0 | $11,708 | $456 | 9 % | 0 % | 1 % | 83 % | $15,933 |
| 5 | (a) ρ = 1 | $15,047 | $-10,987 | 28 % | 0 % | 34 % | 66 % | $19,902 |
| 5 | (c) ρ = 0.5 | $15,002 | $-5,746 | 20 % | 0 % | 7 % | 73 % | $19,901 |
| 5 | (b) ρ = 0 | $14,818 | $2,221 | 6 % | 0 % | 1 % | 88 % | $19,918 |

## + finish-line + 728×3 — una cuenta: media $3,883/año, P(neto < 0) 29 %, P(sin ningún pago) 1 %

| N | caso | ingreso anual esperado | p10 | P(total < 0) | P(sin ningún pago en ninguna cuenta) | P(todas pierden) | P(total ≥ $3k) | costos medios (mensualidades+activaciones+resets) |
|---|---|---|---|---|---|---|---|---|
| 1 | — | $3,890 | $-2,713 | 28 % | 1 % | 28 % | 49 % | $3,941 |
| 2 | (a) ρ = 1 | $8,457 | $-4,740 | 26 % | 1 % | 29 % | 63 % | $7,885 |
| 2 | (c) ρ = 0.5 | $8,495 | $-3,272 | 21 % | 0 % | 15 % | 67 % | $7,876 |
| 2 | (b) ρ = 0 | $8,463 | $-1,496 | 15 % | 0 % | 8 % | 72 % | $7,881 |
| 3 | (a) ρ = 1 | $13,007 | $-6,947 | 25 % | 1 % | 29 % | 67 % | $11,824 |
| 3 | (c) ρ = 0.5 | $12,977 | $-3,702 | 18 % | 0 % | 9 % | 73 % | $11,828 |
| 3 | (b) ρ = 0 | $12,962 | $670 | 9 % | 0 % | 2 % | 84 % | $11,826 |
| 4 | (a) ρ = 1 | $17,469 | $-9,024 | 25 % | 1 % | 29 % | 69 % | $15,771 |
| 4 | (c) ρ = 0.5 | $17,537 | $-4,264 | 17 % | 0 % | 7 % | 77 % | $15,772 |
| 4 | (b) ρ = 0 | $17,664 | $3,174 | 5 % | 0 % | 1 % | 90 % | $15,762 |
| 5 | (a) ρ = 1 | $22,065 | $-10,892 | 24 % | 1 % | 29 % | 71 % | $19,723 |
| 5 | (c) ρ = 0.5 | $22,210 | $-4,268 | 16 % | 0 % | 5 % | 79 % | $19,700 |
| 5 | (b) ρ = 0 | $22,251 | $5,941 | 3 % | 0 % | 0 % | 94 % | $19,694 |

## Reglas que limitan o penalizan la escala (RULEBOOK_XFA.md; hechos del Help Center leído el 20-oct salvo lo marcado)
- Hasta **5 XFA activas** a la vez (1.2). Número máximo de Combines simultáneos: **no está en lo que leí (NO VERIFICADO; pregunta para Topstep)**.
- **«Varias cuentas tocando el MLL el mismo día»** es un motivo público de RTP (6.1) y las **compras excesivas de Combines/Resets** son conducta prohibida (6.3, umbral sin publicar). El caso (a) (mismos trades en todas las cuentas) **produce exactamente ese patrón**: aunque cada cuenta sea legítima, N cuentas con el mismo trade pierden juntas el mismo día. Hoy una cuenta compra ≈ 44–53 Combines/año; N cuentas multiplican ese número. Se reporta como **riesgo de reglas**, no como palanca.
- Explícitamente fuera de alcance: lados opuestos entre cuentas para «asegurar» un pase (apilamiento/cobertura entre cuentas; viola los términos).
- Si copiar la misma estrategia en cuentas propias en paralelo está permitido: **NO VERIFICADO (pregunta para Topstep)**; restricciones de noticias del Combine: **NO VERIFICADO**.