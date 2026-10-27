# RESULTADOS_K1 — Costos: cuándo y cuánto se puede apagar

Martes 27-oct-2026 · BORRADOR. Fuentes: código de `golive/cerebro2-mgc-candidate` (leído con `git grep`; commit `2d45c71`), páginas públicas de Massive y de ProjectX (hoy), los totales de costos que dio Eric en el chat (**sin los estados de cuenta a la vista: SUPUESTO hasta verlos**), el motor de las Partes A/D (`resultados_K1_equilibrio.md`). Estados: MEDIDO (leí el código / corrí el motor), DOCUMENTADO (lo dice la página), SUPUESTO (dato de Eric no contrastado), DESCONOCIDO.

## 1. Resumen

1. **Ningún servicio de producción llama a un endpoint de acciones de Massive.** Los usos de Massive son `/futures/v1/contracts` (`execution/contracts.py:128`, usado por los tres schedulers), `/futures/v1/aggs` (`geometry_mgc_scheduler.py:684-689`, solo para el paper de MGC) y `list_futures_aggregates` (`combo2d_scheduler.py:175`). `list_aggs` (acciones/genérico) aparece únicamente en `data/loader.py:249`, un cargador legado de Polygon que ningún `Procfile` ejecuta (`paper_trading/runner.py` solo importa su tabla de `INSTRUMENT_SPECS`). El servicio legado `GLITCH` (`glitch_scheduler.py`) usa solo `yfinance`. ⇒ **Massive Stock se puede cancelar antes del 6-nov** con una verificación previa de 5 minutos en el panel de Massive (uso por producto en 30 días = 0). MEDIDO en el código; que la llave de Futures no dependa de la suscripción de Stock: DESCONOCIDO (se prueba cancelando al **fin del periodo**, no antes).
2. **Massive Futures ($29/mes, $348/año) no se puede cancelar hoy sin parche:** los tres schedulers exigen `MASSIVE_API_KEY` al arrancar (`require_env`) y `execution/contracts.py:30-35` lanza error **al importarse** si falta. Con un parche pequeño (K1-a: llave opcional en modo real + tolerar el fallo de contratos) el modo real queda sin Massive; lo que se pierde son las alertas de vencimiento y el nombre del contrato en los mensajes (informativos). El paper de MGC y COMBO2D sí lo usan (precio, barras diarias).
3. **Equilibrio de la cadena con los costos reales de Eric** (MODELADO; ruido de simulación ≈ ± 0.1 pp): con $714 (el heredado) 47.86 %; con **$640** (recurrente actual) **47.78 %**; con **$290** (Massive Futures sustituido) **47.44 %**; con **$245** 47.39 %. Cada $100 al año mueve el equilibrio ≈ 0.10 pp (pendiente ≈ $990 por punto de WR). El ahorro de $350/año equivale a 0.35 pp de WR.
4. **Con el WR medido (47.4 %) la cadena «hoy» sigue en ≈ −$50 a −$450 al año por cuenta según el costo** (−$446 con $640; −$96 con $290; −$51 con $245): bajar costos acerca la cadena al equilibrio, **no la vuelve positiva por sí sola**. Con finish-line + 728×3 sería +$479 / +$829 / +$874 (sujeto a Topstep y a parches no aplicados).
5. **Lo que no se puede apagar:** $49 por intento de Combine y $149 de activación (son el producto), y la API de ProjectX mientras haya una cuenta activa (la necesita el Pi).
6. **Falta el desglose por rubro de los $54/mes:** sin los estados de cuenta no sé cuánto de los $25 restantes es Railway, API de ProjectX u otra cosa, ni cuánto cuesta Massive Stock. Eric: pásame las líneas (o dime plan y fecha de renovación de cada una).

## 2. Tabla fecha × rubro × ahorro × condición

