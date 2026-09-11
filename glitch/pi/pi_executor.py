"""
GLITCH — pi_executor.py (DISEÑO / PSEUDOCODIGO, 11-sep-2026)
==============================================================================
NO ES CODIGO FUNCIONAL TODAVIA. Ver GLITCH_RESEARCH_LOG.md (rama
`design/pi-execution`) para el diseño completo: mapeo Railway/Pi,
mecanismo de comunicacion via Gist, comparacion de SDKs, y por que se
descarto el archivo `brokers/projectx.py` ya existente como base (usa
al menos un enum que contradice la documentacion oficial actual --
ver ADVERTENCIA mas abajo).

RESPONSABILIDAD UNICA de este archivo: correr en el Raspberry Pi
(dispositivo personal del usuario) y ser el UNICO componente del
sistema que abre/monitorea/cierra posiciones REALES contra
ProjectX/TopstepX. Topstep prohibe VPN/VPS/servidores remotos para la
EJECUCION de ordenes -- por eso esto NO puede vivir en Railway, a
diferencia de todo el calculo de señal (que se queda ahi sin cambios).

Nunca calcula señales, nunca hace analisis de mercado, nunca decide
side/TP/SL -- todo eso ya lo calculo Railway y lo dejo escrito en
`orden_pendiente_{producto}.json` (mismo Gist compartido, ver
execution/gist_store.py -- CERO codigo nuevo ahi, se reusa
load_state/save_state/load_log/save_log tal cual ya existen).

DEPENDENCIAS: SOLO `requests` (ya es dependencia del resto del
proyecto). Decision explicita, documentada en el research log: se fue
directo contra gateway.docs.projectx.com en vez de cualquiera de los 4
SDKs de terceros evaluados -- ninguno es oficial, el mas completo
(project-x-py) arrastra numpy/polars/plotly innecesarios para un
dispositivo que solo ejecuta ordenes, y la API real es lo bastante
simple (JWT bearer + REST plano) para no justificar la dependencia.

ADVERTENCIA CRITICA, NO VERIFICADA AUN CONTRA CUENTA REAL:
la documentacion oficial (gateway.docs.projectx.com/docs/api-reference/
order/order-place/), citada TEXTUAL dos veces por separado durante la
investigacion de este diseño, dice:
    side: 0 = Bid (buy), 1 = Ask (sell)
El archivo YA EXISTENTE (pero no usado por ningun scheduler actual)
`brokers/projectx.py` define la CONVENCION CONTRARIA:
    OrderSide.BID = 0  # comentado como "Sell"
    OrderSide.ASK = 1  # comentado como "Buy"
Una de las dos fuentes esta invertida. Operar con el lado equivocado
mueve dinero real en la direccion opuesta a la señal. NO CONFIAR EN
NINGUNA DE LAS DOS SIN VERIFICAR EMPIRICAMENTE contra una orden real
en cuenta de practica/demo antes de que este codigo toque una cuenta
fondeada -- ver TODO en OrderSide mas abajo.

REQUISITOS DE HARDWARE/OS (punto 4 del pedido original):
  - Raspberry Pi OS 64-bit (Bookworm o mas reciente), Python 3.11+.
  - Unica dependencia (`requests`) tiene wheels universales (`py3-none-any`
    o `abi3`) -- CERO compilacion nativa necesaria en ARM64, confirmado
    por su naturaleza pure-Python + bindings ya precompilados de sus
    propias dependencias (urllib3, certifi, idna, charset-normalizer),
    todas con soporte ARM64 estandar en PyPI.
  - NO necesita numpy/pandas/scipy -- esas siguen siendo 100% responsabilidad
    de Railway (calculo de señal, backtesting, analisis).
"""
from __future__ import annotations
import os
import sys
import time
import datetime as dt
from enum import IntEnum
from typing import Optional
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Reuso TOTAL de la infraestructura ya construida -- CERO codigo nuevo
# en ninguno de estos dos modulos, ver punto 2 del pedido original.
from execution.gist_store import load_state, save_state, load_log, save_log
from scheduler.telegram_bot import send  # mismo bot/chat que los schedulers de Railway

