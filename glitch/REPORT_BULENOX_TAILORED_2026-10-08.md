# Bulenox a medida (API de $100/mes y reglas verificadas): resultados
*Rama `research/bulenox-tailored`, sandbox, 08-oct-2026. No toca producción, Railway, Topstep ni el Pi; sin credenciales ni red. Código en `bulenox/`, pruebas en `tests/test_bulenox_*.py` (24 pasan), salidas en `bulenox/exp*_output.txt`.*

## 0. Veredicto
1. **Con las reglas verificadas de Bulenox y el costo de API, Bulenox no supera a Topstep para esta estrategia, ni siquiera ajustando la estrategia a sus reglas.** En el mismo marco (simulador por barra, fills conservadores, selección fuera de muestra), una cuenta Topstep rinde ~**$6,300 al año** (p10 −$3,000; P(pérdida) 26%) y Bulenox ~**$1,500–$1,700** (P(pérdida) 42–45%).
2. **Escalar a más cuentas ayuda a Bulenox pero no cierra la brecha.** Con 5 cuentas independientes, Bulenox llega a ~$15,000 al año y Topstep a ~$34,000. El costo fijo de API ($1,740 al año con datos y hardware, contra $714 de Topstep) se diluye con N, pero cada cuenta Bulenox aporta ~$3,300 y cada una de Topstep ~$7,000.
3. **Por qué:** pasar la evaluación es más fácil en Bulenox (43–45% contra ~31–33% de Topstep), pero la etapa fondeada exige más (Master: 10 días, reserva de $2,600, consistencia 40%; Momentum: 5 días rentables, saldo $53,000, consistencia 35%) y cuesta más ($175 + $148, o $143 con Momentum, contra $49 + $149 en Topstep). Los payouts por cuenta salen parecidos ($750–$900 contra $1,080), pero Bulenox necesita más tiempo y más costos fijos para conseguirlos.
4. **Lo mejor que se puede decir de Bulenox:** es una segunda plataforma diversificadora con menos intentos de compra/reinicio por año (≈8 ciclos × 2.2 intentos ≈ 18, contra ≈11 ciclos × 3.2 intentos ≈ 35 en Topstep; cifras derivadas de los pases y duraciones de ciclo medidos), y el pase de calificación es el más alto que he medido con reglas reales (~44%). Pero hoy no mejora el cash flow esperado.
5. **El "cálculo optimista" no es una expectativa.** Con la configuración elegida mirando las dos mitades de la historia (sesgo de selección), Bulenox sale $5,000–$10,000 al año por cuenta. Fuera de muestra baja a ~$1,500 y en el mundo de juego justo a ~$100–$2,500. Úsese solo el escenario fuera de muestra.

## 1. Qué se construyó
- **Reglas como especificación ejecutable** (`bulenox/rules.py`, `RULES.md`): planes Qualification, Momentum y Fast Track, Opciones 1 y 2, escalado por efectivo disponible, DLL suave, lock +$100, reglas de pago de Master, Momentum Master y Fast Track, el 100% de los primeros $10,000, comisiones por lado, cuentas múltiples, costo de API. Cada dato lleva su fuente (centro de ayuda, FAQ, PDF de tarifas, ToU o las páginas que pegaste); lo que no se pudo confirmar está en `rules.UNKNOWN`.
- **Motor de reglas de cuenta** (`account.py`) probado con **los ejemplos numéricos de la propia ayuda de Bulenox** (14 pruebas: ejemplo EOD de 100K, lock de 52,600 → 50,100, ejemplo de drawdown dinámico, tabla de escalado, DLL suave, pago mínimo de $53,600, consistencia 40%, ejemplos de Fast Track de 50K y 25K, Momentum).
- **Simulador rápido por barra** (`barsim.py`, numba) validado día por día contra el motor (Opción 1 y 2) y contra la teoría: en el mundo de juego justo da 40% (Opción 2; techo 45.5% sin costos) y 30% (Opción 1; teoría 30.1%). Incluye slippage del stop y un orden de barra conservador (el orden "neutral" daba 39.9% para la Opción 1 en MNQ, por encima de la teoría; el conservador lo corrige).
- **Contrato de broker + SimBroker** (`broker_port.py`) y **diseño del ejecutor** (`EXECUTOR_DESIGN.md`): opciones de conexión, restricciones (R|Trader y NinjaTrader solo Windows; OCO de NinjaTrader es local y puede dejar posiciones extra), guardas heredadas de la auditoría del Pi y **siete preguntas para Bulenox** por escrito.

