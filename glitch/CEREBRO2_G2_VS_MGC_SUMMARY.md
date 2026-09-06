# Resumen ejecutivo — arquitectura de 2 geometrías (06-sep-2026)

**Decisión de arquitectura propuesta:** G2 para pasar el Combine → candidato MGC/150K para operar la XFA una vez fondeado. Son dos problemas de optimización distintos — no existe una sola geometría que sea óptima para ambos.

| | **G2 (Combine)** | **MGC/150K (XFA)** |
|---|---|---|
| Producto / cuenta | MES / 50K | MGC / 150K |
| Geometría | SL=100 / TP=40 ticks (RR=0.40) | SL=TP=364 ticks (RR=1.0) |
| Dirección | Alternada, sin señal | Alternada, sin señal |
| Contratos (nc) | 40 | 6 |
| WR objetivo | ~70.6% (empírico, validado contra MES real) | 50% (**teórico, NUNCA validado contra MGC real** — ver tarea pendiente abajo) |
| **Diseñado para** | Pasar el Combine rápido | Sobrevivir muchos días en la XFA |
| **Pass rate del Combine** | **~81.4%** | **46.9%** — casi coin-flip |
| Días promedio a resolución (Combine) | ~3.8 días | ~7.6 (pasa) / ~5.6 (truena) |
| Colchón de capital — fase Combine | Bajo (pass rate alto, pocas fees repetidas) | **Más alto**: ~53% de intentos fallan, cada fallo cuesta $149 (150K); P(≥5 fallos seguidos)=37.5%, P(≥10)=11.0% |
| Prob. ≥1 payout en XFA (una vez fondeado) | No evaluado con esta geometría | 46.2% |
| Payout esperado de por vida en XFA | No evaluado con esta geometría | $2,169 |
| Colchón de capital — fase XFA | N/A | **$894 (mediana) / $2,679 (p90)** |
| Payout total esperado a 1 año (cadena completa Combine+XFA) | No aplica (G2 no se diseñó para XFA) | **$31,257 mediana** (p10–p90: $15,809–$53,861) |

## El punto central

**Usar la geometría de MGC para intentar pasar el Combine sería un error de diseño** — su pass rate (46.9%) es casi la mitad del de G2 (81.4%), porque fue optimizada para el objetivo contrario (sobrevivir con pocas pérdidas consecutivas en XFA, no maximizar velocidad de aprobación). La arquitectura correcta es secuencial: **pasar con G2, migrar a la geometría MGC solo después de estar fondeado.**

## Lo que falta antes de confiar en el lado MGC/XFA

El WR=50% de MGC es un **supuesto teórico de Monte Carlo** (gambler's ruin para RR=1.0 simétrico) — a diferencia del WR de G2 (~70.6%), **nunca se verificó contra datos reales de precio de MGC**. Preparado (no corrido): `scripts/validate_mgc_wr_empirical.py`, misma metodología que ya validó a G2 (bracket optimista/conservador, `measure_wr_bracket()`, sin señal predictiva). Correr esto es el paso obligatorio antes de tratar los números de arriba como algo más que una hipótesis de diseño.

## Estado

Todo esto vive en `cerebro2-dev`. No se tocó producción, no se conectó nada a Railway. Nada de esto se ejecuta hasta que el usuario lo decida.
