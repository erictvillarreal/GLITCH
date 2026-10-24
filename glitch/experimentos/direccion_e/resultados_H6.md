# resultados_H6 — geometría del trade y salida por tiempo

## 1. Horario de FLATTEN en MGC (3 micros, SL = TP = 364, entrada 7:15 CT; datos limpios)

| flatten (CT) | días | TP % | SL % | FLATTEN % | WR_dec `alternate` | cobrado por XFA (WR 50 %, W2) | P(≥1 pago) | neto $/año/cuenta |
|---|---|---|---|---|---|---|---|---|
| 10:30 | 503 | 16.5 | 16.9 | 66.6 | 49.4 % | $634 | 36.3 % | $1,205 |
| 12:00 | 503 | 18.1 | 20.5 | 61.4 | 46.9 % | $639 | 34.2 % | $1,281 |
| 13:30 | 498 | 19.3 | 22.5 | 58.2 | 46.2 % | $639 | 33.5 % | $1,335 |
| 14:30 (hoy) | 488 | 20.9 | 23.2 | 55.9 | 47.4 % | $640 | 32.8 % | $1,365 |

Lectura: cerrar antes baja la fracción decidida y el cobrado; **no hay un horario que suba el WR_dec de forma defendible** (con martingala es ≈ 50 % en cualquier horario; las diferencias son ruido de 215 decididos). El flatten tampoco puede moverse después de las 15:10 CT (regla de Topstep, `RULEBOOK_XFA.md` 1.9).

## 2. Razón TP:SL distinta de 1:1 en la XFA de MGC (3 micros). Se compara la **deriva necesaria para neto anual = 0** (z* = μ/σ por sesión), no el WR

Una razón distinta de 1:1 cambia el WR_dec de equilibrio **mecánicamente** (con martingala WR₀ = SL/(TP+SL)); por eso la columna que cuenta es z*: cuánta deriva real hace falta. **Una razón con menor WR* pero mayor z* NO es una mejora.** Resolución de z*: ± ≈ 0.01 (interpolación en una malla de 0.03 y ruido de nivel de ±$100); **no hay bootstrap de días**: diferencias de Δz < 0.015 no se distinguen.

| geometría (TP, SL) ticks | razón | WR₀ mecánico = SL/(TP+SL) | neto $/año a deriva 0 | z* (deriva necesaria) | WR_dec en z* (aprox.) | veredicto frente a 364/364 |
|---|---|---|---|---|---|---|
| (364, 364) | 1.00:1 | 50.0 % | $1,376 | -0.037 | 48.4 % | base |
| (546, 364) | 1.50:1 | 40.0 % | $1,712 | -0.048 | 30.4 % | sin diferencia distinguible (dentro del ruido de 443 días) |
| (364, 546) | 0.67:1 | 60.0 % | $1,765 | -0.050 | 66.9 % | sin diferencia distinguible (dentro del ruido de 443 días) |
| (485, 243) | 2.00:1 | 33.4 % | $1,349 | -0.035 | 23.6 % | sin diferencia distinguible (dentro del ruido de 443 días) |
| (243, 485) | 0.50:1 | 66.6 % | $990 | -0.034 | 74.0 % | sin diferencia distinguible (dentro del ruido de 443 días) |

(La columna «WR_dec en z*» es el WR_dec simulado con la deriva z* sobre los días reales: muestra que **el WR de equilibrio cambia por la geometría aunque la deriva necesaria sea la misma**.)

## 3. Interacciones (por cuenta, $/año; ventaja por deriva en ambas etapas con la misma μ/σ; Combine mezcla {1,3}; stop 0.5)

| configuración | WR 47.4 % | WR 48.5 % | WR 50 % | WR 52 % |
|---|---|---|---|---|
| hoy: P0 + 3×364 | $-1,103 | $-38 | $1,365 | $3,836 |
| finish-line + 3×364 | $-351 | $851 | $2,361 | $5,037 |
| P0 + 728×3 | $-652 | $943 | $2,670 | $5,846 |
| finish-line + 728×3 | $206 | $1,992 | $3,841 | $7,232 |
| finish-line + 4→1 micros (cobro ≥ $1,500) | $468 | $1,643 | $3,026 | $5,100 |

Política de cobro: «cobrar ya» es la de las filas con 3×364/728×3; 4→1 espera a $1,500 de saldo (y baja a 1 micro). **728×3, 4→1 y el uso del tamaño máximo tocan los criterios públicos de RTP/«conducta prohibida»** (`RULEBOOK_XFA.md` 6.1–6.4): preguntas sin responder.

## 4. La barrera efectiva del Combine (MES nc 40)

- Con SL nominal de 100 ticks: SL 0.0 %, liquidación por MLL 47.2 %, TP 52.8 % (LARGO, slip 0). Con un stop a 40 ticks: TP 52.8 %. **El SL de 100 ticks no opera: la barrera real es la liquidación a $2,000/($1.25×40) = 40 ticks.**
- Con martingala P(TP antes que liquidación) = 40/(40+32) = **55.6 %** (no 75.8 % = 100/132, que sería el número si el SL de 100 fuera efectivo). El resultado observado 52.8–56.7 % es esa cifra más la deriva de la muestra.
- Por eso el WR «de equilibrio» del Combine **no es comparable** con el de la XFA ni con el de los scripts que usaban SL 100: la Parte E §4 y H1 ya usan la barrera efectiva.