CT = ZoneInfo("America/Chicago")

# ── Config (env vars -- credenciales de ProjectX viven SOLO en el Pi,
#    NUNCA en Railway, exactamente por la misma razon por la que la
#    ejecucion misma no puede vivir ahi) ─────────────────────────────
PRODUCT_KEY = os.environ.get("GLITCH_PRODUCT", "MES")  # mismo patron que los schedulers de Railway
TOPSTEP_USERNAME = os.environ.get("TOPSTEP_USERNAME")  # reusa el nombre ya usado en brokers/projectx.py
TOPSTEP_API_KEY = os.environ.get("TOPSTEP_API_KEY")
ACCOUNT_ID = os.environ.get("TOPSTEP_ACCOUNT_ID")  # TODO: confirmar via Account/search la primera vez, no adivinar

ORDER_FILE = f"orden_pendiente_{PRODUCT_KEY.lower()}.json"  # Railway -> Pi, ver research log
LOG_FILE = f"geometry_{PRODUCT_KEY.lower()}_log.json"  # MISMO archivo historico que ya usa Railway

POLL_INTERVAL_SECONDS = 120  # 2 min -- ver research log, "Manejo de rate limits" para el calculo de margen
ORDER_POLL_SECONDS = 30  # una vez hay una posicion abierta, poll mas fino (mismo POLL_INTERVAL que Railway usa hoy)
FORCED_FLATTEN_CT = (15, 10)  # 15:10 CT -- hard flat time real de Topstep (core/prop_firm.py: session_close_ct)
TOKEN_MAX_AGE_HOURS = 20  # refrescar con margen, el token real dura 24h

BASE_URL = "https://api.topstepx.com"  # UNICO host confirmado -- demo vs cuenta real se distingue por accountId, NO por host (ver research log)


# ── Enums (ProjectX Gateway API, orden-place) ───────────────────────
class OrderType(IntEnum):
    LIMIT = 1
    MARKET = 2
    STOP = 4
    TRAILING_STOP = 5


class OrderSide(IntEnum):
    """
    TODO CRITICO ANTES DE CUALQUIER ORDEN REAL: verificar empiricamente
    contra una cuenta de practica/demo cual valor realmente compra y
    cual realmente vende -- ver ADVERTENCIA en el docstring del modulo.
    Valores de abajo = los citados TEXTUALMENTE de
    gateway.docs.projectx.com hoy (11-sep-2026), NO los de
    brokers/projectx.py (que dice lo contrario).
    """
    BID_BUY = 0
    ASK_SELL = 1


# ── Estado del proceso (JWT en memoria -- este proceso corre como
#    daemon de larga duracion en el Pi, NO como invocacion fresca de
#    cron por ciclo como los schedulers de Railway) ──────────────────
_token: Optional[str] = None
_token_issued_at: Optional[dt.datetime] = None


def authenticate() -> str:
    """
    POST /api/Auth/loginKey -- {userName, apiKey} -> {token, success}.
    TODO: implementar. Guardar _token/_token_issued_at (UTC now).
    Fallar ruidosamente (raise) si success=False -- mismo criterio
    fail-loud que execution/gist_store.py y scheduler/telegram_bot.py
    ya usan para configuracion ausente/invalida.
    """
    raise NotImplementedError


def ensure_fresh_token() -> str:
    """
    Si no hay token o su edad > TOKEN_MAX_AGE_HOURS: POST
    /api/Auth/validate (requiere el token ACTUAL como Bearer, mismo
    patron que el resto de la API -- TODO: confirmar esto
    empiricamente, la documentacion no lo aclaro explicitamente al
    momento de este diseño) -> {success, newToken}. Si falla la
    validacion, re-autenticar desde cero via authenticate().
    """
    raise NotImplementedError


