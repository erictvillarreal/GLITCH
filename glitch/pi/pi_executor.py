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
ultimo dato real de mercado de ProjectX (client.get_bars(), NO yfinance).
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
    ["TOPSTEP_USERNAME", "TOPSTEP_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    f"PI-EXECUTOR-{_PRODUCT_KEY_FOR_STARTUP_CHECK}",
)

from brokers.projectx import OrderType, ProjectXClient, ProjectXCredentials, position_is_open
from execution.ct_logging import setup_ct_logging
from execution.gist_store import load_log as _gist_load_log
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


def _resolve_account_id(client: ProjectXClient) -> int:
    """Cuenta sobre la que opera el Pi.

    TOPSTEP_ACCOUNT_ID (opcional) la FIJA explicitamente -- obligatoria en cuanto hay mas de una cuenta activa
    (Combine + Practice, desde el 1-oct-2026). Siempre se valida contra las cuentas activas que ve la API: un id
    mal escrito o de una cuenta inactiva detiene el ciclo en vez de operar donde no se debe. Sin variable y con
    una sola cuenta activa se usa esa. Con varias y sin variable NO se adivina por posicion en la lista."""
    accounts = client.get_accounts(only_active=True)
    if not accounts:
        raise RuntimeError("Sin cuentas activas en ProjectX -- verificar TOPSTEP_USERNAME/API_KEY.")
    ids = [a.get("id") for a in accounts]

    pinned = os.getenv("TOPSTEP_ACCOUNT_ID", "").strip()
    if pinned:
        for a in accounts:
            if str(a.get("id")) == pinned:
                return a["id"]
        raise RuntimeError(
            f"TOPSTEP_ACCOUNT_ID={pinned!r} no esta entre las cuentas activas ({ids}) -- no se opera en "
            f"ninguna otra cuenta. Corregir la variable en ~/.glitch_pi.env."
        )

    if len(accounts) > 1:
        raise RuntimeError(
            f"Se encontraron {len(accounts)} cuentas activas ({ids}) y TOPSTEP_ACCOUNT_ID no esta definida -- "
            f"no se adivina cual usar. Definir TOPSTEP_ACCOUNT_ID en ~/.glitch_pi.env."
        )
    return accounts[0]["id"]


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
    bars = client.get_bars(contract_id, bar_type=1, bar_size=1, count=1, live=False)
    if not bars:
        raise RuntimeError(f"Sin datos de mercado de ProjectX para contract_id={contract_id!r} -- "
                            f"no se puede fijar un precio de referencia, no se coloca la orden.")
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
    for k in _FILL_PRICE_KEYS:
        v = order_record.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _lookup_order(client: ProjectXClient, account_id: int, order_id) -> Optional[dict]:
    for o in client.get_orders(account_id, only_open=False):
        if (o.get("id") or o.get("orderId")) == order_id:
            return o
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


# ── 4. place_bracket_order ───────────────────────────────────────────────
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
    tp_id = client.place_order(account_id, contract_id, OrderType.LIMIT, exit_side, size, price=tp_price)
    sl_id = client.place_order(account_id, contract_id, OrderType.STOP, exit_side, size, stop_price=sl_price)

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
            client.cancel_exit_orders(tp_order_id, sl_order_id)
            # closeContract (POST /api/Position/closeContract) NO depende de que lado es compra/venta --
            # a diferencia de client.flatten_position(), que decide el lado con brokers.projectx.OrderSide
            # (el enum SIN verificar, bloqueante #1) y lee `netPos` (campo tampoco verificado): con el enum
            # invertido, "flatten" de un LONG compraria MAS en vez de cerrar. Ver pi/ARCHITECTURE.md.
            flatten_failed = False
            try:
                client.close_contract(account_id, contract_id)
            except Exception as e:
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
            client.cancel_order(sl_order_id)
            rec = _lookup_order(client, account_id, tp_order_id)
            price = _extract_fill_price(rec) if rec else None
            return {"result": "TP", "exit_price": price if price is not None else tp_price,
                    "exit_price_estimated": price is None}

        if tp_open and not sl_open:
            client.cancel_order(tp_order_id)
            rec = _lookup_order(client, account_id, sl_order_id)
            price = _extract_fill_price(rec) if rec else None
            return {"result": "SL", "exit_price": price if price is not None else sl_price,
                    "exit_price_estimated": price is None}

        if not tp_open and not sl_open:
            # Caso raro: ambos ya cerrados (ej. cancelados manualmente fuera
            # de este proceso). No se puede saber cual fue real -- se marca
            # UNKNOWN, queda en el historico para revision manual.
            return {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True}

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
    if outcome.get("flatten_failed"):
        entry["flatten_failed"] = True   # solo cuando ocurre -- revision manual de la posicion
    append_to_historic_log(signal["product"], entry)
    save_order_signal({})
    save_pi_state({})

    msg = (f"{PREFIX}\n[CLOSE] [{outcome['result']}]\n"
           f"{signal['direction']}: {entry_price:,.4f} → {exit_price:,.4f}\n"
           f"PnL: ${pnl:+,.2f}  |  Contracts: {signal['nc']}\n"
           f"Intento #{signal['intento']}\n"
           + ("(precio de entrada estimado -- no confirmado por el broker)\n" if entry_estimated else "")
           + ("(precio de salida estimado -- no confirmado por el broker)\n" if entry["exit_price_estimated"] else "")
           + utc_now_str())
    send(msg)
    log.info(msg.replace("\n", " | "))


# ── 7. append_to_historic_log ────────────────────────────────────────────
def append_to_historic_log(product_key: str, entry: dict) -> None:
    """
    Escribe al MISMO archivo (geometry_{producto}_log.json) que
    geometry_scheduler.py -- misma forma de entrada que ese scheduler ya
    produce en modo paper, para que _current_intento()/_attempt_pnl()/etc.
    (definidas ahi) sigan funcionando sin cambios sobre un historico mixto
    paper+real.
    """
    filename = f"geometry_{product_key.lower()}_log.json"
    paper_log = _gist_load_log(filename)
    paper_log.append(entry)
    _gist_save_log(filename, paper_log)


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


def run_once():
    try:
        reconcile_if_needed()

        signal = load_order_signal()
        if not signal:
            log.info("Sin señal pendiente -- nada que hacer.")
            return

        if not _signal_is_current(signal):
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
        tp_price = reference_price + signal["side"] * signal["tp_ticks"] * CFG.spec.tick_size
        sl_price = reference_price - signal["side"] * signal["sl_ticks"] * CFG.spec.tick_size

        bracket = place_bracket_order(client, account_id, contract_id, signal["side"], signal["nc"],
                                       tp_price, sl_price, verified_map)

        state = {
            "phase": "bracket_open", "signal": signal, "entry_price": reference_price,
            "entry_order_id": bracket["entry_order_id"], "tp_price": tp_price, "sl_price": sl_price,
            "tp_order_id": bracket["tp_order_id"], "sl_order_id": bracket["sl_order_id"],
            "contract_id": contract_id, "account_id": account_id, "opened_at": utc_now_str(),
        }
        save_pi_state(state)

        msg = (f"{PREFIX}\n[OPEN]\n"
               f"{signal['direction']}: ~{reference_price:,.4f} (referencia pre-trade)\n"
               f"TP: {tp_price:,.4f}  SL: {sl_price:,.4f}\n"
               f"Contracts: {signal['nc']}  |  Intento #{signal['intento']}\n"
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
    log.info("=" * 60)
    while True:
        run_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
