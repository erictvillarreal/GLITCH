# Reglas de Bulenox verificadas (leídas el 08-oct-2026)
Fuentes: **[HC]** centro de ayuda `bulenox.com/es/help-center/<página>` (general, qualification, fast-track, momentum, master, funded, connection, subscription, warning) · **[FAQ]** `bulenox.com/es/faq` · **[PDF]** `legal/Bulenox-Rates.pdf` (11-ago-2026) · **[ToU]** `legal/Terms_of_Use.pdf` · **[USR]** páginas de precios que pegó el usuario el 07/08-oct-2026. Versión ejecutable: `bulenox/rules.py`; pruebas con los ejemplos numéricos de la propia ayuda: `tests/test_bulenox_account.py`.

## 1. Planes (50K; otros tamaños en `rules.py`)
| | Qualification | Momentum | Fast Track |
|---|---|---|---|
| Qué es | Evaluación y luego Master | Evaluación que incluye Master gratis | Sin evaluación: simulada financiada desde el día 1 |
| Precio (pago único, 30 días de acceso) | $175 [USR] | $143 [HC momentum, USR] | $488 [HC fast-track, USR] |
| Opción 1 (drawdown dinámico, en tiempo real, incluye no realizado y comisiones; contratos fijos) | DD $2,500, 7 minis, sin DLL | DD $2,250, 7 minis, sin DLL | DD $2,250, 7 minis |
| Opción 2 (drawdown EOD; DLL suave) | DD $2,500, DLL $1,100, **escalado** 2→4→7 minis | DD $2,250, DLL $1,200, 4 minis fijos | DD $2,250, DLL $1,200 (permanente), 4 minis fijos |
| Objetivo | $3,000 | $3,000 | primer pago: $3,000 de ganancia |
| Mínimo de días | ninguno (un día cuenta si se abre ≥1 operación) | ninguno | ninguno |
| Reinicio | $78, no amplía los 30 días [HC qualification] | **no documentado** | **no documentado** |
| Activación del Master | $148 | $0 | $0 |
La opción (1 o 2) queda **bloqueada de por vida** en la cuenta [HC, FAQ, USR]. Escalado de Qualification Opción 2, 50K, por *efectivo disponible* (saldo − saldo inicial): hasta $1,500: 2 minis · $1,501–4,000: 4 · $4,001+: 7; el límite sube y baja con el efectivo [HC]. 1 mini = 10 micros.

## 2. Drawdown, DLL, sesión
- **EOD (Opción 2):** el umbral se recalcula una vez por jornada con el máximo saldo de cierre; las fluctuaciones intradía no lo mueven [HC]. Ejemplo oficial: 100K, DD $3,000: cierra 101,000 → umbral 97,000→98,000; 100,500 → sigue 98,000; 102,500 → 99,500.
- **Dinámico (Opción 1):** sigue el valor máximo incluido el no realizado, en tiempo real; nunca baja [HC].
- **Lock:** en Master y Fast Track el drawdown se fija en saldo inicial + $100 (50K Master: al cerrar en $52,600 queda en $50,100). Para la calificación no está documentado (se asume igual) [HC master/fast-track].
- **DLL (Opción 2):** pérdida neta máxima por jornada (17:00–16:00 CT) con realizado + no realizado + comisiones; al alcanzarla el trading se desactiva el resto de la jornada, **no es infracción** y se reanuda al inicio de la siguiente sesión [HC]. En Master se elimina de forma permanente al fijarse el drawdown; en Fast Track permanece toda la vida de la cuenta (25K sin DLL) [HC].
- **Sesión:** 17:00–16:00 CT; todas las posiciones cerradas antes de las 15:59 CT; overnight prohibido; noticias permitidas sin ventanas de bloqueo [HC, FAQ].
- Alcanzar el drawdown suspende la cuenta (Qualification: reinicio de $78) [FAQ].