def resolve_contract_id(product_code: str) -> str:
    """
    Resuelve el contractId REAL vigente de ProjectX para `product_code`
    (ej. "MES") -- via Contract/search o Contract/available (TODO:
    confirmar cual de los dos exactamente, brokers/projectx.py usa
    Contract/available pero no fue verificado contra la doc oficial
    durante este diseño). INDEPENDIENTE del front-month que Railway ya
    resuelve via Massive (execution/contracts.py) -- son dos
    namespaces de ticker distintos (Massive: "MESZ26", ProjectX:
    "CON.F.US.DA6.M25" segun el ejemplo de la doc oficial), no hay
    forma de traducir uno al otro de forma confiable, asi que el Pi
    resuelve el suyo propio desde la fuente que realmente va a usar
    para operar. El Pi NO necesita credenciales de Massive.
    """
    raise NotImplementedError


# ── Orden pendiente (Railway -> Pi, ver research log para el schema
#    completo del documento) ──────────────────────────────────────────
def load_pending_order() -> dict:
    return load_state(ORDER_FILE)


def save_pending_order(d: dict) -> None:
    save_state(ORDER_FILE, d)


def place_bracket_order(order: dict, contract_id: str) -> dict:
    """
    POST /api/Order/place con stopLossBracket/takeProfitBracket
    nativos (confirmado hoy contra la doc oficial -- soporta bracket
    en la MISMA orden, a diferencia de brokers/projectx.py que hace 3
    ordenes separadas porque asumio que no existia esa opcion).

    TODO CRITICO: la doc oficial documenta un error real
    ("Brackets cannot be used with Position Brackets. You must enable
    Auto OCO Brackets.") -- CONFIRMAR que la cuenta esta en modo
    "Auto OCO Brackets" antes de asumir que este camino funciona. Si
    no lo esta, usar el patron de brokers/projectx.py
    (execute_orb_bracket: entry + TP limit + SL stop como 3 ordenes
    separadas, cancelando la que no fue tocada al cerrar) como fallback
    documentado, NO como bug -- es una alternativa valida segun
    configuracion de cuenta, no una que se descarta por estar
    "vieja".

    order: dict de orden_pendiente_{producto}.json (side, size,
    tp_ticks, sl_ticks). El precio de entrada NO lo decide el Pi --
    es una orden de MERCADO, el precio real lo confirma el broker.

    Retorna: {order_id, entry_price (del fill real, no estimado),
    executed_at_utc}.
    """
    raise NotImplementedError


def poll_position_until_closed(account_id: str, contract_id: str, order: dict) -> dict:
    """
    Loop de monitoreo -- MISMO PATRON que el `while True` de
    scheduler/geometry_scheduler.py, pero contra el broker REAL en vez
    de datos de mercado simulados:

      while True:
          if ct_now() >= FORCED_FLATTEN_CT:
              POST /api/Position/closeContract  # flatten forzado de sesion
              result = "FLATTEN"; break
          positions = POST /api/Position/searchOpen {accountId}
          match = siguiente posicion en `positions` con este contractId
          if match is None:
              # el bracket ya cerro la posicion (TP o SL toco) --
              # confirmar CUAL via Order/search o Trade/search
              # (buscar el order_id de la pierna que llenó, no adivinar
              # por precio actual -- esto es CONFIRMADO, no estimado,
              # a diferencia de la reconciliacion de Railway)
              result = "TP" | "SL"  (segun cual orden hijo se llenó)
              break
          time.sleep(ORDER_POLL_SECONDS)

    Retorna: {result, exit_price (real, del fill o del flatten),
    closed_at_utc}. NUNCA retorna "RECONCILED"/pnl_estimated=True desde
    aqui -- eso es exclusivo de reconcile_if_needed() (ver abajo),
    para el caso donde el proceso murio a mitad de este loop.
    """
    raise NotImplementedError


