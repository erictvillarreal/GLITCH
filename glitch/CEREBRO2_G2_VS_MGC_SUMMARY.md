# Resumen ejecutivo — arquitectura de 2 geometrías (06-sep-2026, actualizado 07-sep-2026)

**Decisión de arquitectura propuesta:** G2 para pasar el Combine → candidato MGC/150K para operar la XFA una vez fondeado. Son dos problemas de optimización distintos — no existe una sola geometría que sea óptima para ambos.

| | **G2 (Combine)** | **MGC/150K (XFA)** |
|---|---|---|
| Producto / cuenta | MES / 50K | MGC / 150K |
| Geometría | SL=100 / TP=40 ticks (RR=0.40) | SL=TP=364 ticks (RR=1.0) |
| Dirección | Alternada, sin señal | Alternada, sin señal |
| Contratos (nc) | 40 | 6 |
| WR objetivo | ~70.6% (empírico, validado contra MES real) | **49.97% empírico** (validado 07-sep-2026 contra MGC real — ver abajo) |
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

## WR de MGC — validado (07-sep-2026)

`scripts/validate_mgc_wr_empirical.py` corrido contra 2 años reales de MGC. Primera lectura de la métrica estándar (`measure_wr_bracket()`) dio 34.9% — alarmante — pero resultó ser un artefacto: 30.2% de los trades de calibración expiran por tiempo (barreras muy anchas relativas al holding window) y esa métrica diluye el denominador con ellos, el mismo problema ya corregido antes para el win_rate de la Dirección 1. La métrica correcta (TP/(TP+SL), excluyendo time-exits) da **WR=49.97% — prácticamente idéntico al 50% teórico** (diferencia: -0.03pp). Pequeña asimetría long/short (52.78%/47.16%) tratada como ruido direccional, mismo criterio ya aplicado a G2, no cambia la recomendación de alternar sin señal.

**El candidato MGC/150K queda validado en sus dos supuestos centrales: WR≈50% empírico y pass rate de Combine 46.9%.**

## Verificación final antes de producción (07-sep-2026)

Dos chequeos adicionales, mismo estándar exigido a cualquier candidato:

1. **Out-of-sample por sub-período:** WR condicional en 3 sub-períodos calendario independientes = 49.90% / 49.92% / 49.89% — estable, sin sorpresas, diferencias <0.15pp en los 3.
2. **Sensibilidad direccional del Combine:** la asimetría long/short **se invierte de signo entre sub-períodos** (long favorecido en 2 de 3, short en el 3º) — confirma que NO es un sesgo real y persistente, solo ruido. El pass rate del Combine SÍ es sensible a esta clase de asimetría si fuera persistente (rango observado 30%-64% de pass rate según qué lado domine) — pero el diseño "alternado" ya elegido es exactamente lo que protege contra ese riesgo, dado que ningún lado gana de forma estable.

**Ningún ítem pendiente de validación básica queda abierto. Fragilidad de modelo a tener presente (no de ejecución):** el candidato opera muy cerca del punto de equilibrio RR=1.0/WR=50%, donde el pass rate del Combine es inherentemente sensible a pequeños errores de calibración del WR real.

## Estado

Todo esto vive en `cerebro2-dev`. No se tocó producción, no se conectó nada a Railway. Nada de esto se ejecuta hasta que el usuario lo decida.
