"""
GLITCH — Geometry Scheduler (Camino B, producto-agnostico) — 25-ago-2026
==========================================================================
Entrada SIN señal predictiva: alterna long/short (default validado) a la
apertura RTH. Salida via barreras fijas en ticks (SL/TP) o flatten
obligatorio de fin de sesion. Ver strategies/geometry_pure.py para la
logica de decision (unica fuente de verdad, compartida con cualquier
backtest futuro) y el porque de cada parametro.

CEREBRO 1 (lo que este modulo resuelve) vs. CEREBRO 2 (pausado, NO
tocar) — diferencia critica:

Cerebro 1 = pasar el Combine. Objetivo: maximizar pass_rate/dias_resolucion
dentro de una ventana ACOTADA de 15 dias, con perdida limitada a la fee
del intento (~$49-149). La geometria de este modulo (Camino B) explota
que esta ventana acotada + perdida acotada permite pasar con alta
probabilidad AUNQUE la estrategia subyacente pierda dinero en promedio
(EV negativo neto de comision) -- la convexidad del payout hace el
trabajo, no una prediccion de mercado.

Cerebro 2 = maximizar payouts reales una vez fondeado (cuenta XFA).
Objetivo DISTINTO: el horizonte es INDEFINIDO (sin ventana de 15 dias que
acote el riesgo), y el umbral relevante no es "$3,000 acumulados" sino
"5 dias de >=$150 netos". Una estrategia con EV negativo o cero que
funciona para pasar el Combine NO sobrevive en Cerebro 2 -- sin la
ventana de tiempo que te protege, el MLL eventualmente alcanza cualquier
estrategia sin edge real positivo.

Cerebro 2 esta PAUSADO porque depende de una pregunta sin resolver: ¿el
MLL de la cuenta XFA se resetea a $0 SOLO la primera vez que se solicita
un payout, o CADA vez? Esto se reporto una vez (fuente: help.topstep.com,
cita parcial) pero NUNCA se verifico el texto completo ni la URL exacta
contra la fuente oficial. Son dos economias completamente distintas para
Cerebro 2 y no se puede diseñar nada confiable sin resolver esto primero.

Regla practica: si una tarea es sobre pasar el Combine (geometria de
ticks, combines_por_año, pass_rate_15d) es Cerebro 1 -- procede. Si es
sobre payouts, XFA, simulate_xfa_lifetime, o el colchon post-payout -- es
Cerebro 2 -- DETENTE y pregunta antes de avanzar, no asumas que el exito
de Cerebro 1 aplica ahi. NO conectar este scheduler a logica de Cerebro 2.

Rotar de producto = cambiar la env var GLITCH_PRODUCT (MES/MGC/M2K/...),
no tocar este archivo. Ver strategies/geometry_pure.py::CANDIDATES.

Arranca en DRY_RUN=true (paper) siempre por default -- pasar a DRY_RUN=false
es una decision explicita separada, no el default de este codigo.

Railway Cron: definir antes de conectar (mismo horario que combo2d,
25 14 * * 1-5, es un punto de partida razonable -- ajustar segun el
producto elegido y su horario RTH real).
"""
import os
import sys
import logging
import time
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# CHEQUEO UNIFICADO DE ARRANQUE (01-sep-2026) -- mismo motivo y mismo
# patron que combo2d_scheduler.py, ver ese archivo y
# GLITCH_RESEARCH_LOG.md para el contexto completo. Debe correr ANTES
# de telegram_bot/execution.contracts/execution.gist_store.
from execution.env_check import require_env