def reconcile_if_needed() -> Optional[dict]:
    """
    Equivalente al paso 0 de run() en los schedulers de Railway, pero
    ESTRUCTURALMENTE MEJOR: Railway solo puede estimar el resultado de
    una posicion interrumpida comparando el precio de mercado ACTUAL
    contra TP/SL (por eso marca todo "RECONCILED"/pnl_estimated=True,
    nunca sabe con certeza que paso durante el hueco). El Pi puede
    preguntarle al BROKER directamente:

      pending = load_pending_order()
      if pending.get("status") != "ejecutada":
          return None  # nada que reconciliar (o nunca se ejecuto, o ya se cerro y limpio)

      positions = POST /api/Position/searchOpen {accountId}
      if hay un match por contract_id en positions:
          # la posicion sigue REALMENTE abierta -- no se perdio nada,
          # solo hay que retomar el monitoreo desde aqui
          return {"still_open": True, ...}

      # no esta abierta -- el bracket ya la cerro MIENTRAS el Pi estaba
      # caido. A diferencia de Railway, esto se puede CONFIRMAR:
      orders = POST /api/Order/search {accountId, desde executed_at_utc}
      # identificar cual leg (TP o SL) tiene status="filled", tomar su
      # precio de fill real y su timestamp real.
      return {"still_open": False, "result": "TP"|"SL", "exit_price": ..., "closed_at_utc": ...}
      # result="RECONCILED" NUNCA aparece aqui -- todo lo que sale de
      # esta funcion es un resultado CONFIRMADO por el broker, no una
      # estimacion. Ver research log: esto es una mejora real sobre el
      # mecanismo de paper trading, no solo un port.

    Si `positions`/`orders` fallan por red (no por logica): NO asumir
    nada -- alertar por Telegram "RECONCILIACION FALLO, revisar
    manualmente en ProjectX" y no tocar el Gist. Con dinero real, un
    dato ausente es preferible a uno inventado.
    """
    raise NotImplementedError


def append_to_historic_log(closed_order: dict) -> None:
    """
    Escribe la entrada final al MISMO geometry_{producto}_log.json que
    Railway ya lee/escribe (gist_store.load_log/save_log, sin cambios)
    -- mismo schema de siempre (date, side, direction, entry, exit,
    result, pnl, sl_ticks, tp_ticks, nc, dry_run, product, intento),
    para que _current_intento()/_attempt_pnl()/_paper_progress() en
    Railway sigan funcionando MAÑANA sin ningun cambio de codigo ahi --
    ven datos reales exactamente en la misma forma en que hoy ven datos
    simulados.
    """
    raise NotImplementedError


def run_once() -> None:
    """
    Un ciclo del loop principal (llamado cada POLL_INTERVAL_SECONDS):

    1. ensure_fresh_token()
    2. recon = reconcile_if_needed()
       - si recon and recon["still_open"]: seguir a poll_position_until_closed()
         directamente con los datos ya conocidos (no hace falta re-ejecutar nada)
       - si recon and not recon["still_open"]: append_to_historic_log(),
         save_pending_order({}), notificar Telegram, continuar
    3. order = load_pending_order()
       si order.get("status") == "pendiente_de_ejecutar":
           contract_id = resolve_contract_id(order["product"])
           exec_info = place_bracket_order(order, contract_id)
           order.update(exec_info, status="ejecutada", contract_id=contract_id)
           save_pending_order(order)
           notificar Telegram: "ORDEN EJECUTADA EN VIVO -- {order}"
    4. si hay una orden en curso (status=="ejecutada"):
           closed = poll_position_until_closed(ACCOUNT_ID, order["contract_id"], order)
           append_to_historic_log({**order, **closed})
           save_pending_order({})
           notificar Telegram con el resultado real
    """
    raise NotImplementedError


def main() -> None:
    """Loop infinito -- este proceso SI esta pensado para correr
    indefinidamente en el Pi (systemd service o screen/tmux), a
    diferencia de los schedulers de Railway (una invocacion de cron
    por dia). Ver research log para la justificacion de por que un
    daemon persistente es correcto aqui: el Pi necesita mantener el
    JWT en memoria entre polls, y el propio requisito de Topstep es
    que la ejecucion viva en un dispositivo personal siempre encendido
    durante horario de mercado, no en invocaciones efimeras."""
    while True:
        try:
            run_once()
        except Exception as e:
            send(f"PI_EXECUTOR ERROR: {e} -- revisar logs del Pi manualmente")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
