# bulenox/ — rama de I+D `research/bulenox-tailored` (sandbox)
Objetivo: probar un camino **a medida para Bulenox** (con API de terceros de $100/mes y todas las reglas verificadas), sin tener que parecerse al Glitch actual de Topstep. **No toca producción, Railway, Topstep ni el Pi; sin credenciales ni red.**

| Archivo | Qué es |
|---|---|
| `RULES.md` | Reglas verificadas con fuente y lista de lo no confirmado |
| `rules.py` | Las mismas reglas como datos ejecutables (planes, topes, pagos, comisiones, costo de API) |
| `account.py` | Motor de reglas de cuenta a nivel de barra (drawdown dinámico/EOD, lock, DLL suave, escalado, pagos) |
| `barsim.py` | Simulador rápido (numba) equivalente al motor, con slippage del stop y orden de barra conservador |
| `broker_port.py` | Contrato de broker + `SimBroker` (reglas simuladas) + `RithmicBroker` (solo contrato) |
| `EXECUTOR_DESIGN.md` | Diseño del ejecutor, opciones de conexión, preguntas para Bulenox |
| `experiments/exp1..3` | Calificación a medida · etapa fondeada a medida · pipeline y escala a varias cuentas |
Pruebas: `python -m pytest tests/test_bulenox_account.py tests/test_bulenox_barsim.py tests/test_bulenox_broker.py -q`.
Datos: `data_cache/*.parquet` (no versionados). Reporte: `REPORT_BULENOX_TAILORED_2026-10-08.md`.