## 3. Pagos
- **Master (50K):** ≥10 días de trading individuales; solicitud mínima $1,000; reserva de seguridad $2,600 sobre el saldo inicial (para el mínimo hace falta saldo ≥ $53,600; tras el pago quedan ≥ $52,600); consistencia 40% (mejor día / P&L del periodo); tope por pago $1,500 en los **tres primeros**, sin tope después; el mejor día **no** se reinicia tras un pago; pagos semanales (miércoles; solicitud antes del viernes 23:59 CT); inactividad: ≥1 operación por semana [HC master].
- **Momentum Master (50K):** 5 días rentables con ≥$150 netos tras comisiones; consistencia 35% del beneficio neto del ciclo; saldo mínimo $53,000; solicitud mínima $1,000; topes $1,500 / $2,000 / $2,500 / $3,000 (el 4.º se mantiene); pagos diarios [HC momentum, FAQ].
- **Fast Track (50K):** primer pago al alcanzar +$3,000 con consistencia 20% (25% el 2.º, 30% desde el 3.º); ciclos siguientes: +$2,000 de ganancia nueva y solo se retira lo que supere ese nivel (el nivel queda como colchón); mínimo $1,000; topes $2,000 (pagos 1–3) / $2,500 (4.º en adelante); un pago no puede dejar el saldo en el umbral; solicitudes antes de las 12:01 CT se procesan el mismo día [HC fast-track].
- **Reparto:** los primeros $10,000 en pagos son 100% del trader (una sola vez por trader, en todas las cuentas Fast Track y Master); después 90/10 [HC, FAQ].
- Pagos por ACH/transferencia o PayPal; W-9 o W-8BEN con **firma manual** (sin firma electrónica); datos de pago deben coincidir [HC master].

## 4. Cuentas múltiples y paso a financiada
- Cuentas de calificación **ilimitadas**; hasta **5 cuentas Master-level activas** (Master, Fast Track, Momentum Master en cualquier combinación); un solo perfil y un solo Rithmic User ID por trader; saldos, beneficios y drawdowns no se combinan. Crear varios perfiles o IDs no está permitido [HC, FAQ].
- Tras ≥3 pagos exitosos las cuentas pueden ser consideradas (a criterio de Bulenox) para una cuenta **financiada real** (consolida las Master positivas; aportación máxima por Master $2,500/$5,000/$10,000/$15,000 y total $30,000; el beneficio excedente se pierde) [HC funded]. Fast Track: revisión tras 3 pagos y 30 días de trading [FAQ].

## 5. Automatización, API y conducta
- **Permitido:** bots, algoritmos y copiadores; **solo herramientas creadas por el propio usuario y de uso personal exclusivo**; no comerciales/compartidas/alquiladas/públicas [FAQ]. Si se conecta a Rithmic mediante una **API de terceros o software compuesto: +$100 al mes** [HC qualification, FAQ].
- ToU, "ALGORITHMS AND AUTO TRADING": no abusar de los programas, "incluye … 'scalping' algorithms, DTC Protocol Bridge API or automated discretional trading … hundreds or thousand of rapid trades … reckless transactions in rough markets to benefit from lack of execution. If abuse is suspected, we reserve the right to refuse to claim any profit. … any third party algorithms must be approved from the Bulenox management team." [ToU]. Todas las ventas son finales [ToU, HC subscription].
- La revisión posterior al pase: "Bulenox verifica tu actividad de trading y confirma que la cuenta se completó conforme a las reglas" [HC master].
- **Plataformas:** Rithmic Paper Trading (gateway Chicago); R|Trader Pro y NinjaTrader 8 solo Windows; OCO de NinjaTrader es **local**: si se desconecta, la segunda pata puede no cancelarse y abrir una posición extra (Bulenox no se hace responsable) [HC connection].
- Datos: no profesional incluido; profesional $112/mes por bolsa [HC connection]. Comisiones por lado (MES/MNQ/M2K $0.61, MGC/MCL $0.76, M6E $0.50, MBT $2.76, MET $0.46); cuentan en el P&L, el drawdown y el DLL [PDF].
- Pagos de compra: tarjeta, PayPal, cripto; sin reembolsos; la cuenta caduca al final del acceso, sin cobros recurrentes [HC subscription].

## 6. Sin confirmar (ver `rules.UNKNOWN`)
Reinicio de Momentum y Fast Track · reinicio de Qualification para tamaños ≠ 50K · lock de +$100 durante la calificación · parámetros exactos del Momentum Master · **descuento del cupón `BULENOX`** (el usuario indica que siempre está activo; monto desconocido, no se aplica en ningún cálculo) · si el algoritmo propio requiere aprobación previa y si un Pi/VPS es aceptable · API de Rithmic (protocolo, costo exacto, requisitos) · reglas de la cuenta financiada real.