| fecha | rubro | ahorro (mensual / anual) | condición para apagarlo | estado |
|---|---|---|---|---|
| **antes del 6-nov-2026** (fecha que dio Eric) | **Massive Stock** (suscripción de acciones) | **DESCONOCIDO** (su precio no está en lo que tengo; los planes publicados de Futures van de $0 a $199) | (i) panel de Massive: 0 llamadas a productos de acciones en 30 días; (ii) cancelar para que **no renueve** y esperar a que termine el periodo pagado: si algo falla, se reactiva; (iii) código: `git grep` limpio (MEDIDO: ver resumen 1) | listo para decidir |
| desde hoy; **antes de la renovación de Futures (fecha: DESCONOCIDA, Eric)** | **Massive Futures** Starter | **$29 / $348** (Eric: ≈ $54 → ≈ $25 al mes sin él) | (a) parche K1-a aplicado y probado (llave opcional en modo real; contratos tolerantes); (b) historia larga ya descargada (K0: si se quiere 5–7 años, **comprar un mes de Developer $79 o Advanced $199, bajar y cancelar**, o usar Databento); (c) decidir qué pasa con el paper de MGC y COMBO2D (si se apagan, sin dependencia); (d) **N = 10 sesiones reales** de MES y MGC sin Massive y sin alertas rotas antes de cancelar (N es un juicio mío, SUPUESTO) | requiere parche |
| tras el PASE | cron de **GEOMETRY (MES)** en Railway | parte de ≈ $65/año de Railway (Parte J: A = $174 API + ≈ $65 Railway; el reparto por servicio: DESCONOCIDO) | Combine cerrada y sin otra Combine comprada (J2 3.1) | decisión de Eric |
| ya | servicios **legados** de Railway: `GLITCH` (`glitch_scheduler.py`, ORB MES en paper con `yfinance`) y `COMBO2D` (`combo2d_scheduler.py`) | ≤ ≈ $65/año en total si fueran todo el gasto de Railway (DESCONOCIDO por servicio) | confirmar en el panel que siguen corriendo y que no alimentan nada de decisión (no escriben señales al Pi: MEDIDO en el código) | por confirmar |
| al cerrar cada Combine | **API de ProjectX** $14.30 por cuenta y mes (Eric) | hasta **$14.30 / $171.6** por cuenta pausable | preguntar a Topstep: ¿se cobra por cuenta **activa** o por usuario?, ¿se puede pausar al cerrar la Combine?, ¿cuenta cuando la Combine ya pasó y la XFA aún no se activa? | DESCONOCIDO (ticket) |
| — | $49 por intento de Combine; $149 activación XFA | no apagables | son el producto; ya están dentro del motor (≈ 4 compras por XFA alcanzada, $345 por XFA con WR 50 %) | — |

**Sobre sustituir Massive Futures por ProjectX (lo que propone Eric):** técnicamente cabe (`activeContract` y `retrieveBars` dan contrato activo y precio casi en tiempo real; ver K0), pero **no recomiendo poner la llave de ProjectX en Railway**: esa llave opera cuentas (el Pi la guarda por esa razón), amplía la superficie de ataque y la regla de Topstep sobre servidores en la nube aplica a transmitir órdenes (el Pi existe por eso; si leer datos desde la nube está permitido: DESCONOCIDO). Dos alternativas, de menor a mayor esfuerzo: (1) **no sustituir**: en modo real el precio y el contrato los resuelve el Pi con ProjectX y los mensajes de Railway pierden solo el nombre del contrato y las alertas de vencimiento (que `check_contracts.py` en el Pi ya cubre bajo demanda); (2) que el **Pi publique en el Gist** un resumen (contrato activo, vencimiento, último precio) y Railway lo lea con el token que ya tiene. La alternativa (1) es la que cubre el parche K1-a.

## 3. Equilibrio de la cadena con los costos reales (`resultados_K1_equilibrio.md`)

MODELADO. Mismo motor que H1b/J5; slippage de entrada del Combine = 8 observaciones de MES (la 8.ª inferida = 0, **NO VERIFICADA**); XFA MGC 3×364; ruido de simulación ≈ ± $100 por celda y ± 0.1 pp en el equilibrio.

