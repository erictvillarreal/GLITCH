# J7 — Veredicto honesto

Lunes 26-oct-2026 · BORRADOR para decidir con Eric. Es un **juicio** apoyado en números modelados (`resultados_J5.md`, `resultados_J8.md`, `REPORTE_H1b.md`); no es una prueba. Cada cifra: MODELADO sobre 443–492 días reales de 5 min salvo que diga otra cosa; supuestos de entrada: slippage de 8 observaciones de MES (la 8.ª inferida, NO VERIFICADA), OPS $245/año.

## 1. Lo que la evidencia dice y no dice

- **No hay ventaja direccional demostrada.** Parte E: 0 de 16 pruebas pasan el criterio pre-registrado; las 3 que pasan una condición son el sesgo alcista del índice. MGC: sin señal. La dirección de producción (`alternate`) es deliberadamente una moneda.
- **El WR no es cognoscible a corto plazo.** El `alternate` de MGC midió 47.4 % [41, 54] sobre 215 sesiones decididas. Distinguir 47.4 de 50 % necesita ≈ 2,300 decididas (≈ 9 años de MGC). Las sesiones vivas (8 de MES, 3 de MGC) no tienen potencia.
- **El resultado depende de un parámetro que no podemos aprender:** el neto anual por cuenta de la cadena Combine → XFA es **−$145 [−356, +319] a WR 47.4 %** y **+$2,543 [2,336, 2,939] a WR 50 %** (OPS $245). El equilibrio está en WR ≈ **47.5 %** (con costos B de $827: 48.0 %). El WR medido cae **en** el equilibrio.
- Un buen o mal arranque **no** informa el WR: 5 sesiones de XFA o 3 intentos de Combine no distinguen 47.4 de 50 %.

## 2. EV, sin suavizar

| etapa | cifra | estado |
|---|---|---|
| Cadena anual por cuenta, WR medido (47.4 %), OPS $245 | **−$145 [−356, +319]** (≈ 0 con signo incierto; **negativa** si los costos son los del escenario B: ≈ −$727) | MODELADO |
| Cadena anual por cuenta, WR 50 % | +$2,543 | MODELADO (el WR de 50 % es una hipótesis, no un dato) |
| Combine: probabilidad de pasar una cuenta nueva (MES, nc 40, slippage empírico, WR 50 %) | 24.9 % ⇒ ≈ 4.0 compras de $49 ($196) + $149 de activación ≈ **$345** por XFA alcanzada | MODELADO |
| XFA, cobrado esperado por vida | **$384 [362, 437]** a WR 47.4 %; $618 a 50 % | MODELADO |
| **75 %** de las XFA **no pagan nada nunca** a WR 47.4 % (68 % a WR 50 %); mediana al 1.er pago 8 días de trading | | MODELADO |
| XFA **condicionada a haber pasado** (Combine ya pagado): cobrado − $149 − OPS prorrateado | ≈ **+$230** a WR 47.4 % | MODELADO |

Lectura: **comprar Combines al WR medido es una apuesta de EV ≈ 0 con varianza grande**; la parte con EV positivo del modelo es *la XFA ya alcanzada* (el costo de llegar ya está pagado). Es una lotería de pagos grandes y poco frecuentes (primer pago medio ≈ $1,000), no un flujo estable.

## 3. Opciones y veredicto