## 2. Resultados
**Calificación** (exp1; 50K, selección en una mitad y evaluación en la otra, fills exactos): Opción 2 gana a la Opción 1 en todos los casos.
| Plan | Pase OOS | Config consistente | Pase en mundo justo | Costo hasta Master activa (fees + reinicios + activación + API) | Días esperados |
|---|---|---|---|---|---|
| Qualification Opc.2 | 52.6% | MGC 7:13, TP 100 ticks, G=100% del objetivo | 45.7% | $497 | 5.3 |
| Momentum Opc.2 | 47.7% | MGC 7:13 (TP 160) | 42.5% | $395 | 4.2 |
| Qualification Opc.1 | 28.8% | MES 8:45 | 30.0% | $585 | 13.8 |
| Momentum Opc.1 | 25.3% | MES 8:45 | 26.7% | $561 | 14.1 |
Con slippage de 50% del sobrepaso de la barra, el pase de las mejores configuraciones cae de 52% y 49% a **44% y 43%**.

**Pipeline completo y escala** (exp3/exp4; neto de 12 meses, después de fees, reinicios, activaciones y costos compartidos; slip 0.5):
| Plataforma | 1 cuenta, fuera de muestra | P(pérdida) | 5 cuentas independientes | Mundo justo, 1 cuenta |
|---|---|---|---|---|
| **Topstep** (Combine + XFA) | **$6,255** | 26% | $34,144 | $8,412 |
| Bulenox Qualification + Master | $1,653 | 45% | $15,522 | $2,485 |
| Bulenox Momentum | $1,518 | 42% | $14,662 | $119 |
| Bulenox Fast Track | −$836 | 60% | $2,761 | −$1,324 |
(Fast Track viene de exp3; el resto de exp4, mismo marco. Las cuentas correlacionadas, con las mismas señales, dan la misma media y más riesgo de cola: P(pérdida) ≥ 29% aun con 5 cuentas.)

**Payout por cuenta fondeada** (exp2/3, fuera de muestra): Master $923 (P≥1 pago 24%, vida 26 días), Momentum $770 (25%, 25 días), Fast Track $614; Topstep $1,079 (21%, 7 días). El payout esperado no es la diferencia; lo son el costo por cuenta y el tiempo.

## 3. Riesgos y límites
- **Conducta y términos:** el ToU de Bulenox exige aprobación para algoritmos de terceros y se reserva negar profits si sospecha abuso ("reckless transactions in rough markets"). Operar las mismas señales en varias cuentas a la vez no está prohibido en la ayuda ("Varias cuentas"), pero tampoco hay un umbral; ver pregunta 7.
- **Infraestructura:** Bulenox opera en Rithmic Paper Trading; el ejecutor actual habla con ProjectX/TopstepX. Hay que construir un adaptador de Rithmic (API de terceros: $100/mes) o usar NinjaTrader en Windows, con OCO local.
- **Datos:** una sola historia de 515 días, barras de 5 min; la API/ejecución real puede cambiar fills, comisiones y latencia. Los $100 de API son un supuesto de costo fijo por conexión; si Bulenox cobrara por cuenta, el escalado empeora.
- **Sin confirmar** (ver `RULES.md` §6): reinicio de Momentum y Fast Track, lock durante la calificación, parámetros exactos del Momentum Master, descuento del cupón (no aplicado), política de servidor/VPS, reglas de la cuenta financiada real.
- Escalado XFA de Topstep (20/30/40) y el límite de una cuenta personal (ToU Sec. 16) siguen sin verificar; el cálculo de Topstep a 5 cuentas es un techo teórico.

## 4. Qué haría con esto
1. **No construir el adaptador de Rithmic todavía.** Con estas cifras, el trabajo no se paga: Topstep rinde ~4× por cuenta y su ejecutor ya existe.
2. Si quieres conservar la opción, **enviar las siete preguntas de `EXECUTOR_DESIGN.md` a Bulenox** y guardar las respuestas por escrito; cambiarían el costo (API compartida o por cuenta, reinicios de Momentum, cupón) más que cualquier ajuste de la estrategia.
3. Si algún día se usa Bulenox, la combinación a probar primero es **Momentum Opción 2 con MGC 7:13**: es el camino más barato ($143) y el de mejor pase, y la API puede compartirse entre cuentas.
4. El mayor ahorro de dinero sigue en Topstep: pasar el Combine rápido con el TP corregido y reducir compras/reinicios innecesarios (ver reporte del 7-oct).

## Reproducir
```bash
cd glitch   # rama research/bulenox-tailored; datos en data_cache/*.parquet (no versionados)
python -m pytest tests/test_bulenox_account.py tests/test_bulenox_barsim.py tests/test_bulenox_broker.py -q
python bulenox/experiments/exp1_qualification.py 50000
python bulenox/experiments/exp2_funded.py            # ~3 min
python -m bulenox.experiments.exp3_pipeline_scale
python -m bulenox.experiments.exp4_topstep_vs_bulenox
```
