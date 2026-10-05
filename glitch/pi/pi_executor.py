"""
Glitch — Pi Executor: ejecucion real de ordenes contra ProjectX (29-sep-2026)
================================================================================
Corre en el Raspberry Pi (nunca en Railway/VPS -- Topstep prohibe VPN/VPS
para transmitir ordenes, ver GLITCH_HANDOFF/estado_y_expectativas). Consume
la señal que scheduler/geometry_scheduler.py escribe al Gist compartido
cuando DRY_RUN=false (ver ORDER_FILE abajo y el cambio equivalente en ese
scheduler), coloca la orden real (bracket: entrada de mercado + TP limit +
SL stop, LAS TRES JUNTAS -- ver diseño mas abajo, nunca con una ventana sin
proteccion), monitorea hasta que se resuelve, y escribe el resultado al
MISMO historico (LOG_FILE = geometry_{producto}_log.json) que
geometry_scheduler.py ya usa para calcular intento/PASE/QUIEBRE -- sin
cambios ahi, la transicion de paper a real es transparente para esa logica.

ANTES de este archivo (ver reporte 29-sep-2026), las 8 funciones de este
modulo eran puro pseudocodigo (`raise NotImplementedError`) -- arrancarlo
tal cual habria fallado en el primer ciclo y mandado un error a Telegram
cada POLL_SECONDS indefinidamente. Esta version es real: si no hay nada que
hacer, sale en silencio (solo log); si hay una señal pero el gate de abajo
no esta satisfecho, avisa UNA vez por dia (no por ciclo) y no toca la red
del broker en absoluto.

>>> GATE DE SEGURIDAD (instruccion del usuario, 22-sep-2026) <<<
Este modulo se niega a colocar CUALQUIER orden real (incluso contra cuenta
de practica) a menos que AMBAS condiciones se cumplan:
  1. GLITCH_PI_PHASE3=si en el entorno (Fase 3: Combine pagado + Pi
     validado -- no exportar esta variable antes de eso).
  2. Existe pi/orderside_verified.json con un mapeo {"BUY_SIDE_INT": int,
     "SELL_SIDE_INT": int} -- el resultado de correr verify_orderside_demo.py
     (script aparte, todavia no escrito, tambien gateado por PHASE3) contra
     una cuenta Practice/Demo real. Deliberadamente NO se usa
     brokers.projectx.OrderSide para decidir compra/venta: ese enum
     (BID=0 # Sell, ASK=1 # Buy) contradice la documentacion oficial de
     ProjectX (0=Bid=Buy) y NUNCA se ha verificado contra una cuenta real
     -- es exactamente el bloqueante #1 sin resolver. Ver brokers/projectx.py,
     docstring de la clase OrderSide.
Sin ambas, run_once() se detiene ANTES de llamar authenticate() -- cero
llamadas de red al broker, cero riesgo, sea cual sea el estado del codigo.

DISEÑO DE EJECUCION -- entrada y proteccion SIEMPRE juntas: a diferencia de
un primer borrador de este modulo (autocritica durante la escritura, no
desplegado en ningun momento) que esperaba a confirmar el fill de la
entrada ANTES de colocar TP/SL, esta version coloca las 3 ordenes en el
MISMO ciclo (place_bracket_order), usando como referencia de precio el
ultimo dato real de mercado de ProjectX (client.get_recent_bars(), NO yfinance).
Esperar la confirmacion del fill antes de proteger la posicion deja una
ventana de exposicion sin SL -- inaceptable para dinero real, aunque sea
breve. El precio de entrada EXACTO (para el PnL final) se reconstruye al
cierre del ciclo consultando el fill real de la orden de entrada
(_lookup_order) -- si no se puede confirmar, se usa el precio de
referencia pre-trade, marcado explicitamente como estimado.

DISEÑO DE ESTADO (todo en el mismo Gist que ya usan los schedulers, via
execution/gist_store.py sin modificar):
  ORDER_FILE           -- orden_pendiente_{producto}.json (dict, "state").
                          Escrito por geometry_scheduler.py cuando
                          DRY_RUN=false, consumido (limpiado a {}) por este
                          modulo tras cerrar el ciclo. Ver ORDER_FILE_SCHEMA.
  PI_STATE_FILE        -- pi_position_{producto}.json (dict, "state").
                          Estado PROPIO de este modulo (geometry_scheduler.py
                          nunca lo toca): bracket actualmente en curso, si
                          lo hay -- permite reconcile_if_needed() retomar un
                          ciclo interrumpido a mitad de monitoreo usando el
                          broker como fuente de verdad (get_open_orders/
                          get_positions), no una estimacion de precio como
                          hace geometry_scheduler.py::_reconcile_pending_position.
  PI_BLOCK_NOTICE_FILE  -- pi_block_notice_{producto}.json (dict, "state").
                          Ultima fecha+razon en que se aviso un bloqueo, para
                          no repetir el mismo aviso cada POLL_SECONDS.
  LOG_FILE              -- geometry_{producto}_log.json (lista, "log").
                          MISMO archivo que geometry_scheduler.py -- la
                          continuidad de intento/Pass Rate depende de que
                          ambos escriban aqui con el mismo schema de entrada.

RIESGO RESIDUAL HONESTO (no resuelto, documentado en vez de escondido): si
el proceso muere en la ventana exacta entre place_bracket_order() colocando
las 3 ordenes reales y save_pi_state() persistiendo ese hecho al Gist,
PI_STATE_FILE queda vacio pero SI existe una posicion real abierta en el
broker. Mitigacion parcial: run_once() verifica, ANTES de colocar una orden
nueva, que no haya ya una posicion abierta en el contrato segun
get_positions() sin que PI_STATE_FILE la conozca -- si la encuentra, se
niega a operar y alerta en vez de apilar una segunda posicion encima. Esto
detecta el problema (evita duplicar exposicion) pero no lo resuelve solo
-- requeriria intervencion manual para reconciliar esa posicion huerfana
contra el historico.

ORDER_FILE_SCHEMA (lo que geometry_scheduler.py escribe, lo que este modulo
lee):
  {
    "date": "YYYY-MM-DD", "side": 1|-1, "direction": "LONG"|"SHORT",
    "ticker": str (yf_ticker, solo para logging), "product_code": str,
    "nc": int, "sl_ticks": int, "tp_ticks": int, "product": str (PRODUCT_KEY),
    "intento": int, "dry_run": False,
  }

CICLO DE run_once() (llamado cada POLL_SECONDS por main()):
  0. reconcile_if_needed() -- si PI_STATE_FILE muestra un bracket sin
     cerrar de un ciclo anterior, retomarlo ANTES de mirar si hay señal
     nueva.
  1. Sin señal pendiente (ORDER_FILE vacio) -- log y salir, sin Telegram.
  2. Señal pendiente pero gate no satisfecho -- avisar (rate-limited) y
     salir, sin tocar el broker.
  3. Señal pendiente y gate satisfecho -- verificar que no haya una
     posicion huerfana sin rastrear, authenticate, resolver contrato,
     tomar precio de referencia real, colocar bracket completo,
     notificar OPEN, monitorear hasta TP/SL/flatten de fin de sesion,
     calcular PnL, escribir a LOG_FILE, limpiar ORDER_FILE y
     PI_STATE_FILE, notificar CLOSE.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CHEQUEO UNIFICADO DE ARRANQUE -- mismo patron y mismo motivo que
# scheduler/geometry_scheduler.py y scheduler/combo2d_scheduler.py (ver
# execution/env_check.py). Nota: MASSIVE_API_KEY/POLYGON_API_KEY NO son
# necesarias aqui -- este modulo resuelve su propio contractId y su propio
# precio de referencia contra ProjectX, no contra Massive.
from execution.env_check import require_env

_PRODUCT_KEY_FOR_STARTUP_CHECK = os.getenv("GLITCH_PRODUCT", "MES")
require_env(
    ["TOPSTEP_USERNAME", "TOPSTEP_API_KEY", "TOPSTEP_ACCOUNT_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    f"PI-EXECUTOR-{_PRODUCT_KEY_FOR_STARTUP_CHECK}",
)

from brokers.projectx import OrderType, ProjectXClient, ProjectXCredentials, position_is_open, position_net
from execution.ct_logging import setup_ct_logging
from execution.gist_store import load_log as _gist_load_log
from execution.gist_store import load_log_strict as _gist_load_log_strict
from execution.gist_store import save_log_strict as _gist_save_log_strict
from execution.gist_store import load_state as _gist_load_state
from execution.gist_store import save_log as _gist_save_log
from execution.gist_store import save_state as _gist_save_state
from scheduler.telegram_bot import send
from strategies.geometry_pure import CANDIDATES

CT = ZoneInfo("America/Chicago")
log = setup_ct_logging("pi_executor")

# ── Config ────────────────────────────────────────────────────────────────
PRODUCT_KEY = _PRODUCT_KEY_FOR_STARTUP_CHECK
if PRODUCT_KEY not in CANDIDATES:
    log.error(f"FATAL: GLITCH_PRODUCT={PRODUCT_KEY!r} no esta en CANDIDATES "
              f"({sorted(CANDIDATES)}). Ver strategies/geometry_pure.py.")
    sys.exit(1)
CFG = CANDIDATES[PRODUCT_KEY]

ORDER_FILE = f"orden_pendiente_{PRODUCT_KEY.lower()}.json"
LOG_FILE = f"geometry_{PRODUCT_KEY.lower()}_log.json"  # MISMO archivo que geometry_scheduler.py
PI_STATE_FILE = f"pi_position_{PRODUCT_KEY.lower()}.json"
PI_BLOCK_NOTICE_FILE = f"pi_block_notice_{PRODUCT_KEY.lower()}.json"

PREFIX = f"S10GLITCH - PI EXECUTOR - {PRODUCT_KEY}"

# Gate de Fase 3 (22-sep-2026) -- ver docstring del modulo. No exportar
# GLITCH_PI_PHASE3=si hasta llegar genuinamente a Fase 3.
PHASE3_ENABLED = os.getenv("GLITCH_PI_PHASE3", "no").lower() == "si"
ORDERSIDE_VERIFIED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orderside_verified.json")

POLL_SECONDS = 120           # intervalo entre ciclos de main() -- "cada 2 minutos", ver reporte 29-sep-2026
POSITION_POLL_INTERVAL = 30  # segundos entre checks de TP/SL DENTRO de un ciclo con bracket abierto
HEARTBEAT_EVERY_POLLS = 10   # una linea de log cada N polls (10 x 30 s = ~5 min) mientras hay un bracket abierto.
                             # Sin esto el log queda MUDO horas durante un trade y pi/ops/watchdog.py (que vigila que
                             # el log siga creciendo) daria falsa alarma en cada posicion abierta.
FLATTEN_HOUR, FLATTEN_MINUTE = 14, 30  # mismo cierre de sesion RTH que geometry_scheduler.py (14:30 CT)


def _parse_hhmm(value: str, default_minutes: int) -> int:
    """'HH:MM' -> minutos desde medianoche; si no es valido, el default (nunca falla el arranque por esto)."""
    try:
        hh, mm = str(value).strip().split(":")
        h, m = int(hh), int(mm)
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except Exception:
        pass
    log.error(f"GLITCH_PI_ENTRY_DEADLINE_CT={value!r} no es HH:MM valido -- se usa el default")
    return default_minutes


# Hora limite (CT) para ENTRAR a mercado con una señal real (auditoria 04-oct-2026, hallazgo A3). Railway escribe la señal a
# las ~9:35 CT y el paper entra ~9:40; su reintento de entrada se rinde ~9:45-9:50, asi que el paper NUNCA entra mas tarde.
# Sin limite, un Pi que vuelve tarde (ya tuvo un reinicio inesperado) entraria a cualquier hora del mismo dia CT --
# a las 15:30 abre 40 contratos y los aplana al instante, a las 17:05 (reapertura Globex) igual. Fuera de la ventana la
# señal se descarta con aviso. Configurable (HH:MM CT) con GLITCH_PI_ENTRY_DEADLINE_CT.
ENTRY_DEADLINE_MINUTES = _parse_hhmm(os.getenv("GLITCH_PI_ENTRY_DEADLINE_CT", "10:00"), 10 * 60)

_FILL_PRICE_KEYS = ("filledPrice", "avgFillPrice", "averageFillPrice", "fillPrice", "price")


# ── Helpers de tiempo/estado ─────────────────────────────────────────────
def ct_now():
    return datetime.now(CT)


def utc_now_str():
    return datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M UTC")


def load_order_signal() -> dict:
    return _gist_load_state(ORDER_FILE)


def save_order_signal(d: dict):
    _gist_save_state(ORDER_FILE, d)


def load_pi_state() -> dict:
    return _gist_load_state(PI_STATE_FILE)


def save_pi_state(d: dict):
    _gist_save_state(PI_STATE_FILE, d)


# ── Idempotencia LOCAL: una señal real se ejecuta A LO MAS UNA VEZ (auditoria 04-oct-2026, hallazgo A1) ──────────
# gist_store._write_file TRAGA cualquier error de escritura (solo loguea). Si falla el PATCH que limpia la señal
# (`save_order_signal({})`), la señal sigue vigente, la cuenta ya esta plana y el siguiente ciclo (120 s) entraria
# OTRA VEZ: un segundo trade completo, o -con TP rechazado- un bucle abrir/aplanar cada ciclo. La unica defensa
# fiable es estado en el DISCO del Pi (no en el Gist): se escribe ANTES de la orden de entrada (semantica
# at-most-once: si el proceso muere entre el marcador y la orden, ese dia simplemente no se opera -- falla segura).
def _state_dir() -> str:
    return os.environ.get("GLITCH_PI_STATE_DIR") or os.path.expanduser("~")


def _executed_marker_path() -> str:
    return os.path.join(_state_dir(), f".glitch_pi_executed_{PRODUCT_KEY.lower()}.json")


def _is_test_signal(signal: dict) -> bool:
    """Señal de ENSAYO: `product` distinto del producto real del servicio (p. ej. "MEStest"). Escribe a su propio
    historial (geometry_mestest_log.json) y asi no contamina el real. Las de ensayo se exentan del marcador y de la
    ventana horaria (para poder repetir ensayos, tambien despues de las 14:30), pero _validate_signal las limita
    a <= TEST_SIGNAL_MAX_NC contratos."""
    return str(signal.get("product")) != PRODUCT_KEY


def _signal_already_claimed(signal: dict) -> bool:
    try:
        with open(_executed_marker_path()) as f:
            return json.load(f).get("date") == str(signal.get("date"))
    except FileNotFoundError:
        return False
    except ValueError as e:
        # Contenido corrupto (el marcador se escribe atomico, asi que no deberia pasar): ante la duda NO se opera
        # (mejor perder un dia que duplicar una entrada).
        log.error(f"marcador de ejecucion corrupto ({e}) -- se trata como YA EJECUTADA por seguridad")
        return True
    # Cualquier otro error de E/S (disco, permisos, directorio ilegible) se PROPAGA: run_once lo avisa como falla real
    # y la señal se conserva para reintentar, en vez de descartarla como si ya se hubiera ejecutado.


def _claim_signal(signal: dict) -> None:
    """Escribe (atomico + fsync) el marcador de que ESTA señal esta a punto de ejecutarse. Lanza si no puede
    escribirlo: sin marcador no se opera."""
    path = _executed_marker_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"date": str(signal.get("date")), "intento": signal.get("intento"), "claimed_at": utc_now_str()}, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ── 1. authenticate ──────────────────────────────────────────────────────
def authenticate() -> ProjectXClient:
    """Autentica contra ProjectX usando TOPSTEP_USERNAME/TOPSTEP_API_KEY del
    entorno (ya verificadas presentes por require_env al importar este
    modulo). Devuelve un cliente listo para usar."""
    creds = ProjectXCredentials.from_env()
    client = ProjectXClient(creds, verbose=False)
    client.authenticate()
    return client


# ── 2. ensure_fresh_token ────────────────────────────────────────────────
def ensure_fresh_token(client: ProjectXClient) -> None:
    """Revalida el JWT si expiro, re-autentica si hace falta -- delega en
    ProjectXClient.ensure_auth(), que ya implementa exactamente este
    patron (validate_session() -> authenticate() si es necesario)."""
    client.ensure_auth()


# Cuentas en las que el Pi NUNCA opera salvo que se permita explicitamente (auditoria 04-oct-2026, hallazgo A5).
# Default: la Combine 28197705 (dinero real: una ruptura la pierde). TOPSTEP_ACCOUNT_DENY="" (vacia) desactiva la lista;
# TOPSTEP_ACCOUNT_DENY="id1,id2" la reemplaza. Se necesita para la Fase 3 real, cuando SI se quiera operar la Combine.
DEFAULT_ACCOUNT_DENYLIST = "28197705"


def _account_denylist() -> set:
    raw = os.environ.get("TOPSTEP_ACCOUNT_DENY")
    raw = DEFAULT_ACCOUNT_DENYLIST if raw is None else raw
    return {x.strip() for x in raw.split(",") if x.strip()}


def _resolve_account_id(client: ProjectXClient) -> int:
    """Cuenta sobre la que opera el Pi: SIEMPRE la fijada explicitamente en TOPSTEP_ACCOUNT_ID (obligatoria, tambien
    la exige require_env al arrancar). Antes la variable era opcional: vacia/ausente con UNA sola cuenta activa operaba
    esa cuenta -- y si la Practice se liquida/reinicia deja de estar activa, esa cuenta unica seria la Combine.
    Se valida ademas contra las cuentas activas que ve la API (un id mal escrito o de una cuenta inactiva detiene el
    ciclo) y contra la lista de denegacion. Nunca se adivina por posicion ni por ser "la unica"."""
    pinned = os.getenv("TOPSTEP_ACCOUNT_ID", "").strip()
    if not pinned:
        raise RuntimeError(
            "TOPSTEP_ACCOUNT_ID esta vacia o no definida -- el Pi no opera sin una cuenta fijada explicitamente "
            "(nunca se adivina). Definirla en ~/.glitch_pi.env."
        )
    if pinned in _account_denylist():
        raise RuntimeError(
            f"TOPSTEP_ACCOUNT_ID={pinned!r} esta en la lista de denegacion (TOPSTEP_ACCOUNT_DENY) -- el Pi no opera "
            f"en esa cuenta. Si es intencional (Fase 3 real), definir TOPSTEP_ACCOUNT_DENY sin ese id."
        )
    accounts = client.get_accounts(only_active=True)
    ids = [a.get("id") for a in accounts]
    for a in accounts:
        if str(a.get("id")) == pinned:
            return a["id"]
    raise RuntimeError(
        f"TOPSTEP_ACCOUNT_ID={pinned!r} no esta entre las cuentas activas ({ids}) -- no se opera en ninguna otra "
        f"cuenta. Si la Practice se liquido o se reinicio, la cuenta nueva tiene OTRO id: actualizar la variable en "
        f"~/.glitch_pi.env y reiniciar el servicio."
    )


# ── 3. resolve_contract_id ───────────────────────────────────────────────
def resolve_contract_id(client: ProjectXClient, product_code: str) -> dict:
    """Generaliza ProjectXClient.find_mes_contract() (que hardcodea "MES")
    a cualquier product_code de CANDIDATES -- front month = vencimiento mas
    cercano entre los contratos disponibles cuyo nombre contiene el codigo."""
    contracts = client.get_contracts(live=False)
    matches = [c for c in contracts if product_code in c.get("name", "")]
    if not matches:
        raise RuntimeError(f"No se encontro contrato para product_code={product_code!r} en ProjectX.")
    matches.sort(key=lambda c: c.get("expirationDate", ""))
    return matches[0]


def _reference_price(client: ProjectXClient, contract_id) -> float:
    """Ultimo precio real de ProjectX (no yfinance) para calcular TP/SL
    ANTES de colocar la orden de entrada -- ver diseño del modulo (entrada
    y proteccion siempre juntas, sin ventana desnuda)."""
    bars = client.get_recent_bars(contract_id, minutes_back=15, live=False)
    if not bars:
        raise RuntimeError(f"Sin barras de los ultimos 15 min en ProjectX para contract_id={contract_id!r} "
                            f"(mercado cerrado o sin datos) -- no se puede fijar un precio de referencia, "
                            f"no se coloca la orden.")
    last = bars[-1]
    for k in ("close", "c", "last", "lastPrice"):
        if k in last and last[k] is not None:
            return float(last[k])
    raise RuntimeError(f"Barra de ProjectX sin campo de precio reconocible: {last!r}")


# ── Resolucion de OrderSide -- gateada, nunca adivinada ──────────────────
def _load_verified_side_map() -> Optional[dict]:
    """None si no existe o esta incompleto -- ver docstring del modulo,
    seccion GATE DE SEGURIDAD. Nunca cae en un default silencioso."""
    if not os.path.exists(ORDERSIDE_VERIFIED_PATH):
        return None
    try:
        with open(ORDERSIDE_VERIFIED_PATH) as f:
            data = json.load(f)
        if "BUY_SIDE_INT" not in data or "SELL_SIDE_INT" not in data:
            return None
        return data
    except Exception as e:
        log.error(f"orderside_verified.json presente pero ilegible -- {e}. Tratando como NO verificado.")
        return None


def _orderside_verified() -> bool:
    return PHASE3_ENABLED and _load_verified_side_map() is not None


def _resolve_side(direction: int, verified_map: dict) -> int:
    """direction: +1 (long -- comprar para entrar) / -1 (short -- vender
    para entrar). Devuelve el int de `side` que ProjectX espera, leido
    UNICAMENTE del mapeo verificado (nunca brokers.projectx.OrderSide
    directamente -- ver bloqueante #1, docstring del modulo)."""
    return verified_map["BUY_SIDE_INT"] if direction == 1 else verified_map["SELL_SIDE_INT"]


def _notify_blocked_once_per_day(reason: str):
    """Evita repetir el mismo aviso cada POLL_SECONDS (~cada 2 min) -- un
    aviso por dia calendario (por razon distinta) es suficiente para que el
    usuario se entere sin que Telegram se vuelva ruido. Ver hallazgo #1 del
    reporte 29-sep-2026 (la version pseudocodigo de este modulo habria
    mandado esto cada ciclo, indefinidamente)."""
    today_str = str(date.today())
    notice = _gist_load_state(PI_BLOCK_NOTICE_FILE)
    if notice.get("date") == today_str and notice.get("reason") == reason:
        return
    msg = f"{PREFIX}\nSTATUS: BLOCKED\n{reason}\n{utc_now_str()}"
    send(msg)
    log.warning(msg.replace("\n", " | "))
    _gist_save_state(PI_BLOCK_NOTICE_FILE, {"date": today_str, "reason": reason})


# ── Lectura de fill price real (best-effort, siempre marcado si es estimado) ──
def _extract_fill_price(order_record: dict) -> Optional[float]:
    """Primer precio POSITIVO y numerico entre las claves conocidas. Un `filledPrice` de 0 / nulo / no numerico (lo que
    puede traer una orden cancelada o sin ejecutar en un listado real) NO es un fill: aceptarlo daria un precio de
    salida 0 y un P&L absurdo (auditoria 04-oct-2026, P0-10: el FakeClient de los tests nunca emite ceros ni nulos)."""
    for k in _FILL_PRICE_KEYS:
        v = order_record.get(k)
        if v is None or isinstance(v, bool):
            continue
        try:
            price = float(v)
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return None


def _lookup_order(client: ProjectXClient, account_id: int, order_id) -> Optional[dict]:
    """Mejor esfuerzo: si la consulta falla devuelve None y el llamador cae a precios estimados (marcados como
    tales). Un fallo de lectura NO debe dejar el ciclo sin cerrar (ensayo del 4-oct-2026: Order/search dio 400
    y el estado quedo a medias con el bracket 'abierto')."""
    try:
        for o in client.get_orders(account_id, only_open=False):
            if (o.get("id") or o.get("orderId")) == order_id:
                return o
    except Exception as e:
        log.warning(f"_lookup_order({order_id}) fallo -- {e} -- se usaran precios estimados")
    return None


def _cancel_orders_verified(client: ProjectXClient, account_id: int, order_ids) -> list:
    """Cancela las ordenes dadas CON accountId y luego verifica contra el broker (searchOpen) que ya no estan.
    Devuelve los ids que SIGUEN abiertos (lista vacia = todo limpio). Nunca lanza: un fallo aqui no debe
    impedir el flatten ni el cierre del ciclo, pero tampoco se oculta."""
    for oid in order_ids:
        try:
            if not client.cancel_order(oid, account_id):
                log.warning(f"cancelar orden {oid}: la API no devolvio success (puede que ya no estuviera abierta)")
        except Exception as e:
            log.warning(f"cancelar orden {oid} fallo -- {e}")
    try:
        still = {o.get("id") or o.get("orderId") for o in client.get_open_orders(account_id)}
    except Exception as e:
        log.error(f"_cancel_orders_verified: no se pudo verificar ordenes abiertas -- {e}")
        return list(order_ids)
    return [oid for oid in order_ids if oid in still]


def _position_still_open(client: ProjectXClient, account_id: int, contract_id) -> bool:
    try:
        return any(p.get("contractId") == contract_id and position_is_open(p)
                   for p in client.get_positions(account_id))
    except Exception:
        return True   # sin poder confirmar, se asume abierta


FLATTEN_FILL_TOLERANCE_TICKS = 10   # holgura (slippage del cierre a mercado) fuera del rango [SL, TP] del bracket


def _find_flatten_fill(client: ProjectXClient, account_id: int, state: dict) -> Optional[float]:
    """Precio REAL del cierre por closeContract, o None si no se puede determinar con certeza (entonces el llamador cae
    al precio estimado, MARCADO como tal). Deliberadamente conservadora (auditoria 04-oct-2026, hallazgo A6): es mejor un
    estimado marcado que un precio "real" equivocado en el historial compartido.

    Candidato = orden de este contrato, posterior a la entrada (ids crecientes), que no es la entrada ni el TP/SL del
    bracket, con precio de fill. Se acepta SOLO si:
      * hay EXACTAMENTE un candidato (con varios -- p. ej. una orden manual posterior -- no se adivina cual cerro), y
      * su precio cae dentro del rango del bracket +- FLATTEN_FILL_TOLERANCE_TICKS (como ni el TP ni el SL se
        ejecutaron, el cierre de las 14:30 ocurre entre ellos; un precio muy fuera de rango es otra operacion).
    Mejor esfuerzo: nunca lanza."""
    try:
        exclude = {state["entry_order_id"], state["tp_order_id"], state["sl_order_id"]}
        cands = [o for o in client.get_orders(account_id, only_open=False)
                 if o.get("contractId") == state["contract_id"]
                 and isinstance(o.get("id"), int) and not isinstance(o.get("id"), bool)
                 and o["id"] > state["entry_order_id"]
                 and o["id"] not in exclude and _extract_fill_price(o) is not None]
        if len(cands) != 1:
            if cands:
                log.warning(f"_find_flatten_fill: {len(cands)} ordenes candidatas -- ambiguo, se usara precio estimado")
            return None
        price = _extract_fill_price(cands[0])
        slack = FLATTEN_FILL_TOLERANCE_TICKS * CFG.spec.tick_size
        lo = min(state["tp_price"], state["sl_price"]) - slack
        hi = max(state["tp_price"], state["sl_price"]) + slack
        if not (lo <= price <= hi):
            log.warning(f"_find_flatten_fill: fill {price} fuera del rango del bracket [{lo}, {hi}] -- "
                        f"no parece el cierre de este ciclo, se usara precio estimado")
            return None
        return price
    except Exception as e:
        log.warning(f"_find_flatten_fill fallo -- {e} -- se usara precio estimado")
        return None


def _has_untracked_position(client: ProjectXClient, account_id: int, contract_id) -> bool:
    """Guardia contra el riesgo residual documentado arriba (crash entre
    colocar el bracket y guardar PI_STATE_FILE): si el broker ya muestra
    una posicion abierta en este contrato y PI_STATE_FILE no la conoce, no
    se coloca una orden nueva encima."""
    try:
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id and position_is_open(p):
                return True
    except Exception as e:
        log.error(f"_has_untracked_position: get_positions fallo -- {e} -- "
                  f"no se puede confirmar que la cuenta este plana, absteniendose por seguridad.")
        return True
    return False


# ── Verificacion post-resolucion (auditoria 04-oct-2026, hallazgo A2) ───────────────────────────────────────────
# TP y SL son DOS ordenes sueltas (no un OCO del broker). Detectar "una pata desaparecio => se lleno" es una
# INFERENCIA: tambien desaparecen por cancelacion manual, liquidacion por MLL, un error de lectura de la API, o
# porque se llenaron AMBAS casi a la vez (posicion invertida). Antes de dar un ciclo por cerrado (lo que borra el
# estado y la señal y deja de monitorear) se comprueba contra el broker que la cuenta quedo plana y sin ordenes
# huerfanas -- y si no, se cierra y se avisa en vez de seguir como si nada.
CONFIRM_GONE_READS = 2     # lecturas ADICIONALES a la del poll que deben seguir viendo ambas patas ausentes
CONFIRM_GONE_SLEEP = 3     # segundos entre esas lecturas


def _orders_really_gone(client: ProjectXClient, account_id: int, tp_id, sl_id) -> bool:
    """True solo si TP y SL siguen AUSENTES en CONFIRM_GONE_READS lecturas consecutivas mas. Una lectura que los
    muestre abiertos, o que falle, devuelve False: no se dan por perdidas."""
    for _ in range(CONFIRM_GONE_READS):
        time.sleep(CONFIRM_GONE_SLEEP)
        try:
            ids = {o.get("id") or o.get("orderId") for o in client.get_open_orders(account_id)}
        except Exception as e:
            log.warning(f"_orders_really_gone: lectura fallo ({e}) -- no se dan por perdidas las ordenes")
            return False
        if tp_id in ids or sl_id in ids:
            return False
    return True


def _confirm_flat(client: ProjectXClient, account_id: int, contract_id) -> Optional[bool]:
    """True = plana en este contrato, False = hay posicion abierta, None = no se pudo leer."""
    try:
        return not any(p.get("contractId") == contract_id and position_is_open(p)
                       for p in client.get_positions(account_id))
    except Exception as e:
        log.warning(f"_confirm_flat: get_positions fallo -- {e}")
        return None


def _verify_resolution(client: ProjectXClient, account_id: int, contract_id, outcome: dict, leftover=None) -> dict:
    """Se llama cuando el bracket parece resuelto (TP / SL / ambas patas ausentes). Devuelve `outcome` con banderas:
      orphan_orders       -- ids de ordenes de salida que SIGUEN abiertas (un stop huerfano abriria una posicion nueva)
      position_forced_flat-- la cuenta NO estaba plana al resolverse (reversion/parcial/cancelacion manual) y se cerro
      flatten_failed      -- no estaba plana y NO se pudo cerrar: puede haber una posicion abierta sin proteccion
      flat_unverified     -- no se pudo leer la posicion para confirmar"""
    outcome = dict(outcome)
    if leftover:
        outcome["orphan_orders"] = list(leftover)
        send(f"{PREFIX}\nSTATUS: ALERTA\nTras resolverse el bracket ({outcome['result']}) siguen ABIERTAS las ordenes "
             f"{list(leftover)} en {contract_id} -- cancelarlas MANUALMENTE en TopstepX (un stop/limite huerfano "
             f"abriria una posicion nueva al tocarse).\n{utc_now_str()}")
    flat = _confirm_flat(client, account_id, contract_id)
    if flat is False:
        try:
            client.close_contract(account_id, contract_id)
        except Exception as e:
            log.error(f"_verify_resolution: closeContract fallo -- {e}")
        if _confirm_flat(client, account_id, contract_id) is True:
            outcome["position_forced_flat"] = True
            send(f"{PREFIX}\nSTATUS: ALERTA\nAl resolverse el bracket ({outcome['result']}) la cuenta NO estaba plana en "
                 f"{contract_id} (posicion invertida, parcial o cancelacion manual). El Pi la CERRO automaticamente. "
                 f"Revisa el historial en TopstepX: el P&L del registro es el del bracket, no incluye ese cierre.\n"
                 f"{utc_now_str()}")
        else:
            outcome["flatten_failed"] = True
            send(f"{PREFIX}\nSTATUS: ALERTA\nAl resolverse el bracket ({outcome['result']}) la cuenta NO esta plana en "
                 f"{contract_id} y el Pi NO pudo cerrarla -- CERRARLA MANUALMENTE en TopstepX AHORA.\n{utc_now_str()}")
    elif flat is None:
        outcome["flat_unverified"] = True
        send(f"{PREFIX}\nSTATUS: ALERTA\nSe resolvio el bracket ({outcome['result']}) pero no se pudo confirmar que "
             f"la cuenta quedo plana en {contract_id} -- verificalo en TopstepX.\n{utc_now_str()}")
    return outcome


# ── Confirmacion del fill de la entrada (auditoria 04-oct-2026, hallazgo M1) ─────────────────────────────────
# place_bracket_order coloca entrada + TP + SL SIN esperar el fill (a proposito: nunca hay una ventana desnuda). Si la
# entrada queda SIN ejecutarse (halt, rechazo posterior), los exits quedan sin posicion y el TP/SL, al tocarse, abririan
# una posicion CONTRARIA. Despues de colocarlos se comprueba, contra el broker, que la posicion existe.
ENTRY_CONFIRM_ATTEMPTS = 5
ENTRY_CONFIRM_SLEEP = 3   # segundos -> ~12 s de espera maxima


def _observed_size(client: ProjectXClient, account_id: int, contract_id) -> Optional[int]:
    """Tamano absoluto de la posicion abierta en el contrato; 0 = plana; None = no se pudo leer."""
    try:
        total = 0
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id and position_is_open(p):
                total += abs(position_net(p)) or 1    # forma no reconocida pero listada como abierta: cuenta como presente
        return total
    except Exception as e:
        log.warning(f"_observed_size: get_positions fallo -- {e}")
        return None


def _confirm_entry_filled(client: ProjectXClient, account_id: int, contract_id, size: int) -> tuple:
    """(tamano_observado, se_pudo_leer). Reintenta hasta ENTRY_CONFIRM_ATTEMPTS veces; sale en cuanto ve `size`."""
    seen, readable = 0, False
    for i in range(ENTRY_CONFIRM_ATTEMPTS):
        obs = _observed_size(client, account_id, contract_id)
        if obs is not None:
            readable, seen = True, obs
            if seen >= size:
                return seen, True
        if i < ENTRY_CONFIRM_ATTEMPTS - 1:
            time.sleep(ENTRY_CONFIRM_SLEEP)
    return seen, readable


def _abort_unfilled_entry(client: ProjectXClient, account_id: int, contract_id, bracket: dict) -> None:
    """La entrada NO aparecio como posicion: cancela entrada/TP/SL, cierra por si el fill llego justo ahora, limpia
    estado y señal (ya reclamada, no se reintenta) y avisa."""
    ids = [bracket["entry_order_id"], bracket["tp_order_id"], bracket["sl_order_id"]]
    leftover = _cancel_orders_verified(client, account_id, ids)
    try:
        client.close_contract(account_id, contract_id)       # si no hay posicion devuelve success=false: se ignora
    except Exception as e:
        log.info(f"_abort_unfilled_entry: closeContract respondio error ({e}) -- esperado si la cuenta esta plana")
    still_open = _position_still_open(client, account_id, contract_id)
    save_pi_state({})
    save_order_signal({})
    tail = ""
    if leftover:
        tail += f" Siguen ABIERTAS las ordenes {leftover}: cancelarlas MANUALMENTE en TopstepX."
    if still_open:
        tail += " Hay una posicion abierta que el Pi NO pudo cerrar: CERRARLA MANUALMENTE en TopstepX AHORA."
    send(f"{PREFIX}\nSTATUS: ALERTA\nLa orden de entrada no aparecio como posicion en "
         f"{ENTRY_CONFIRM_ATTEMPTS * ENTRY_CONFIRM_SLEEP} s (no se ejecuto). Se cancelaron entrada/TP/SL y se descarto la "
         f"señal (no se reintenta).{tail}\n{utc_now_str()}")


# ── 4. place_bracket_order ───────────────────────────────────────────────
class BracketPlacementFailed(Exception):
    """La entrada se ejecuto pero TP o SL no se pudieron colocar. Ya se intento aplanar; `flatten_error` es
    None si el flatten funciono."""

    def __init__(self, reason: str, flatten_error=None):
        super().__init__(reason)
        self.reason = reason
        self.flatten_error = flatten_error


def _round_to_tick(price: float) -> float:
    tick = CFG.spec.tick_size
    return round(round(price / tick) * tick, 10)


def place_bracket_order(client: ProjectXClient, account_id: int, contract_id,
                         direction: int, size: int, tp_price: float, sl_price: float,
                         verified_map: dict) -> dict:
    """
    Coloca entrada de mercado + TP (limit) + SL (stop) COMO UN SOLO PASO --
    ver "DISEÑO DE EJECUCION" en el docstring del modulo: nunca hay una
    entrada sin su proteccion ya colocada. Similar en espiritu a
    ProjectXClient.execute_orb_bracket(), pero SIN usar ese metodo: bakea
    brokers.projectx.OrderSide directamente, que es exactamente el mapeo
    sin verificar (bloqueante #1). Usa _resolve_side() con el mapeo YA
    verificado (pasado explicitamente -- el llamador ya confirmo el gate
    antes de invocar esto).
    """
    entry_side = _resolve_side(direction, verified_map)
    exit_side = _resolve_side(-direction, verified_map)

    entry_id = client.place_order(account_id, contract_id, OrderType.MARKET, entry_side, size)
    placed_exits = []
    try:
        tp_id = client.place_order(account_id, contract_id, OrderType.LIMIT, exit_side, size, price=tp_price)
        placed_exits.append(tp_id)
        sl_id = client.place_order(account_id, contract_id, OrderType.STOP, exit_side, size, stop_price=sl_price)
    except Exception as e:
        # La entrada de mercado YA se ejecuto: si una de las dos salidas falla, hay una posicion SIN
        # proteccion. Nunca se deja asi -- se cancela lo que haya quedado y se aplana con closeContract
        # (independiente del lado). Hallazgo del ensayo del 4-oct-2026: el TP se rechazo ("Invalid limit
        # price") y la entrada quedo abierta y desnuda.
        for oid in placed_exits:
            try:
                client.cancel_order(oid, account_id)
            except Exception as ce:
                log.error(f"place_bracket_order: no se pudo cancelar la orden {oid} tras el fallo -- {ce}")
        flatten_error = None
        try:
            client.close_contract(account_id, contract_id)
        except Exception as fe:
            flatten_error = str(fe)
            log.error(f"place_bracket_order: flatten de emergencia fallo -- {fe}")
        raise BracketPlacementFailed(str(e), flatten_error) from e

    return {"entry_order_id": entry_id, "tp_order_id": tp_id, "sl_order_id": sl_id}


# ── 5. poll_position_until_closed ────────────────────────────────────────
def poll_position_until_closed(client: ProjectXClient, account_id: int, contract_id,
                                tp_order_id, sl_order_id, tp_price: float, sl_price: float,
                                poll_interval: int = POSITION_POLL_INTERVAL,
                                flatten_hour: int = FLATTEN_HOUR,
                                flatten_minute: int = FLATTEN_MINUTE) -> dict:
    """
    Monitorea el bracket hasta que se resuelve: TP lleno (cancela SL), SL
    lleno (cancela TP), o cierre forzado de sesion (cancela ambos y
    flattenea) -- mismo umbral de tiempo (14:30 CT) que el flatten
    obligatorio de geometry_scheduler.py, para que el comportamiento en
    vivo no se desvie del ya validado en paper.

    Devuelve {"result": "TP"|"SL"|"FLATTEN"|"UNKNOWN", "exit_price": float|None,
    "exit_price_estimated": bool} -- el precio de salida se intenta leer del
    fill REAL de la orden que se ejecuto; si no se puede confirmar, cae al
    precio objetivo (tp_price/sl_price) marcado como estimado, nunca sin
    marcar.
    """
    polls = 0
    while True:
        now = ct_now()
        if now.hour * 60 + now.minute >= flatten_hour * 60 + flatten_minute:
            leftover = _cancel_orders_verified(client, account_id, [tp_order_id, sl_order_id])
            if leftover:
                send(f"{PREFIX}\nSTATUS: ALERTA\nTras el cierre de sesion siguen ABIERTAS las ordenes {leftover} "
                     f"en {contract_id} -- cancelarlas MANUALMENTE en TopstepX.\n{utc_now_str()}")
            # closeContract (POST /api/Position/closeContract) NO depende de que lado es compra/venta --
            # a diferencia de client.flatten_position(), que decide el lado con brokers.projectx.OrderSide
            # (el enum SIN verificar, bloqueante #1) y lee `netPos` (campo tampoco verificado): con el enum
            # invertido, "flatten" de un LONG compraria MAS en vez de cerrar. Ver pi/ARCHITECTURE.md.
            flatten_failed = False
            try:
                client.close_contract(account_id, contract_id)
            except Exception as e:
                # closeContract devuelve success=false si NO hay posicion que cerrar (p. ej. ya se cerro a mano
                # o en un intento anterior): eso no es un fallo. Solo es fallo si la posicion sigue abierta.
                if not _position_still_open(client, account_id, contract_id):
                    log.info(f"closeContract respondio error ({e}) pero la cuenta esta plana en {contract_id} -- ok")
                    return {"result": "FLATTEN", "exit_price": None, "exit_price_estimated": True}
                flatten_failed = True
                log.error(f"poll_position_until_closed: flatten de fin de sesion fallo -- {e}")
                send(f"{PREFIX}\nSTATUS: ALERTA\n"
                     f"El flatten de fin de sesion FALLO ({e}). La posicion en {contract_id} puede seguir "
                     f"ABIERTA -- cerrarla MANUALMENTE en TopstepX ahora (Topstep exige estar plano antes de "
                     f"las 3:10 PM CT).\n{utc_now_str()}")
            outcome = {"result": "FLATTEN", "exit_price": None, "exit_price_estimated": True}
            if flatten_failed:
                outcome["flatten_failed"] = True
            return outcome

        try:
            open_ids = {o.get("id") or o.get("orderId") for o in client.get_open_orders(account_id)}
        except Exception as e:
            log.error(f"poll_position_until_closed: get_open_orders fallo -- {e} -- reintentando")
            time.sleep(poll_interval)
            continue

        tp_open, sl_open = tp_order_id in open_ids, sl_order_id in open_ids

        if not tp_open and sl_open:
            leftover = _cancel_orders_verified(client, account_id, [sl_order_id])
            rec = _lookup_order(client, account_id, tp_order_id)
            price = _extract_fill_price(rec) if rec else None
            return _verify_resolution(
                client, account_id, contract_id,
                {"result": "TP", "exit_price": price if price is not None else tp_price,
                 "exit_price_estimated": price is None}, leftover)

        if tp_open and not sl_open:
            leftover = _cancel_orders_verified(client, account_id, [tp_order_id])
            rec = _lookup_order(client, account_id, sl_order_id)
            price = _extract_fill_price(rec) if rec else None
            return _verify_resolution(
                client, account_id, contract_id,
                {"result": "SL", "exit_price": price if price is not None else sl_price,
                 "exit_price_estimated": price is None}, leftover)

        if not tp_open and not sl_open:
            # Ambas patas ausentes. Puede ser: cierre manual, liquidacion por MLL, ambas ejecutadas casi a la vez
            # (posicion INVERTIDA), o un error de lectura. NO se puede dar el ciclo por cerrado sin comprobarlo
            # contra el broker (auditoria 04-oct-2026, A2): primero se re-lee para descartar un glitch transitorio,
            # luego se verifica que la cuenta este plana.
            if not _orders_really_gone(client, account_id, tp_order_id, sl_order_id):
                time.sleep(poll_interval)
                continue
            if _confirm_flat(client, account_id, contract_id) is None:
                log.warning("poll_position_until_closed: ambas patas ausentes pero no se pudo leer la posicion -- "
                            "se sigue monitoreando (no se finaliza a ciegas)")
                time.sleep(poll_interval)
                continue
            return _verify_resolution(client, account_id, contract_id,
                                       {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True}, None)

        polls += 1
        if polls % HEARTBEAT_EVERY_POLLS == 0:
            log.info(f"[{now.strftime('%H:%M')} CT] bracket abierto (heartbeat): TP y SL siguen en el libro, "
                     f"{polls} polls sin resolverse")
        time.sleep(poll_interval)


def _compute_pnl(side: int, entry_price: float, exit_price: float, nc: int) -> float:
    return (exit_price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * nc


# ── 6. reconcile_if_needed ───────────────────────────────────────────────
def reconcile_if_needed():
    """
    Si PI_STATE_FILE muestra un bracket que no llego a cerrarse (el proceso
    murio a mitad de poll_position_until_closed), lo retoma usando el
    broker como fuente de verdad -- a diferencia de
    geometry_scheduler.py::_reconcile_pending_position (que tiene que
    ADIVINAR el resultado comparando el precio actual contra TP/SL porque
    nunca hubo una posicion real que consultar), aqui se pregunta
    directamente al broker (get_open_orders) que paso.
    """
    state = load_pi_state()
    if not state:
        return
    if state.get("phase") != "bracket_open":
        log.error(f"reconcile_if_needed: PI_STATE_FILE con phase desconocida {state.get('phase')!r} -- "
                  f"revision manual requerida, no se toca.")
        return

    client = authenticate()
    account_id = state.get("account_id") or _resolve_account_id(client)
    outcome = poll_position_until_closed(
        client, account_id, state["contract_id"], state["tp_order_id"], state["sl_order_id"],
        state["tp_price"], state["sl_price"],
    )
    _finalize_cycle(client, account_id, state, outcome)


def _finalize_cycle(client: ProjectXClient, account_id: int, state: dict, outcome: dict):
    signal = state["signal"]

    entry_price = state["entry_price"]
    entry_estimated = True
    rec = _lookup_order(client, account_id, state["entry_order_id"])
    fill = _extract_fill_price(rec) if rec else None
    if fill is not None:
        entry_price, entry_estimated = fill, False

    outcome = dict(outcome)
    if outcome["result"] == "FLATTEN" and outcome["exit_price"] is None and not outcome.get("flatten_failed"):
        flat_fill = _find_flatten_fill(client, account_id, state)
        if flat_fill is not None:
            outcome["exit_price"], outcome["exit_price_estimated"] = flat_fill, False

    exit_price = outcome["exit_price"] if outcome["exit_price"] is not None else entry_price
    pnl = _compute_pnl(signal["side"], entry_price, exit_price, signal["nc"])
    entry = {
        "date": signal["date"], "signal": True, "side": signal["side"],
        "direction": signal["direction"], "entry": entry_price, "exit": exit_price,
        "result": outcome["result"], "pnl": round(pnl, 2),
        "sl_ticks": signal["sl_ticks"], "tp_ticks": signal["tp_ticks"], "nc": signal["nc"],
        "dry_run": False, "product": signal["product"], "intento": signal["intento"],
        "entry_price_estimated": entry_estimated,
        "exit_price_estimated": outcome.get("exit_price_estimated", False),
    }
    # Banderas que SOLO aparecen cuando ocurren -- cada una pide revision manual de ese dia
    for flag in ("flatten_failed", "position_forced_flat", "flat_unverified"):
        if outcome.get(flag):
            entry[flag] = True
    if signal.get("nc_signal") is not None:
        entry["nc_signal"] = signal["nc_signal"]     # contratos de la señal (paper); "nc" = los operados
    if outcome.get("orphan_orders"):
        entry["orphan_orders"] = outcome["orphan_orders"]
    if outcome["result"] == "UNKNOWN":
        entry["needs_review"] = True
    append_to_historic_log(signal["product"], entry)
    save_order_signal({})
    save_pi_state({})

    msg = (f"{PREFIX}\n[CLOSE] [{outcome['result']}]\n"
           f"{signal['direction']}: {entry_price:,.4f} → {exit_price:,.4f}\n"
           f"PnL: ${pnl:+,.2f}  |  Contracts: {_nc_label(signal)}\n"
           f"Intento #{signal['intento']}\n"
           + ("ATENCION: resultado NO determinado -- ambas patas desaparecieron (cierre manual, liquidacion por MLL "
              "o error de lectura). El PnL $0.00 de arriba NO es real: revisar el P&L en TopstepX. "
              "Este dia queda marcado needs_review y fuera del WR.\n" if outcome["result"] == "UNKNOWN" else "")
           + ("(precio de entrada estimado -- no confirmado por el broker)\n" if entry_estimated else "")
           + ("(precio de salida estimado -- no confirmado por el broker)\n" if entry["exit_price_estimated"] else "")
           + utc_now_str())
    send(msg)
    log.info(msg.replace("\n", " | "))


# ── 7. append_to_historic_log ────────────────────────────────────────────
HISTORY_WRITE_ATTEMPTS = 3
HISTORY_RETRY_SLEEP = 2   # segundos entre intentos


def _spool_path(product_key: str) -> str:
    return os.path.join(_state_dir(), f".glitch_pi_unsynced_log_{product_key.lower()}.jsonl")


def _spool_read(path: str) -> list:
    try:
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
    except Exception as e:
        log.error(f"spool del historial ilegible ({e}) -- se ignora y se conserva el archivo para revision manual")
        return []


def _spool_append(path: str, entry: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _entry_present(paper_log: list, entry: dict) -> bool:
    """Evita duplicar una entrada si un intento anterior SI escribio (p. ej. el PATCH llego pero la respuesta no)."""
    keys = ("date", "result", "entry", "exit", "intento", "nc", "side")
    return any(all(e.get(k) == entry.get(k) for k in keys) and e.get("dry_run") is False for e in paper_log)


def append_to_historic_log(product_key: str, entry: dict) -> None:
    """
    Escribe al MISMO archivo (geometry_{producto}_log.json) que geometry_scheduler.py -- misma forma de entrada que ese
    scheduler ya produce en modo paper, para que _current_intento()/_attempt_pnl()/etc. (definidas ahi) sigan funcionando
    sin cambios sobre un historico mixto paper+real.

    NUNCA sobrescribe el historial a ciegas (auditoria 04-oct-2026, A4): antes, si la LECTURA fallaba, load_log devolvia []
    y el PATCH reemplazaba TODO el historial por esta sola entrada. Ahora: lectura estricta, 3 intentos, sin duplicar;
    si no se logra, la entrada se guarda en un spool LOCAL (se fusiona en el siguiente cierre exitoso) y se avisa por
    Telegram con la entrada completa. El historial del Gist queda intacto.
    """
    filename = f"geometry_{product_key.lower()}_log.json"
    spool = _spool_path(product_key)
    last_err = None
    for attempt in range(HISTORY_WRITE_ATTEMPTS):
        try:
            paper_log = _gist_load_log_strict(filename)
            changed = False
            for e in _spool_read(spool) + [entry]:
                if not _entry_present(paper_log, e):
                    paper_log.append(e)
                    changed = True
            if changed:
                _gist_save_log_strict(filename, paper_log)
            if os.path.exists(spool):
                os.remove(spool)
            return
        except Exception as e:
            last_err = e
            log.warning(f"append_to_historic_log intento {attempt + 1}/{HISTORY_WRITE_ATTEMPTS} fallo -- {e}")
            if attempt < HISTORY_WRITE_ATTEMPTS - 1:
                time.sleep(HISTORY_RETRY_SLEEP)

    spooled = True
    try:
        _spool_append(spool, entry)
    except Exception as e:
        spooled = False
        log.error(f"append_to_historic_log: tampoco se pudo escribir el spool local -- {e}")
    send(f"{PREFIX}\nSTATUS: ALERTA\nNo se pudo escribir el historial en el Gist tras {HISTORY_WRITE_ATTEMPTS} intentos "
         f"({last_err}). El historial NO se sobrescribio. "
         + ("La entrada quedo en el spool local del Pi y se fusionara en el siguiente cierre exitoso. "
            if spooled else "TAMPOCO se pudo guardar en el Pi: copiar esta entrada a mano. ")
         + f"Entrada: {json.dumps(entry, default=str)}\n{utc_now_str()}")


# ── 8. run_once / main ───────────────────────────────────────────────────
def _signal_is_current(signal: dict) -> bool:
    """Una señal solo se ejecuta el MISMO dia (CT) en que se genero: la estrategia es intradia y se aplana a las
    14:30 CT, asi que una señal de un dia anterior ya no describe nada operable.

    * Señal de un dia ANTERIOR: se DESCARTA (se limpia ORDER_FILE y se avisa por Telegram). Si no se limpiara,
      el scheduler de Railway se niega a escribir la señal nueva mientras haya una sin consumir -- una señal
      vieja atascada bloquearia todos los dias siguientes.
    * Fecha ausente, ilegible o FUTURA: no se ejecuta ni se limpia -- algo esta mal y requiere ojos humanos
      (aviso limitado a uno por dia).
    Devuelve True solo si la señal es de hoy."""
    today = ct_now().date().isoformat()
    sig_date = str(signal.get("date", ""))
    if sig_date == today:
        return True
    try:
        date.fromisoformat(sig_date)
        parsable = True
    except ValueError:
        parsable = False
    if parsable and sig_date < today:
        msg = (f"{PREFIX}\nSTATUS: SEÑAL VIEJA DESCARTADA\n"
               f"Habia una señal sin consumir del {sig_date} ({signal.get('direction', '?')}, "
               f"{signal.get('nc', '?')} contratos); hoy es {today} (CT). No se ejecuta -- la estrategia es "
               f"intradia -- y se limpia para no bloquear al scheduler.\n{utc_now_str()}")
        send(msg)
        log.warning(msg.replace("\n", " | "))
        save_order_signal({})
        return False
    _notify_blocked_once_per_day(
        f"La señal pendiente trae una fecha que no es valida ni anterior a hoy ({sig_date!r}, hoy es {today} CT) "
        f"-- no se ejecuta ni se limpia. Requiere revision manual."
    )
    return False


# Una señal es DATOS que llegan por el Gist (cualquiera con el token del Gist, o un bug de Railway, podria escribir
# `nc=400`). El Pi ejecutaba `signal["nc"]` crudo (auditoria 04-oct-2026, hallazgo A7). Se valida contra la config LOCAL
# como COTA SUPERIOR -- no igualdad -- para no romper las señales de ensayo (mas chicas) ni futuros ajustes a la baja.
TEST_SIGNAL_MAX_NC = 2     # las señales de ensayo (product != GLITCH_PRODUCT) no pueden pasar de 2 contratos
SIGNAL_TICKS_MAX_FACTOR = 4  # sl/tp en ticks: 1 .. 4x lo configurado


# Tope LOCAL de contratos (GLITCH_PI_NC_MAX). Motivo: la cuenta Practice (150K) tiene margen de MLL de ~$4,474 y un stop
# de 40 contratos cuesta -$5,000 (la liquida, y ese dia se pierde del historial). El tope solo REDUCE el tamaño: la
# señal (lado, hora, SL/TP en ticks) no cambia, asi que el resultado por trade en TICKS es identico al de paper.
# Sin la variable: sin tope (comportamiento anterior). Valor invalido: se usa 1 contrato (falla chico, con log fuerte).
def _parse_nc_cap(raw: Optional[str]) -> Optional[int]:
    if raw is None or not raw.strip():
        return None
    try:
        v = int(raw.strip())
    except ValueError:
        v = 0
    if v < 1:
        log.error(f"GLITCH_PI_NC_MAX={raw!r} no es un entero >= 1 -- se usa 1 contrato por seguridad. Corregir el env.")
        return 1
    return v


NC_MAX = _parse_nc_cap(os.getenv("GLITCH_PI_NC_MAX"))


def _apply_nc_cap(signal: dict) -> dict:
    """Devuelve la señal con nc = min(nc, tope). Se aplica ANTES de operar, asi TODO lo que sigue (ordenes, confirmacion
    del fill, P&L, historial, estado del Pi) usa los contratos realmente operados. Conserva el original en nc_signal."""
    nc = signal["nc"]
    if NC_MAX is None or nc <= NC_MAX:
        return signal
    capped = dict(signal)
    capped["nc"] = NC_MAX
    capped["nc_signal"] = nc
    return capped


def _nc_label(signal: dict) -> str:
    if signal.get("nc_signal") is not None:
        return f"{signal['nc']} (señal: {signal['nc_signal']}, tope local)"
    return str(signal["nc"])


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _validate_signal(signal: dict) -> Optional[str]:
    """None si la señal es operable; si no, la razon. No toca la red."""
    side = signal.get("side")
    if not _is_int(side) or side not in (1, -1):
        return f"side invalido ({side!r}; debe ser 1 o -1)"
    max_nc = TEST_SIGNAL_MAX_NC if _is_test_signal(signal) else CFG.nc
    nc = signal.get("nc")
    if not _is_int(nc) or not (1 <= nc <= max_nc):
        return f"nc invalido ({nc!r}; debe ser un entero entre 1 y {max_nc})"
    for key, ref in (("sl_ticks", CFG.sl_ticks), ("tp_ticks", CFG.tp_ticks)):
        v = signal.get(key)
        if not _is_int(v) or not (1 <= v <= SIGNAL_TICKS_MAX_FACTOR * ref):
            return f"{key} invalido ({v!r}; debe ser un entero entre 1 y {SIGNAL_TICKS_MAX_FACTOR * ref})"
    if str(signal.get("product_code")) != CFG.spec.product_code:
        return f"product_code {signal.get('product_code')!r} no coincide con {CFG.spec.product_code!r}"
    if "direction" in signal and signal["direction"] != ("LONG" if side == 1 else "SHORT"):
        return f"direction {signal['direction']!r} no coincide con side {side}"
    return None


def run_once():
    try:
        reconcile_if_needed()

        signal = load_order_signal()
        if not signal:
            log.info("Sin señal pendiente -- nada que hacer.")
            return

        if not _signal_is_current(signal):
            return

        invalid = _validate_signal(signal)
        if invalid:
            _notify_blocked_once_per_day(
                f"La señal pendiente del {signal.get('date')} NO es valida: {invalid}. No se ejecuta y se descarta "
                f"(el Pi solo opera señales dentro de los limites de su config local)."
            )
            save_order_signal({})
            return

        signal = _apply_nc_cap(signal)

        if not _is_test_signal(signal):
            _now = ct_now()
            if _now.hour * 60 + _now.minute >= ENTRY_DEADLINE_MINUTES:
                _notify_blocked_once_per_day(
                    f"La señal del {signal.get('date')} ({signal.get('direction', '?')}) se vio a las "
                    f"{_now.strftime('%H:%M')} CT, DESPUES de la hora limite de entrada "
                    f"({ENTRY_DEADLINE_MINUTES // 60:02d}:{ENTRY_DEADLINE_MINUTES % 60:02d} CT). NO se ejecuta: el paper "
                    f"entra ~9:40 CT y entrar tarde no replica lo que se mide. Se descarta."
                )
                save_order_signal({})
                return

        if not _is_test_signal(signal) and _signal_already_claimed(signal):
            # Esta señal YA se ejecuto (o se intento) hoy y por alguna razon sigue en el Gist (p. ej. fallo en
            # silencio el PATCH que la limpia). Re-ejecutarla duplicaria la entrada: se descarta y se limpia.
            # Aviso limitado a uno por dia: si la limpieza SIGUE fallando, esto se repetiria cada ciclo.
            _notify_blocked_once_per_day(
                f"La señal del {signal.get('date')} ({signal.get('direction', '?')}) ya se ejecuto o se intento "
                f"hoy y sigue en el Gist (¿fallo la limpieza?). NO se vuelve a ejecutar; se intenta limpiarla."
            )
            log.warning("señal ya reclamada hoy -- descartada y limpiada (no se re-ejecuta)")
            save_order_signal({})
            return

        if not _orderside_verified():
            _notify_blocked_once_per_day(
                "Hay una señal pendiente pero el gate de Fase 3 no esta satisfecho "
                "(GLITCH_PI_PHASE3=si y pi/orderside_verified.json, ambos requeridos) -- "
                "por diseño (instruccion del 22-sep), no se coloca ninguna orden real "
                "hasta completar la verificacion de OrderSide contra cuenta de practica."
            )
            return

        verified_map = _load_verified_side_map()
        client = authenticate()
        account_id = _resolve_account_id(client)
        contract = resolve_contract_id(client, signal["product_code"])
        contract_id = contract["id"]

        if _has_untracked_position(client, account_id, contract_id):
            _notify_blocked_once_per_day(
                f"Hay una posicion abierta en {contract_id} que este modulo no tiene registrada en "
                f"PI_STATE_FILE (posible resto de un crash entre colocar una orden y guardar el "
                f"estado) -- no se coloca una orden nueva encima. Requiere revision manual."
            )
            return

        reference_price = _reference_price(client, contract_id)
        tp_price = _round_to_tick(reference_price + signal["side"] * signal["tp_ticks"] * CFG.spec.tick_size)
        sl_price = _round_to_tick(reference_price - signal["side"] * signal["sl_ticks"] * CFG.spec.tick_size)

        # Reclamar la señal ANTES de la orden de entrada (at-most-once, ver _claim_signal). Lo mas tarde posible
        # -- despues de todos los chequeos que pueden abortar sin operar (precio de referencia, guard de posicion)
        # -- y estrictamente antes de tocar el broker con una orden. Si no se puede escribir, no se opera.
        if not _is_test_signal(signal):
            _claim_signal(signal)

        try:
            bracket = place_bracket_order(client, account_id, contract_id, signal["side"], signal["nc"],
                                           tp_price, sl_price, verified_map)
        except BracketPlacementFailed as bf:
            # Se descarta la señal: reintentar cada 2 min abriria y cerraria posiciones en bucle.
            save_order_signal({})
            if bf.flatten_error is None:
                tail = "La posicion se aplano automaticamente (cuenta plana). Señal descartada."
            else:
                tail = (f"El flatten automatico TAMBIEN FALLO ({bf.flatten_error}): hay una posicion ABIERTA "
                        f"sin proteccion en {contract_id} -- CERRARLA MANUALMENTE en TopstepX AHORA. "
                        f"Señal descartada.")
            msg = (f"{PREFIX}\nSTATUS: ALERTA\nLa entrada se ejecuto pero no se pudo colocar TP/SL "
                   f"({bf.reason}). {tail}\n{utc_now_str()}")
            send(msg)
            log.error(msg.replace("\n", " | "))
            return

        state = {
            "phase": "bracket_open", "signal": signal, "entry_price": reference_price,
            "entry_order_id": bracket["entry_order_id"], "tp_price": tp_price, "sl_price": sl_price,
            "tp_order_id": bracket["tp_order_id"], "sl_order_id": bracket["sl_order_id"],
            "contract_id": contract_id, "account_id": account_id, "opened_at": utc_now_str(),
        }
        save_pi_state(state)

        seen, readable = _confirm_entry_filled(client, account_id, contract_id, signal["nc"])
        if readable and seen == 0:
            _abort_unfilled_entry(client, account_id, contract_id, bracket)
            return
        if not readable:
            send(f"{PREFIX}\nSTATUS: ALERTA\nNo se pudo leer la posicion para confirmar el fill de la entrada "
                 f"({signal['nc']} contratos en {contract_id}); se sigue monitoreando el bracket. Verificalo en "
                 f"TopstepX.\n{utc_now_str()}")
        elif seen < signal["nc"]:
            send(f"{PREFIX}\nSTATUS: ALERTA\nFill PARCIAL de la entrada: {seen} de {signal['nc']} contratos en "
                 f"{contract_id}. TP/SL estan por {signal['nc']}: al resolverse, el Pi cerrara cualquier remanente "
                 f"invertido.\n{utc_now_str()}")

        msg = (f"{PREFIX}\n[OPEN]\n"
               f"{signal['direction']}: ~{reference_price:,.4f} (referencia pre-trade)\n"
               f"TP: {tp_price:,.4f}  SL: {sl_price:,.4f}\n"
               f"Contracts: {_nc_label(signal)}  |  Intento #{signal['intento']}\n"
               + utc_now_str())
        send(msg)
        log.info(msg.replace("\n", " | "))

        outcome = poll_position_until_closed(client, account_id, contract_id,
                                              state["tp_order_id"], state["sl_order_id"],
                                              tp_price, sl_price)
        _finalize_cycle(client, account_id, state, outcome)

    except Exception as e:
        log.error(f"run_once: fallo no manejado -- {e}")
        _notify_blocked_once_per_day(f"Ciclo del Pi fallo con una excepcion no manejada: {e}")


def main():
    log.info("=" * 60)
    log.info(f"GLITCH — Pi Executor ({CFG.spec.label})")
    log.info(f"PHASE3_ENABLED={PHASE3_ENABLED}  orderside_verified={_load_verified_side_map() is not None}")
    log.info(f"NC_MAX (tope local de contratos)={NC_MAX if NC_MAX is not None else 'sin tope'}")
    log.info("=" * 60)
    while True:
        run_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