| opción | EV modelado (WR 47.4 %) | varianza / riesgo de reglas | veredicto |
|---|---|---|---|
| **A. Parar ahora** | $0 (pierdes lo ya pagado del Combine actual) | ninguno | Es la única opción con EV exacto 0 y varianza 0. **No** es la mejor si la XFA ya está pagada: ver B |
| **B. Activar la XFA y operar la producción 3×364, con el día 1 de FOMC en 1 micro** | **+$230 por XFA** (sobre la activación), cobrado $384 | 75 % de las XFA pagan 0; cada XFA muerta exige otra Combine (≈ $345) | **Recomendada para la XFA que Eric ya tiene**: es el único tramo con EV positivo en el modelo y la decisión de activar ($149) se toma con el Combine ya hundido |
| **C. B + palancas estructurales (finish-line; 728×3)** | **+$702 [+470, +1,421]** de neto anual por cuenta con ambas (vs −$145 hoy), **+$848 [+488, +1,354]** de mejora pareada | requiere código de capital (revisión humana) y **RTP/«conducta» sin respuesta** para 728×3; 728×3 liquida el día 1 en 9 % de las XFA | **Es el único camino a EV positivo con el WR medido**, pero se apoya en el motor y en un supuesto de slippage (N = 8, sin CSV). Hacerlo *después* de la respuesta de Topstep y de medir el slippage, no antes |
| **D. Escalar a más cuentas** | EV por cuenta ≈ −$145 (WR 47.4) ⇒ **multiplica la pérdida esperada y la varianza** | RTP: «varias cuentas tocando el MLL el mismo día»; mismas señales en todas las cuentas | **No** con la evidencia actual. A WR 50 % cada cuenta añade ≈ $2.6k, pero ese 50 % es lo que no sabemos |
| **E. Cambiar de geometría (más angosta, otros horarios, otros productos, filtros de volatilidad)** | todas las palancas probadas fuera de las estructurales quedaron < $500/año/cuenta o negativas (Partes G, H) | — | No hay evidencia a favor. J6 (planes angostos) no se hizo |

**Mi veredicto:** *con la evidencia disponible, la mejor opción es B para la XFA actual, C como siguiente paso condicionado a dos datos (respuesta de Topstep sobre RTP/conducta y slippage medido de MGC y de MES), y no D.* Es una recomendación de **reducir el costo de la apuesta y no ampliarla**, no de que haya una ventaja. Si Eric prefiere cero varianza, A es racional.

## 4. Qué cambiaría este veredicto

- **Hacia D/C con confianza:** slippage medido de entrada ≤ 1 tick de media con N ≥ 30 en TopstepX (el `exec_exit` y los tiempos del parche J4-d lo miden); respuesta escrita de Topstep que permita 728×3 y cuentas paralelas; y ≥ 1–2 años de sesiones vivas con WR_dec ≥ 50 % (no hay forma más rápida de saber el WR).
- **Hacia A:** slippage medio ≥ 2 ticks con N ≥ 30 (el escalón de +2/+3 ticks cuesta ≈ $1.5–2k/año/cuenta en el Combine), una respuesta de Topstep que prohíba lo estructural, o que en ≥ 12 intentos de Combine no haya ningún pase (si p = 24.9 % eso ocurre 3 % de las veces: 0.751¹² = 3.2 %; una racha menor no refuta p).
- **Regla de parada en dinero** (la fijas tú; yo no conozco tu presupuesto): como la señal no informa el WR, la regla útil es financiera —un tope de pérdida acumulada por cuenta y por periodo— y no «hasta ver si el WR sube». Con p = 24.9 % la compra de Combines sin pasar cuesta ≈ $196 de media hasta el pase, pero la cola es larga: 5 fallos seguidos 24 %, 10 fallos 6 %.

## 5. Sin frases que suavicen

- El WR que mediste (47.4 %) es **compatible con 50 % y con 44 %**. El modelo no puede decirte que tu EV sea positivo.
- Con costos de $827 al año (escenario B) y el WR medido, la cadena **pierde** ≈ $730 por cuenta y año; con $245, está en ≈ −$145 ± $340.
- La XFA «paga» en 25 % de los casos a WR 47.4 %. En los otros 75 % la cuenta se liquida sin cobrar nada.
- Todo lo anterior supone que el motor reproduce las reglas de Topstep y que los 2 años de datos son representativos; ninguna de las dos cosas está contrastada con una XFA viva.