**Neto anual por cuenta ($) a WR 47.4 % / 50 %**

| costos al año | hoy (P0, 3×364) | + finish-line | + 728×3 | finish-line + 728×3 |
|---|---|---|---|---|
| $714 (heredado de la Parte D) | −520 / 2,165 | −167 / 2,628 | 8 / 3,655 | 405 / 4,180 |
| **$640** (recurrente actual, $54/mes) | **−446 / 2,239** | −93 / 2,702 | 82 / 3,729 | 479 / 4,254 |
| **$290** (Massive Futures sustituido, $25/mes) | **−96 / 2,589** | 257 / 3,052 | 432 / 4,079 | 829 / 4,604 |
| **$245** (base de la Parte J) | −51 / 2,634 | 302 / 3,097 | 477 / 4,124 | 874 / 4,649 |

**Equilibrio (WR de la etiqueta con neto anual = 0)**

| costos al año | hoy | + finish-line | + 728×3 | finish-line + 728×3 |
|---|---|---|---|---|
| $714 | 47.86 % | 47.50 % | 47.30 % | 47.03 % |
| **$640** | **47.78 %** | 47.43 % | 47.25 % | 46.98 % |
| **$290** | **47.44 %** | 47.10 % | 47.00 % | 46.74 % |
| $245 | 47.39 % | 47.05 % | 46.96 % | 46.71 % |

**Lectura sin adornos.** El WR medido (47.4 %, IC95 [41, 54]) cae justo en el equilibrio de «hoy» con $290 (47.44 %) y **por debajo** del equilibrio con $640 (47.78 %): con los costos actuales la cadena pierde dinero en el centro de la estimación; bajar a $290 la deja en ≈ 0 con signo incierto. La etiqueta de WR es la de H1 (con 728×3 no es comparable con el WR por sesión; ver `REPORTE_H1b.md` §5). Los costos reales no son una constante anual: la API de ProjectX corre por cuenta y mes; el motor la resta anual por simplicidad.

## 4. Parche K1-a (hecho, sin aplicar): Massive opcional en modo real — `k1_massive_opcional.patch`

NEEDS HUMAN REVIEW. Qué cambia: (1) `execution/contracts.py` ya **no lanza al importarse** sin llave; la exige al llamar (`_headers()`) y expone `have_key()`; (2) `geometry_scheduler.py` (MES) y `geometry_mgc_scheduler.py` dejan de exigir `MASSIVE_API_KEY` al arrancar **solo con `DRY_RUN=false`** (paper y COMBO2D la siguen exigiendo); (3) en modo real sin llave se **omite** la resolución del contrato y las alertas de vencimiento; y, **hallazgo aparte**, en el scheduler **MES** un fallo de Massive al resolver el contrato hacía `return` **también en modo real** (no se enviaba señal ese día): ahora en modo real solo avisa. Pruebas: 12 nuevas (`tests/test_k1_massive_optional.py`; subprocesos con el entorno sin llave); aplica **solo sobre la candidata de J1** (`git apply --check` OK) y sobre la pila J4: **695 pruebas verdes** (683 + 12), 0 fallos. Rama local: `golive/cerebro2-mgc-candidate-k1`.

**Lo que se pierde al cancelar Massive Futures en modo real:** el nombre del contrato en los mensajes y las **alertas de vencimiento de contrato** (checkpoints 10/5/2/1 días). Mitigación: `check_contracts.py` en el Pi (a demanda) y, si se quiere, que el Pi publique el contrato activo y su vencimiento en el Gist (no hecho).

**Calendario propuesto (juicio mío):** (1) revisión y aplicación del parche; (2) **10 sesiones reales de MES y MGC sin la llave de Massive en los dos servicios**, sin errores de arranque y con señales a tiempo; (3) recién entonces cancelar Massive Futures **al fin del periodo pagado**. Si se quiere historia larga, comprar **un mes** de Developer ($79) o Advanced ($199) **antes** de cancelar, o usar Databento (K0).