_PRODUCT_KEY_FOR_STARTUP_CHECK = os.getenv("GLITCH_PRODUCT", "MES")  # plain os.getenv, sin dependencias -- seguro de leer aqui
require_env(
    [("MASSIVE_API_KEY", "POLYGON_API_KEY"), "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    f"GEOMETRY-{_PRODUCT_KEY_FOR_STARTUP_CHECK}",
)

from scheduler.telegram_bot import send
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index
from execution.contracts import get_front_month, check_expiry_alerts
from execution.gist_store import load_log as _gist_load_log, save_log as _gist_save_log
from execution.gist_store import load_state as _gist_load_state, save_state as _gist_save_state
from core.prop_firm import TOPSTEP_50K

CT = ZoneInfo("America/Chicago")
# Logging con timestamp SIEMPRE en America/Chicago -- fix del
# 07-sep-2026, ver execution/ct_logging.py para el por que (el patron
# anterior, format="%(asctime)s CT" via basicConfig, dependia
# silenciosamente del TZ del contenedor).
from execution.ct_logging import setup_ct_logging
log = setup_ct_logging("geometry")

# ── Config ────────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

PRODUCT_KEY = _PRODUCT_KEY_FOR_STARTUP_CHECK  # ya calculado arriba, antes del chequeo unificado
if PRODUCT_KEY not in CANDIDATES:
    log.error(f"FATAL: GLITCH_PRODUCT={PRODUCT_KEY!r} no esta en CANDIDATES "
              f"({sorted(CANDIDATES)}). Ver strategies/geometry_pure.py.")
    sys.exit(1)
CFG = CANDIDATES[PRODUCT_KEY]

if CFG.spec.yf_ticker is None:
    log.error(f"FATAL: {PRODUCT_KEY} no tiene yf_ticker verificado en ProductSpec -- "
              f"NO se va a adivinar un simbolo de yfinance para el feed de precio en vivo. "
              f"Verificar y setear ProductSpec.yf_ticker antes de correr este producto.")
    sys.exit(1)

LOG_FILE = f"geometry_{PRODUCT_KEY.lower()}_log.json"  # nombre del archivo DENTRO del gist compartido -- ver execution/gist_store.py
# Estado volatil de "posicion actualmente abierta, si hay una" (09-sep-2026,
# ver GLITCH_RESEARCH_LOG.md) -- archivo SEPARADO de LOG_FILE (historial
# append-only). Reconciliacion de crash-a-mitad-de-monitoreo: ver
# _reconcile_pending_position() y el paso 0 de run().
PENDING_FILE = f"geometry_{PRODUCT_KEY.lower()}_pending.json"
POLL_INTERVAL = 60  # segundos entre polls

# Benchmark teorico para el reporte diario de pass_rate -- ver
# GLITCH_RESEARCH_LOG.md, "Duracion recomendada del periodo de paper
# trading": G2 (SL=100/TP=40, alternar, nc=40) da pass_rate_15d=0.8144
# via Monte Carlo (n_paths=8000, seed=42). El criterio de graduacion a
# DRY_RUN=false exige que el pass_rate EMPIRICO de paper no caiga mas de
# ~15-20pp por debajo de esto -- esa evaluacion la hace un humano al
# cierre del periodo, este reporte solo la deja visible dia a dia.
THEORETICAL_PASS_RATE = 0.8144

# Rediseño de templates de Telegram (09-sep-2026) -- mismo estandar en los
# 3 schedulers, ver GLITCH_RESEARCH_LOG.md. PREFIX identifica el mensaje
# como Cerebro 1/COMBINE de un vistazo, sin ambiguedad con Cerebro 2/XFA
# (geometry_mgc_scheduler.py) ni con COMBO2D.
PREFIX = f"S10GLITCH - COMBINE - {PRODUCT_KEY}"

# "Dias vs. Estimado" -- dias_calendario_esperados = dias_promedio_resolucion
# (avg de TODOS los intentos de Combine resueltos, pase o truene) x
# (1/pass_rate) (intentos esperados hasta pasar). Ver
# GLITCH_RESEARCH_LOG.md, "Duracion recomendada del periodo de paper
# trading" (25-ago-2026): dias_promedio_resolucion=3.6571,
# pass_rate=0.8144 -> intentos_esperados=1.2279 ->
# dias_calendario_esperados=4.4905. Redondeado a 4.49. Numero ya
# calculado y documentado en esa sesion -- no requiere una corrida
# nueva (a diferencia del equivalente de MGC, ver
# scripts/mgc_dias_esperados.py, 09-sep-2026).
DIAS_ESPERADOS = 4.49

# Logica de reinicio de intento de Combine (09-sep-2026) -- confirmado
# contra core/prop_firm.py (fuente ya auditada, usada por
# scripts/cerebro2_cashflow_monte_carlo.py), NO hardcodeado a mano:
# TOPSTEP_50K.profit_target=$3,000, TOPSTEP_50K.mll_distance=$2,000.
# Cuenta 50K es correcta para ESTE scheduler independientemente de que
# producto este activo via GLITCH_PRODUCT -- todo Camino B (MES/MGC/M2K/
# etc. como CANDIDATES) se disenio y valido contra nc_cap de una cuenta
# 50K, no es especifico de MES.
PROFIT_TARGET = TOPSTEP_50K.profit_target      # $3,000
MLL_THRESHOLD = -TOPSTEP_50K.mll_distance      # -$2,000 (perdida acumulada del intento)

_front_month_cache: dict[str, tuple[str, str]] = {}


def utc_now_str():
    """Timestamp UTC para los mensajes de Telegram (template 09-sep-2026)
    -- distinto de ct_now(), que sigue usandose para el timing operativo
    del scheduler (apertura, flatten, etc). No afecta setup_ct_logging()
    (execution/ct_logging.py) -- los logs del servidor siguen en CT."""
    return datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M UTC")


def _current_intento(paper_log: list) -> int:
    """
    Numero de intento de Combine actual -- derivado de paper_log, SIN
    estado separado (mismo principio que _paper_progress: la fecha de
    la primera entrada ES el dia 1, aqui el "intento" mas alto ya visto
    ES el intento actual, A MENOS que ese intento ya haya cruzado un
    umbral de reinicio -- ver el segundo fix de abajo). 1 si no hay
    ninguna entrada con el campo "intento" todavia.

    CORREGIDO #1 (09-sep-2026, ver GLITCH_RESEARCH_LOG.md -- logica de
    reconciliacion tras crash a mitad de monitoreo): considera CUALQUIER
    entrada que tenga el campo "intento", no solo las resueltas
    (TP/SL/FLATTEN). Antes de este fix, una entrada "RECONCILED"
    (result fuera de ese set, a proposito, para excluirla de Pass
    Rate/attempt_pnl) habria quedado invisible aqui tambien -- causando
    que el siguiente trade real se etiquetara con un numero de intento
    YA CONSUMIDO por el intento reconciliado, en vez de avanzar al
    siguiente. "Que intento vamos" y "que entradas cuentan para el
    desempeño de ese intento" son dos preguntas distintas -- esta
    funcion resuelve la primera; _attempt_entries() (mas abajo) resuelve
    la segunda, con el filtro de "resuelto" que SI le corresponde.

    CORREGIDO #2 (10-sep-2026, ver GLITCH_RESEARCH_LOG.md -- OPEN de hoy
    seguia mostrando "$3,000.00 / $3,000 (100.0%)" un dia DESPUES del
    PASE real): el incremento `intento_actual += 1` en run() (paso 5b)
    NUNCA se persistia -- era una variable local de Python, usada solo
    para el resumen diario de ESA MISMA corrida, y se perdia al salir
    del proceso. La corrida del dia SIGUIENTE volvia a calcular
    _current_intento() desde cero, encontraba el mismo intento ya
    completado (sus entradas siguen ahi, sumando exactamente el umbral),
    y abria un trade NUEVO etiquetado con un numero de intento YA
    PASADO -- el sistema nunca avanzaba de intento por su cuenta.
    Corregido para que "que intento vamos" se derive COMPLETO de los
    datos guardados, sin necesitar el incremento local de run(): si el
    intento mas alto YA cruzo PROFIT_TARGET o MLL_THRESHOLD, el intento
    actual real es el SIGUIENTE (que todavia no tiene ninguna entrada),
    no el que acaba de cerrar.
    """
    tags = [e.get("intento") for e in paper_log if e.get("intento") is not None]
    if not tags:
        return 1
    latest = max(tags)
    latest_pnl = _attempt_pnl(paper_log, latest)
    if _check_attempt_reset(latest_pnl, PROFIT_TARGET, MLL_THRESHOLD) is not None:
        return latest + 1
    return latest


def _attempt_entries(paper_log: list, intento: int) -> list:
    """Ciclos resueltos que pertenecen a un intento especifico."""
    return [e for e in paper_log
            if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(paper_log: list, intento: int) -> float:
    """PnL acumulado de UN intento especifico -- distinto de total_pnl
    (historico, todos los intentos). Ver logica de reinicio, 09-sep-2026."""
    return sum(e.get('pnl', 0) for e in _attempt_entries(paper_log, intento))


def _attempt_days_elapsed(paper_log: list, intento: int, today_str: str) -> int:
    """Dias transcurridos DENTRO de un intento especifico. 0 si el
    intento todavia no tiene ningun ciclo resuelto (ej. justo despues de
    un reinicio, antes de que se resuelva el primer trade del intento
    nuevo) -- distinto de _paper_progress()['days_elapsed'] (historico,
    devuelve 1 en ese caso, porque ese cuenta "dias desde el inicio del
    paper trading", no de un intento especifico)."""
    entries = _attempt_entries(paper_log, intento)
    dates_seen = sorted({e["date"] for e in entries if e.get("date")})
    if not dates_seen:
        return 0
    first_date = datetime.strptime(dates_seen[0], "%Y-%m-%d").date()
    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    return (today - first_date).days + 1


def _attempt_peak(paper_log: list, intento: int) -> float:
    """Maximo rodante del PnL acumulado DENTRO de un intento especifico
    -- se reinicia junto con el intento (ver _check_attempt_reset)."""
    peak = 0.0
    running = 0.0
    for e in _attempt_entries(paper_log, intento):
        running += e.get('pnl', 0)
        if running > peak:
            peak = running
    return peak


def _check_attempt_reset(attempt_pnl_after: float, profit_target: float, mll_threshold: float) -> Optional[str]:
    """
    Retorna "PASE", "QUIEBRE", o None -- funcion PURA, sin efectos
    secundarios (no manda mensajes, no toca paper_log), para poder
    testearla en aislamiento del resto de run() (que si tiene llamadas
    de red). mll_threshold ya viene NEGATIVO (ver MLL_THRESHOLD arriba).
    """
    if attempt_pnl_after >= profit_target:
        return "PASE"
    if attempt_pnl_after <= mll_threshold:
        return "QUIEBRE"
    return None


def _build_pending_record(side: int, direction_str: str, entry_price: float, tp_price: float,
                           sl_price: float, ticker: str, today_str: str, intento: int,
                           nc: int, sl_ticks: int, tp_ticks: int, product_key: str, dry_run: bool) -> dict:
    """
    Todo lo necesario para reconciliar esta posicion si el proceso
    muere antes de resolverla (09-sep-2026, ver GLITCH_RESEARCH_LOG.md
    -- hallazgo de la posicion SHORT MGCV6 del 09-sep que nunca recibio
    su CLOSE). Se guarda con save_pending() ANTES del mensaje de
    Telegram de apertura -- estado durable primero, notificacion
    despues, mismo criterio que execution/gist_store.py ya documenta.
    """
    return {
        "date": today_str, "side": side, "direction": direction_str,
        "entry": entry_price, "tp_price": tp_price, "sl_price": sl_price,
        "ticker": ticker, "nc": nc, "sl_ticks": sl_ticks, "tp_ticks": tp_ticks,
        "product": product_key, "dry_run": dry_run, "intento": intento,
    }


def _reconcile_pending_position(pending: dict, current_price: float,
                                 tick_value_usd: float, tick_size: float) -> dict:
    """
    Funcion PURA (sin red, sin Telegram) -- reconstruye la mejor
    estimacion posible de como termino una posicion que quedo
    "pendiente" porque el proceso murio a mitad del monitoreo.

    LIMITACION HONESTA, documentada en el propio registro (no solo en
    un comentario): comparar el precio ACTUAL contra TP/SL no puede
    recuperar el camino real del precio durante el hueco -- si el
    precio toco TP y luego se revirtio antes de la siguiente corrida,
    esto no lo detecta, solo ve donde esta el precio AHORA. Por eso el
    resultado SIEMPRE se marca "RECONCILED" (nunca "TP"/"SL"/"FLATTEN")
    y "pnl_estimated": True -- excluido a proposito de Pass Rate/WR,
    attempt_pnl, y deteccion de PASE/QUIEBRE, porque todos esos filtran
    por result in ("TP","SL","FLATTEN") y "RECONCILED" nunca califica
    (mismo mecanismo que ya excluye "no_data_entry", sin codigo nuevo
    en esos otros calculos).
    """
    side = pending["side"]
    entry_price = pending["entry"]
    tp_price = pending["tp_price"]
    sl_price = pending["sl_price"]

    if side == 1:
        if current_price >= tp_price:
            estimated_outcome, exit_price = "TP", tp_price
        elif current_price <= sl_price:
            estimated_outcome, exit_price = "SL", sl_price
        else:
            estimated_outcome, exit_price = "INCONCLUSIVE", current_price
    else:
        if current_price <= tp_price:
            estimated_outcome, exit_price = "TP", tp_price
        elif current_price >= sl_price:
            estimated_outcome, exit_price = "SL", sl_price
        else:
            estimated_outcome, exit_price = "INCONCLUSIVE", current_price

    pnl = (exit_price - entry_price) * side * tick_value_usd / tick_size * pending["nc"]

    return {
        "date": pending["date"], "side": side, "direction": pending.get("direction"),
        "entry": entry_price, "exit": exit_price, "result": "RECONCILED",
        "estimated_outcome": estimated_outcome,
        "pnl": round(pnl, 2), "pnl_estimated": True, "reconciled": True,
        "sl_ticks": pending.get("sl_ticks"), "tp_ticks": pending.get("tp_ticks"),
        "nc": pending["nc"], "dry_run": pending.get("dry_run"),
        "product": pending.get("product"), "intento": pending["intento"],
    }


def _paper_progress(paper_log: list, today_str: str) -> dict:
    """
    Deriva el progreso del periodo de paper SIN estado separado -- la
    fecha de la primera entrada en paper_log ES el dia 1, no hay que
    llevar un contador aparte que se pueda desincronizar del log real.
    """
    resolved = [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN")]
    dates_seen = sorted({e["date"] for e in paper_log if e.get("date")})

    if dates_seen:
        first_date = datetime.strptime(dates_seen[0], "%Y-%m-%d").date()
        today = datetime.strptime(today_str, "%Y-%m-%d").date()
        days_elapsed = (today - first_date).days + 1
    else:
        days_elapsed = 1  # primera corrida de la vida del scheduler

    n_cycles = len(resolved)
    wins = sum(1 for e in resolved if e.get("result") == "TP")
    pass_rate_empirico = wins / n_cycles if n_cycles > 0 else None

    # Entrada mas reciente ANTERIOR a hoy con resultado -- "el dia anterior"
    prior_resolved = [e for e in resolved if e.get("date") != today_str]
    yesterday = prior_resolved[-1] if prior_resolved else None

    return {
        "days_elapsed": days_elapsed,
        "n_cycles": n_cycles,
        "pass_rate_empirico": pass_rate_empirico,
        "yesterday": yesterday,
    }


# ── Helpers ───────────────────────────────────────────────────────────────
def ct_now(): return datetime.now(CT)


# REFACTOR (27-ago-2026): ya NO leen/escriben el filesystem local -- ver
# el mismo cambio en combo2d_scheduler.py y execution/gist_store.py.
def load_log():
    return _gist_load_log(LOG_FILE)


def save_log(l):
    _gist_save_log(LOG_FILE, l)


def load_pending() -> dict:
    """{} si no hay ninguna posicion pendiente de reconciliar -- ver
    PENDING_FILE arriba y GLITCH_RESEARCH_LOG.md, 09-sep-2026."""
    return _gist_load_state(PENDING_FILE)


def save_pending(d: dict):
    """Pasar {} para limpiar (posicion resuelta normalmente o ya reconciliada)."""
    _gist_save_state(PENDING_FILE, d)


def is_trading_day():
    """
    Calendario de feriados duplicado deliberadamente desde
    combo2d_scheduler.py (a diferencia de la señal/ATR/front-month, esto
    es un dato estatico trivial -- el riesgo de duplicacion es bajo,
    no amerita otro modulo compartido).
    """
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)
    }
    return (now.year, now.month, now.day) not in holidays


def fetch_intraday(ticker):
    """Descarga barras de hoy en 1min para precio actual (mismo patron que combo2d_scheduler.py)."""
    try:
        d = yf.Ticker(ticker).history(period="5d", interval="1m", prepost=False)
        if d.empty: return None
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        import pandas as pd
        d['dt']  = pd.to_datetime(d[tcol], utc=True).dt.tz_convert(CT)
        d['t']   = d['dt'].dt.hour*60 + d['dt'].dt.minute
        d['day'] = d['dt'].dt.date
        today = date.today()
        rth = d[(d['day']==today) & (d['t']>=9*60+30) & (d['t']<=14*60+30)].copy()
        return rth.reset_index(drop=True)
    except Exception as e:
        log.error(f"fetch_intraday {ticker}: {e}")
        return None


def run():
    log.info("=" * 60)
    log.info(f"GLITCH — Geometry Scheduler ({CFG.spec.label})")
    log.info(f"DRY_RUN={DRY_RUN}  NC={CFG.nc}  SL={CFG.sl_ticks}  TP={CFG.tp_ticks}  "
              f"direction={CFG.direction}")
    log.info("=" * 60)

    if not is_trading_day():
        log.info("No es dia de trading — saliendo")
        return

    now = ct_now()
    today_str = str(date.today())
    paper_log = load_log()
    # Logica de reinicio de intento (09-sep-2026, ver GLITCH_RESEARCH_LOG.md)
    # -- resuelve la limitacion documentada anteriormente ("Progreso a
    # Target acumulado sin limite de intento"). "Progreso a
    # Target"/"Equity"/"Peak"/"Dias vs. Estimado" ahora estan acotados al
    # intento actual, que se reinicia a $0 cuando el PnL acumulado del
    # intento cruza PROFIT_TARGET (PASE) o MLL_THRESHOLD (QUIEBRE) --
    # ver paso 5b abajo. "Dia de paper", "Pass Rate", y "Ciclos" NO se
    # reinician -- siguen siendo historicos de TODOS los intentos
    # (decision explicita del usuario: esa es la metrica que importa
    # para juzgar si la geometria se sostiene con mas muestra).
    intento_actual = _current_intento(paper_log)
    attempt_pnl_before = _attempt_pnl(paper_log, intento_actual)

    # ── 0. Reconciliar posicion pendiente de una corrida anterior
    #        interrumpida (09-sep-2026, ver GLITCH_RESEARCH_LOG.md --
    #        hallazgo de la posicion SHORT MGCV6 que nunca recibio su
    #        CLOSE). El propio ticker de la posicion pendiente ya esta
    #        guardado en `pending`, no hace falta resolver el
    #        front-month de HOY para esto. ──
    pending = load_pending()
    if pending:
        log.info(f"Posicion pendiente encontrada de {pending.get('date')} -- reconciliando antes de continuar...")
        recon_bars = fetch_intraday(pending["ticker"])
        recon_price = float(recon_bars.iloc[-1]['close']) if recon_bars is not None and len(recon_bars) > 0 else None
        if recon_price is None:
            msg = (f"{PREFIX}\nSTATUS: ERROR\n"
                   f"ERROR: posicion pendiente de {pending.get('date')} no se pudo reconciliar "
                   f"(sin datos de precio) -- reintentando la proxima corrida. No se abre "
                   f"posicion nueva hoy.\n{utc_now_str()}")
            send(msg)
            log.error(msg.replace("\n", " | "))
            return
        reconciled_entry = _reconcile_pending_position(pending, recon_price, CFG.spec.tick_value_usd, CFG.spec.tick_size)
        paper_log.append(reconciled_entry)
        save_log(paper_log)
        save_pending({})
        recon_msg = (f"{PREFIX} [POSICION RECONCILIADA TRAS INTERRUPCION]\n"
                     f"Intento #{reconciled_entry['intento']}  |  {pending.get('direction')}: "
                     f"{reconciled_entry['entry']:,.4f} → {reconciled_entry['exit']:,.4f}\n"
                     f"Resultado estimado: {reconciled_entry['estimated_outcome']} (NO CONFIRMADO)\n"
                     f"PnL estimado: ${reconciled_entry['pnl']:+,.2f} (reconciliado, no confirmado -- "
                     f"el precio pudo haber tocado TP o SL y revertido durante la interrupcion, "
                     f"esto solo ve donde esta el precio ahora)\n"
                     f"Excluido de Pass Rate/attempt_pnl -- ver GLITCH_RESEARCH_LOG.md\n"
                     f"{utc_now_str()}")
        send(recon_msg)
        log.info(recon_msg.replace("\n", " | "))
        # Recalcular -- la entrada reconciliada puede ser la UNICA con el
        # intento que estaba pendiente (ej. crasheo antes de que ningun
        # trade real de ese intento se resolviera), asi que
        # _current_intento podria cambiar tras appendear.
        intento_actual = _current_intento(paper_log)
        attempt_pnl_before = _attempt_pnl(paper_log, intento_actual)

    # ── 1. Resuelve el contrato en uso (para logging/alertas de vencimiento --
    #        ver docstring de arriba: el feed de precio en vivo usa el simbolo
    #        continuo de yfinance, no requiere el ticker exacto de Massive) ──
    try:
        ticker = get_front_month(CFG.spec.product_code, _front_month_cache)
        log.info(f"Contrato en uso ({CFG.spec.product_code}): {ticker}")
        check_expiry_alerts(_front_month_cache, send, PREFIX)
    except Exception as e:
        log.error(f"No se pudo resolver front-month para {CFG.spec.product_code}: {e}")
        send(f"{PREFIX}\nSTATUS: ERROR\nERROR: front-month resolution failed: {e}")
        return

    # ── 2. Señal: sin predictiva, funcion pura de la fecha (ver geometry_pure.py) ──
    day_idx = trading_day_index(date.today())
    side = decide_side(day_idx, CFG.direction)
    direction_str = {1: "LONG", -1: "SHORT"}[side]
    log.info(f"Direccion (day_index={day_idx}, mode={CFG.direction}): {direction_str}")

    # ── 2b. Reporte de arranque: señal de hoy + resultado de ayer + progreso
    #         del periodo de paper. Se manda YA, sin esperar a que resuelva
    #         el trade de hoy -- el usuario necesita esto para juzgar el
    #         criterio de graduacion sin tener que revisar logs a mano. ──
    progress = _paper_progress(paper_log, today_str)

    if progress["yesterday"] is not None:
        y = progress["yesterday"]
        yesterday_line = f"{y['date']}: {y.get('direction', '?')} → {y['result']}  PnL=${y.get('pnl', 0):+,.2f}"
    else:
        yesterday_line = "(sin ciclo previo registrado)"

    if progress["pass_rate_empirico"] is not None:
        gap_pp = (progress["pass_rate_empirico"] - THEORETICAL_PASS_RATE) * 100
        pass_rate_line = (f"{progress['pass_rate_empirico']:.1%} empirico vs "
                           f"{THEORETICAL_PASS_RATE:.1%} teorico ({gap_pp:+.1f}pp)")
    else:
        pass_rate_line = "sin ciclos resueltos todavia"

    kickoff = (f"{PREFIX} | INICIO DE DIA\n"
               f"Dia {progress['days_elapsed']} de paper  |  Ciclos completados: {progress['n_cycles']}\n"
               f"Señal de hoy: {direction_str} (day_index={day_idx}, mode={CFG.direction})\n"
               f"Resultado de ayer: {yesterday_line}\n"
               f"Pass rate acumulado: {pass_rate_line}\n"
               f"{utc_now_str()}")
    send(kickoff)
    log.info(kickoff.replace("\n", " | "))

    # ── 3. Espera apertura RTH + margen de propagacion de Yahoo.
    #        CAMBIO (03-sep-2026): 9:32 -> 9:35 CT. La ventana anterior
    #        (9:32 + 12x30s = se rinde ~9:37:34 CT real) se rindio 2
    #        minutos ANTES del umbral confirmado de 9:40:09 CT donde
    #        Yahoo SI tiene datos reales para MES=F (confirmado por
    #        scripts/probe_mes_open.py Y por el exito real del "dia 3",
    #        que entro a las 9:40 CT). El dia 4 (03-sep-2026) fallo
    #        exactamente por esto -- no era delay variable/no confiable,
    #        era una ventana ya conocida como insuficiente que nunca se
    #        habia ampliado en el codigo pese a la evidencia. Ver
    #        GLITCH_RESEARCH_LOG.md para el detalle completo. ──
    while ct_now().hour * 60 + ct_now().minute < 9 * 60 + 35:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura RTH...")
        time.sleep(15)

    # CAMBIO (03-sep-2026): 12 -> 20 reintentos (6min -> 10min de
    # presupuesto). Desde el gate de 9:35, 20x30s cubre comodamente hasta
    # ~9:45 CT -- pasa el umbral confirmado de 9:40:09 CT con margen real,
    # no al límite como la ventana anterior. Logging por intento distingue
    # None (fetch_intraday() lanzo excepcion -- esa excepcion ya se
    # loguea aparte dentro de la funcion) de "DataFrame vacio" (fetch OK,
    # pero el filtro RTH no dejo filas).
    entry_bars = None
    for attempt in range(20):
        entry_bars = fetch_intraday(CFG.spec.yf_ticker)
        n_rows = len(entry_bars) if entry_bars is not None else 0
        if entry_bars is not None and n_rows >= 1:
            log.info(f"  {CFG.spec.yf_ticker}: {n_rows} filas RTH recibidas en intento {attempt+1}/20")
            break
        estado = "fetch devolvio None (ver linea de excepcion arriba, si la hay)" if entry_bars is None \
            else f"{n_rows} filas (fetch OK, vacio tras filtro RTH)"
        log.info(f"  Esperando datos {CFG.spec.yf_ticker} ({attempt+1}/20) -- {estado}")
        time.sleep(30)

    if entry_bars is None or entry_bars.empty:
        gave_up_at = ct_now().strftime("%H:%M:%S")
        msg = (f"{PREFIX}\nSTATUS: ERROR\n"
               f"ERROR: no entry data available\n"
               f"Se rindio tras {attempt + 1} intentos a las {gave_up_at} CT")
        send(msg)
        # CAMBIO (03-sep-2026): registrar cuantos intentos se hicieron y a
        # que hora CT se rindio -- no solo que fallo. Con el retraso de
        # Yahoo confirmado como VARIABLE dia a dia (dia 3 entro a las
        # 9:40 CT, dia 4 no entro ni tras 12/12), esto es el dato que
        # permite calcular que tan seguido pasa esto y decidir si Yahoo
        # sigue siendo viable como fuente de precio en vivo, en vez de
        # solo un contador binario de "fallo". Ver GLITCH_RESEARCH_LOG.md.
        paper_log.append({"date": today_str, "signal": True, "side": side,
                          "pnl": 0, "note": "no_data_entry",
                          "attempts_made": attempt + 1, "gave_up_at_ct": gave_up_at})
        save_log(paper_log)
        return

    entry_price = float(entry_bars.iloc[-1]['close'])
    tp_price, sl_price = CFG.barrier_prices(entry_price, side)
    tp_usd, sl_usd = CFG.dollar_tp_sl()

    log.info(f"Entrada: {direction_str} @ {entry_price:.4f}")
    log.info(f"TP={tp_price:.4f} (+${tp_usd:.0f})  SL={sl_price:.4f} (-${sl_usd:.0f})  NC={CFG.nc}")

    # Estado durable ANTES de la notificacion -- si el proceso muere en
    # cualquier punto desde aqui hasta el cierre normal, la PROXIMA
    # corrida encuentra esto y reconcilia en vez de perder el rastro por
    # completo (ver paso 0 arriba). NOTA: se guarda CFG.spec.yf_ticker
    # (el simbolo continuo que fetch_intraday() realmente consulta en el
    # loop de monitoreo), NO `ticker` (el contrato especifico de Massive,
    # solo usado para logging/alertas de vencimiento) -- la reconciliacion
    # necesita el mismo simbolo que el monitoreo en vivo habria usado.
    save_pending(_build_pending_record(
        side, direction_str, entry_price, tp_price, sl_price, CFG.spec.yf_ticker,
        today_str, intento_actual, CFG.nc, CFG.sl_ticks, CFG.tp_ticks, PRODUCT_KEY, DRY_RUN,
    ))

    pct_target_before = attempt_pnl_before / PROFIT_TARGET * 100
    msg = (f"{PREFIX}\n"
           f"[OPEN]\n"
           f"Symbol: {CFG.spec.label} ({ticker})\n"
           f"Direction: {direction_str}\n"
           f"Entry: {entry_price:,.4f}\n"
           f"Contracts: {CFG.nc}\n"
           f"TP: {tp_price:,.4f}\n"
           f"SL: {sl_price:,.4f}\n"
           f"Progreso a Target: ${attempt_pnl_before:,.2f} / ${PROFIT_TARGET:,.0f} ({pct_target_before:.1f}%)\n"
           f"{utc_now_str()}")
    send(msg)

    # ── 4. Monitorea la posicion -- flatten obligatorio de fin de sesion es la
    #        barrera de tiempo VINCULANTE en vivo (ver nota en geometry_pure.py:
    #        max_holding_bars del backtest, ~8.3h, es mas largo que una sesion) ──
    result = None
    exit_price = entry_price

    while True:
        now = ct_now()
        t = now.hour * 60 + now.minute

        if t >= 14 * 60 + 30:
            bars = fetch_intraday(CFG.spec.yf_ticker)
            exit_price = float(bars.iloc[-1]['close']) if bars is not None and len(bars) > 0 else entry_price
            result = "FLATTEN"
            log.info(f"[{now.strftime('%H:%M')} CT] Cierre forzado de sesion @ {exit_price:.4f}")
            break

        bars = fetch_intraday(CFG.spec.yf_ticker)
        if bars is None or bars.empty:
            log.info(f"[{now.strftime('%H:%M')} CT] Sin datos, reintentando...")
            time.sleep(POLL_INTERVAL)
            continue

        price = float(bars.iloc[-1]['close'])
        unreal = (price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * CFG.nc

        if side == 1:
            if price <= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price >= tp_price:
                exit_price = tp_price; result = "TP"; break
        else:
            if price >= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price <= tp_price:
                exit_price = tp_price; result = "TP"; break

        log.info(f"[{now.strftime('%H:%M')} CT] {direction_str} @ {price:.4f} | "
                  f"unreal=${unreal:+.2f} | TP={tp_price:.4f} SL={sl_price:.4f}")
        time.sleep(POLL_INTERVAL)

    # ── 5. PnL y notificacion ──────────────────────────────────────────────
    pnl = (exit_price - entry_price) * side * CFG.spec.tick_value_usd / CFG.spec.tick_size * CFG.nc
    log.info(f"EXIT {result} @ {exit_price:.4f} | PnL={pnl:+.2f}")

    attempt_pnl_after = attempt_pnl_before + pnl
    pct_target_acumulado = attempt_pnl_after / PROFIT_TARGET * 100
    msg = (f"{PREFIX}\n"
           f"[CLOSE] [{result}]\n"
           f"Symbol: {CFG.spec.label} ({ticker})\n"
           f"PnL: ${pnl:+,.2f}\n"
           f"Contracts: {CFG.nc}\n"
           f"Progreso a Target: ${attempt_pnl_after:,.2f} / ${PROFIT_TARGET:,.0f} ({pct_target_acumulado:.1f}%)\n"
           f"Dia de paper: {progress['days_elapsed']}\n"
           f"Pass Rate: {pass_rate_line}\n"
           f"{utc_now_str()}")
    send(msg)

    paper_log.append({
        "date": today_str, "signal": True, "side": side,
        "direction": direction_str, "entry": entry_price,
        "exit": exit_price, "result": result,
        "pnl": round(pnl, 2), "sl_ticks": CFG.sl_ticks, "tp_ticks": CFG.tp_ticks,
        "nc": CFG.nc, "dry_run": DRY_RUN, "product": PRODUCT_KEY,
        "intento": intento_actual,
    })
    save_log(paper_log)
    save_pending({})  # posicion resuelta normalmente -- nada pendiente que reconciliar

    # ── 5b. Verificar reinicio de intento (PASE/QUIEBRE) --
    #         09-sep-2026, ver GLITCH_RESEARCH_LOG.md. El evento se
    #         registra el mismo dia que ocurre -- mensaje separado del
    #         resumen diario normal. ──
    event = _check_attempt_reset(attempt_pnl_after, PROFIT_TARGET, MLL_THRESHOLD)
    if event is not None:
        attempt_days = _attempt_days_elapsed(paper_log, intento_actual, today_str)
        historic_progress = _paper_progress(paper_log, today_str)  # ya incluye el ciclo de hoy
        if historic_progress["pass_rate_empirico"] is not None:
            gap_pp = (historic_progress["pass_rate_empirico"] - THEORETICAL_PASS_RATE) * 100
            hist_pass_rate_line = (f"{historic_progress['pass_rate_empirico']:.1%} empirico vs "
                                     f"{THEORETICAL_PASS_RATE:.1%} teorico ({gap_pp:+.1f}pp)")
        else:
            hist_pass_rate_line = "sin ciclos resueltos todavia"

        reset_msg = (f"{PREFIX} [INTENTO #{intento_actual} COMPLETADO: {event}]\n"
                     f"PnL final del intento: ${attempt_pnl_after:+,.2f}\n"
                     f"Dias que tomo este intento: {attempt_days}\n"
                     f"Pass Rate acumulado historico: {hist_pass_rate_line}\n"
                     f"Iniciando intento #{intento_actual + 1} desde $0\n"
                     f"{utc_now_str()}")
        send(reset_msg)
        log.info(reset_msg.replace("\n", " | "))
        # CORREGIDO (10-sep-2026): re-derivar via _current_intento() en vez
        # de un "+= 1" local -- ese incremento nunca se persistia, asi que
        # la corrida del dia siguiente volvia a calcular el mismo intento
        # ya completado desde cero. _current_intento() ahora detecta este
        # mismo caso (el intento mas alto ya cruzo un umbral) directamente
        # desde paper_log, asi que reusar la MISMA funcion aqui (en vez de
        # una copia manual del mismo calculo) es lo que hace que el fix sea
        # consistente para HOY y para MAÑANA -- una sola fuente de verdad.
        intento_actual = _current_intento(paper_log)

    progress = _paper_progress(paper_log, today_str)  # historico -- recalculado, incluye el ciclo de hoy

    if progress["pass_rate_empirico"] is not None:
        gap_pp = (progress["pass_rate_empirico"] - THEORETICAL_PASS_RATE) * 100
        pass_rate_line = (f"{progress['pass_rate_empirico']:.1%} empirico vs "
                           f"{THEORETICAL_PASS_RATE:.1%} teorico ({gap_pp:+.1f}pp)")
    else:
        pass_rate_line = "sin ciclos resueltos todavia"

    # Acotado al intento actual (ya incrementado arriba si hubo
    # PASE/QUIEBRE hoy) -- si el intento acaba de reiniciarse, estos tres
    # caen naturalmente en 0/0.00/0 (sin ciclos resueltos todavia para el
    # intento nuevo), consistente con "Iniciando intento #N+1 desde $0"
    # del mensaje de reinicio de arriba.
    attempt_equity = _attempt_pnl(paper_log, intento_actual)
    attempt_peak = _attempt_peak(paper_log, intento_actual)
    attempt_days = _attempt_days_elapsed(paper_log, intento_actual, today_str)

    summary = (f"{PREFIX}\n"
               f"Equity: ${attempt_equity:,.2f}\n"
               f"Peak: ${attempt_peak:,.2f}\n"
               f"PnL Hoy: ${pnl:+,.2f}\n"
               f"Ciclos: {progress['n_cycles']}\n"
               f"Pass Rate: {pass_rate_line}\n"
               f"Dias vs. Estimado: {attempt_days} / {DIAS_ESPERADOS} esperados\n"
               f"{utc_now_str()}")
    send(summary)
    log.info("Done — saliendo")


if __name__ == "__main__":
    run()
