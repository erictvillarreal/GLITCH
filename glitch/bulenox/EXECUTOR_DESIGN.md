# Diseño de un ejecutor a medida para Bulenox (sin implementación real, sandbox)
Objetivo: poder usar la estrategia (un bracket por día, cierre antes de las 15:59 CT) sobre cuentas Bulenox con el costo de **API de terceros de $100/mes**, aprovechando que Bulenox permite cuentas ilimitadas (hasta 5 Master-level) bajo un mismo Rithmic User ID. **Nada aquí se conecta a Bulenox ni a Rithmic**; solo existe el contrato (`bulenox/broker_port.py`) y un broker simulado con las reglas (`SimBroker`) para probar la lógica sin riesgo.

## 1. Restricciones duras (de `RULES.md`)
- Bulenox opera sobre **Rithmic Paper Trading (Chicago)**. R|Trader Pro y NinjaTrader 8 son **solo Windows**; hoy el ejecutor corre en un Raspberry Pi (Linux ARM) contra ProjectX/TopstepX, que no sirve aquí.
- Conectarse por API de terceros cuesta **+$100/mes**, y solo se admiten herramientas **propias y de uso personal**; el ToU exige aprobación de Bulenox para algoritmos de terceros y se reserva negar profits si sospecha abuso ("reckless transactions in rough markets…").
- OCO de NinjaTrader es **local**: si se cae la conexión la otra pata puede quedar viva y abrir una posición extra. El ejecutor necesita OCO **del lado del servidor** o una verificación activa.
- Cierre de todas las posiciones antes de las 15:59 CT; DLL suave pausa la jornada (el ejecutor debe respetar `dll_hit`); un día cuenta solo si se abre ≥1 operación; Master exige ≥1 operación por semana.

## 2. Opciones de conexión (a confirmar con Bulenox/Rithmic antes de construir)
| Opción | Qué es | A favor | En contra / desconocido |
|---|---|---|---|
| A. Estrategia nativa en NinjaTrader 8 (NinjaScript) en una máquina Windows | Lógica dentro de NT8 conectado a Rithmic | Sin librería de terceros; ¿quizá sin los $100? | Requiere un Windows siempre encendido; OCO local; reglas sobre VPS/servidor desconocidas |
| B. API de Rithmic (protocolo propio) desde un servicio propio en Linux | Cliente propio sobre la API de Rithmic | Corre en el Pi o en un VPS; control total; OCO/brackets del lado del servidor si la API lo soporta | Cuesta $100/mes por la API de terceros; requiere acceso/credenciales de API de Rithmic; riesgo de mantenimiento; "DTC Protocol Bridge API" aparece nombrada en el ToU como ejemplo de abuso |
| C. Ejecución semimanual (señal por Telegram, orden a mano) | El humano coloca el bracket | Cero riesgo de API/ToU | No escala a varias cuentas; pierde el sentido de la automatización |
Recomendación de partida: **B**, pero solo tras la respuesta escrita de Bulenox a las preguntas de la sección 5.

## 3. Arquitectura propuesta (B)
1. **Señal** (igual que hoy, Railway): `orden_pendiente_<producto>.json` con producto, lado, nc, TP/SL en ticks, hora, **cuenta destino**.
2. **Orquestador de cuentas**: lee la lista de cuentas activas (≤5 Master-level + calificaciones), aplica el tope de contratos por cuenta (`rules.plan(...).micros_cap(cash_on_hand)`), el DLL y el estado de la cuenta (`account_state`) antes de cada entrada; una falla en una cuenta no detiene las otras.
3. **BrokerPort** (`place_bracket`, `flatten`, `cancel_all`, `account_state`): implementación real = Rithmic; implementación de pruebas = `SimBroker` (reglas de Bulenox a nivel de barra).
4. **Guardas heredadas de la auditoría del 4-oct (Pi):** marcador local de "al menos/máximo una ejecución", entrada solo antes de una hora límite, verificación de cuenta plana después de resolver, lecturas estrictas (un error de lectura no es "sin órdenes"), fijar la cuenta destino y una lista de cuentas prohibidas, validación de la señal como cotas superiores, conciliación al reiniciar.
5. **Cierre previo a 15:59 CT** (flatten a las 14:30 CT como hoy) y vigilancia independiente (watchdog) que verifica posición/órdenes a las 14:35 CT.
6. **Costos operativos por mes:** API $100 + datos de mercado (Massive $43.5) + hardware ($1.5): **$145**, compartidos por todas las cuentas.

## 4. Plan de pruebas (todo sin riesgo)
- Reglas: `tests/test_bulenox_account.py` (ejemplos de la ayuda), `tests/test_bulenox_barsim.py` (simulador rápido = motor de reglas, día por día), `tests/test_bulenox_broker.py` (SimBroker).
- Repetición histórica: pasar las barras reales de cada día por `SimBroker.on_bar()` con la lógica del ejecutor y comparar contra `barsim`.
- Caos: desconexión a media posición, orden parcial, DLL en la primera barra, cuenta suspendida, cambio de cuenta destino; todo contra `SimBroker`.
- Antes de dinero: una única cuenta de calificación (costo $143–$175) como prueba real con 1–2 micros, solo si Bulenox confirma por escrito que el ejecutor propio es aceptable.

## 5. Preguntas para Bulenox (por escrito, guardar la respuesta)
1. ¿Una estrategia propia (un bracket por día, sin alta frecuencia) que se conecta por la API de Rithmic requiere aprobación previa? ¿Qué se necesita para obtenerla?
2. ¿Los $100/mes cubren todas mis cuentas bajo un mismo Rithmic User ID? ¿También aplican si uso NinjaTrader nativo?
3. ¿Se acepta que el ejecutor corra en un servidor/VPS/Raspberry fuera de mi casa? (Topstep lo prohíbe; la ayuda de Bulenox no lo menciona.)
4. Momentum y Fast Track: ¿existe reinicio y a qué precio? ¿Qué drawdown, DLL y lock exactos tiene el Momentum Master?
5. ¿Se aplica el lock de saldo inicial + $100 también durante la calificación?
6. ¿Qué descuento da el cupón `BULENOX` y a qué compras aplica?
7. ¿Operar con la misma estrategia en varias cuentas a la vez (hasta 5 Master-level) se considera copiado/abuso o es aceptable?
