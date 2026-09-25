"""
GLITCH — Geometry CANDIDATO A Scheduler (Cerebro 1, paper trading) — PREPARADO 25-sep-2026, NO DESPLEGADO
==========================================================================================================
Candidato A: MES, entrada 8:43 CT (apertura RTH 8:30 CT + ENTRY_WAIT_MINUTES), TP = SL = 100 ticks, nc = 16, alternando sin señal predictiva,
Combine 50K. Ver GLITCH_RESEARCH_LOG.md ("PARTE B", 24/25-sep-2026): disenado con las reglas OFICIALES reales de Topstep
(help.topstep.com), NO con el simulador viejo:

  1. LIQUIDACION MLL EN TIEMPO REAL (help.topstep.com/8284204): el MLL se monitorea con P&L no realizado y al tocarlo la cuenta se liquida.
     A diferencia de geometry_scheduler.py (G2) -- cuyo loop solo sale por TP/SL/flatten -- este scheduler calcula la distancia al piso
     trailing del intento y liquida (resultado "SL" con liquidated_mll=True) si el precio la alcanza antes del SL.
  2. CONSISTENCY TARGET 55% (help.topstep.com/8284208): el intento pasa cuando el profit neto >= max($3,000, mejor_dia / 0.55) y han pasado >= 2 dias.
  3. Flatten condicional en dias de cierre anticipado (execution/session_calendar.py, help.topstep.com/13350348).
  4. Comision del round-turn incluida en el P&L de cada trade (los backtests la incluyen; G2/MGC paper no la incluian).

Diferencias deliberadas con geometry_scheduler.py (MES/G2): fuente de precio = MASSIVE (barra 1min con high/low), no Yahoo -- el delay de Yahoo
para MES=F (datos reales solo desde ~9:40 CT) hace inviable una entrada a las 8:43 CT. ENTRY_WAIT_MINUTES == None a proposito: el delay de
Massive se midio para MGC (~9.4-9.9 min), NO para MES. Este scheduler SE NIEGA A ARRANCAR hasta que se corra scripts/probe_massive_mes_delay.py
en 2 horarios distintos y se fije el valor real (mismo estandar "medir, no asumir" que MGC).

Namespace de Gist NUEVO: geometry_candidatoa_log.json / geometry_candidatoa_pending.json (nunca reusar geometry_mes_log.json de G2).
DRY_RUN=true por default. Poll de 60s con la barra 1min mas reciente: las mechas intra-minuto entre polls no se ven (limitacion declarada; el
backtest usa barras de 5min completas).

NO DESPLEGAR sin aprobacion explicita del usuario (Railway: servicio nuevo, cron ~8:30 CT, freeze windows normales).
"""
from __future__ import annotations
import os
import sys
import math
import time
import datetime as dt
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from execution.env_check import require_env

require_env(
    [("MASSIVE_API_KEY", "POLYGON_API_KEY"), "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
     "GITHUB_GIST_TOKEN", "GIST_ID"],
    "GEOMETRY-CANDIDATO-A",
)

import requests  # noqa: E402

from scheduler.telegram_bot import send  # noqa: E402
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index  # noqa: E402
from execution.contracts import get_front_month, check_expiry_alerts  # noqa: E402
from execution.session_calendar import is_flatten_time, flatten_minutes_ct  # noqa: E402
from execution.gist_store import load_log as _gist_load_log, save_log as _gist_save_log  # noqa: E402
from execution.gist_store import load_state as _gist_load_state, save_state as _gist_save_state  # noqa: E402
from core.prop_firm import TOPSTEP_50K  # noqa: E402

CT = ZoneInfo("America/Chicago")
from execution.ct_logging import setup_ct_logging  # noqa: E402
log = setup_ct_logging("geometry_candidato_a")

# ── Config ────────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
PRODUCT_KEY = "MES_A"
CFG = CANDIDATES[PRODUCT_KEY]
PREFIX = "S10GLITCH - COMBINE - MES-A"
LOG_FILE = "geometry_candidatoa_log.json"
PENDING_FILE = "geometry_candidatoa_pending.json"
POLL_INTERVAL = 60

RTH_OPEN_HOUR, RTH_OPEN_MINUTE = 8, 30     # apertura RTH de MES en CT (9:30 ET)
ENTRY_WAIT_MINUTES = None                  # PENDIENTE: medir con scripts/probe_massive_mes_delay.py (2 corridas, horarios distintos)

# Benchmarks teoricos (scripts/partb2.py, motor con reglas reales; 20,000 paths, 40 dias max por intento) -- ver GLITCH_RESEARCH_LOG.md.
THEORETICAL_PASS_RATE = 0.289
DIAS_ESPERADOS = 7.1                       # dias calendario esperados hasta pasar (dias/pase)

# Reglas del Combine 50K -- fuente unica core/prop_firm.py (verificadas contra help.topstep.com, 24-sep-2026)
PROFIT_TARGET = TOPSTEP_50K.profit_target          # $3,000
MLL_DISTANCE = TOPSTEP_50K.mll_distance            # $2,000
CONSISTENCY_TARGET = 0.55                          # oficial (core/prop_firm.py aun dice 0.50: corregir cuando se apruebe tocar ese modulo)
MIN_TRADING_DAYS = 2                               # "You can pass in as few as two days"
TICK_SIZE, TICK_VALUE, COMMISSION_RT = CFG.spec.tick_size, CFG.spec.tick_value_usd, CFG.spec.commission_roundturn

_front_month_cache: dict[str, tuple[str, str]] = {}


def _fail_if_entry_wait_not_confirmed():
    if ENTRY_WAIT_MINUTES is None:
        msg = (f"{PREFIX}\nSTATUS: ERROR\n"
               f"ERROR: ENTRY_WAIT_MINUTES sin confirmar (None). Correr scripts/probe_massive_mes_delay.py en 2 horarios distintos "
               f"y setear el valor real antes de desplegar. Este scheduler no arranca con un margen adivinado.")
        log.error(msg.replace("\n", " | "))
        try:
            send(msg)
        except Exception as e:
            log.error(f"No se pudo enviar alerta de Telegram: {e}")
        sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────
def ct_now(): return dt.datetime.now(CT)


def utc_now_str():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_log(): return _gist_load_log(LOG_FILE)
def save_log(l): _gist_save_log(LOG_FILE, l)
def load_pending() -> dict: return _gist_load_state(PENDING_FILE)
def save_pending(d: dict): _gist_save_state(PENDING_FILE, d)


def is_trading_day():
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25),
        (2027,1,1)
    }
    return (now.year, now.month, now.day) not in holidays


# ── Logica de intento con las REGLAS REALES (funciones puras, testeables) ─────────────────────────────
def _attempt_entries(paper_log: list, intento: int) -> list:
    return [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(paper_log: list, intento: int) -> float:
    return sum(e.get("pnl", 0) for e in _attempt_entries(paper_log, intento))


def _required_target(best_day: float) -> float:
    """Consistency Target oficial: el target sube a mejor_dia/0.55 si eso excede $3,000. El mejor dia NO se resetea con perdidas."""
    return max(PROFIT_TARGET, best_day / CONSISTENCY_TARGET)


def _trailing_floor_from_peak(peak: float) -> float:
    return min(peak - MLL_DISTANCE, 0.0)


def _attempt_state(paper_log: list, intento: int) -> dict:
    """Recorre el intento en orden. {"status": "PASE"|"QUIEBRE"|None, "pnl","peak","floor","best_day","days","required_target"}.
    QUIEBRE si el pnl tras un trade <= piso trailing PREVIO (el del cierre anterior); PASE si pnl >= target ajustado y dias >= 2."""
    run = peak = best = 0.0
    status = None
    days = 0
    for e in _attempt_entries(paper_log, intento):
        days += 1
        prior_floor = _trailing_floor_from_peak(peak)
        run += e.get("pnl", 0)
        best = max(best, e.get("pnl", 0))
        if status is None:
            if run <= prior_floor: status = "QUIEBRE"
            elif days >= MIN_TRADING_DAYS and run >= _required_target(best): status = "PASE"
        peak = max(peak, run)
    return {"status": status, "pnl": run, "peak": peak, "floor": _trailing_floor_from_peak(peak),
            "best_day": best, "days": days, "required_target": _required_target(best)}


def _current_intento(paper_log: list) -> int:
    tags = [e.get("intento") for e in paper_log if e.get("intento") is not None]
    if not tags:
        return 1
    latest = max(tags)
    return latest + 1 if _attempt_state(paper_log, latest)["status"] is not None else latest


def _liquidation_distance_usd(paper_log: list, intento: int) -> float:
    """Distancia (USD) entre el balance actual del intento y el piso trailing: perdida no realizada que dispara la liquidacion HOY."""
    st = _attempt_state(paper_log, intento)
    return st["pnl"] - st["floor"]


def _liquidation_ticks(distance_usd: float, nc: int, tick_value: float) -> int:
    return max(1, math.ceil(distance_usd / (nc * tick_value) - 1e-9))


def _trade_pnl(entry: float, exit_: float, side: int, nc: int) -> float:
    """P&L neto de comision del round-turn (los backtests la incluyen)."""
    return (exit_ - entry) * side * TICK_VALUE / TICK_SIZE * nc - COMMISSION_RT * nc


def _bar_outcome(side: int, tp_price: float, adverse_price: float, high: float, low: float) -> Optional[str]:
    """'ADVERSE' | 'TP' | None. En una barra que toca ambos, gana el lado adverso (conservador, igual que el backtest)."""
    hit_adv = (low <= adverse_price) if side == 1 else (high >= adverse_price)
    hit_tp = (high >= tp_price) if side == 1 else (low <= tp_price)
    if hit_adv: return "ADVERSE"
    if hit_tp: return "TP"
    return None


def _build_pending_record(side, direction_str, entry_price, tp_price, sl_price, liq_price, ticker, today_str, intento, nc, sl_ticks, tp_ticks, dry_run) -> dict:
    return {"date": today_str, "side": side, "direction": direction_str, "entry": entry_price, "tp_price": tp_price,
            "sl_price": sl_price, "liq_price": liq_price, "ticker": ticker, "nc": nc, "sl_ticks": sl_ticks, "tp_ticks": tp_ticks,
            "product": PRODUCT_KEY, "dry_run": dry_run, "intento": intento}


def _reconcile_pending_position(pending: dict, current_price: float) -> dict:
    """Igual que en G2/MGC: resultado SIEMPRE 'RECONCILED' (estimado, excluido de WR/attempt_state)."""
    side, entry, tp_p = pending["side"], pending["entry"], pending["tp_price"]
    liq = pending.get("liq_price", pending["sl_price"])
    adverse = max(pending["sl_price"], liq) if side == 1 else min(pending["sl_price"], liq)
    hit_tp = current_price >= tp_p if side == 1 else current_price <= tp_p
    hit_adv = current_price <= adverse if side == 1 else current_price >= adverse
    est, exit_price = ("TP", tp_p) if hit_tp else (("SL", adverse) if hit_adv else ("INCONCLUSIVE", current_price))
    return {"date": pending["date"], "side": side, "direction": pending.get("direction"), "entry": entry, "exit": exit_price,
            "result": "RECONCILED", "estimated_outcome": est, "pnl": round(_trade_pnl(entry, exit_price, side, pending["nc"]), 2),
            "pnl_estimated": True, "reconciled": True, "sl_ticks": pending.get("sl_ticks"), "tp_ticks": pending.get("tp_ticks"),
            "nc": pending["nc"], "dry_run": pending.get("dry_run"), "product": pending.get("product"), "intento": pending["intento"]}


def _paper_progress(paper_log: list, today_str: str) -> dict:
    resolved = [e for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN")]
    dates = sorted({e["date"] for e in paper_log if e.get("date")})
    days_elapsed = ((dt.datetime.strptime(today_str, "%Y-%m-%d").date() - dt.datetime.strptime(dates[0], "%Y-%m-%d").date()).days + 1) if dates else 1
    intentos = sorted({e.get("intento", 1) for e in resolved})
    passes = sum(1 for i in intentos if _attempt_state(paper_log, i)["status"] == "PASE")
    blows = sum(1 for i in intentos if _attempt_state(paper_log, i)["status"] == "QUIEBRE")
    pr = passes / (passes + blows) if passes + blows else None
    prior = [e for e in resolved if e.get("date") != today_str]
    return {"days_elapsed": days_elapsed, "n_cycles": len(resolved), "passes": passes, "blows": blows, "pass_rate": pr,
            "yesterday": prior[-1] if prior else None}


def fetch_latest_bar(ticker: str) -> Optional[dict]:
    """Barra mas reciente via Massive (sort=window_start.desc + limit=1, SIN rango de fechas -- ver GLITCH_RESEARCH_LOG.md 07-sep-2026)."""
    api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    for resolution in ("1min", "5min"):
        try:
            r = requests.get(f"https://api.massive.com/futures/v1/aggs/{ticker}", headers=headers,
                             params={"resolution": resolution, "sort": "window_start.desc", "limit": 1}, timeout=20)
            r.raise_for_status()
            res = r.json().get("results", [])
            if res:
                b = res[0]
                return {"open": float(b["open"]), "high": float(b["high"]), "low": float(b["low"]), "close": float(b["close"])}
        except Exception as e:
            log.error(f"fetch_latest_bar {ticker} ({resolution}): {e}")
    return None


def run():
    log.info("=" * 60)
    log.info(f"GLITCH — GEOMETRY CANDIDATO A ({CFG.spec.label})  DRY_RUN={DRY_RUN}  NC={CFG.nc}  SL={CFG.sl_ticks}  TP={CFG.tp_ticks}  ENTRY_WAIT={ENTRY_WAIT_MINUTES}")
    log.info("=" * 60)
    _fail_if_entry_wait_not_confirmed()
    if not is_trading_day():
        log.info("No es dia de trading — saliendo"); return

    today_str = str(dt.date.today())
    paper_log = load_log()
    intento = _current_intento(paper_log)

    pending = load_pending()
    if pending:
        bar = fetch_latest_bar(pending["ticker"])
        if bar is None:
            send(f"{PREFIX}\nSTATUS: ERROR\nERROR: posicion pendiente de {pending.get('date')} no se pudo reconciliar (sin datos) -- reintenta la proxima corrida.\n{utc_now_str()}")
            return
        rec = _reconcile_pending_position(pending, bar["close"])
        paper_log.append(rec); save_log(paper_log); save_pending({})
        send(f"{PREFIX} [POSICION RECONCILIADA TRAS INTERRUPCION]\nIntento #{rec['intento']} | {pending.get('direction')}: {rec['entry']:,.2f} -> {rec['exit']:,.2f}\n"
             f"Resultado estimado: {rec['estimated_outcome']} (NO CONFIRMADO) | PnL estimado ${rec['pnl']:+,.2f}\nExcluido de pass rate/attempt_state.\n{utc_now_str()}")
        intento = _current_intento(paper_log)

    try:
        ticker = get_front_month(CFG.spec.product_code, _front_month_cache)
        check_expiry_alerts(_front_month_cache, send, PREFIX)
    except Exception as e:
        send(f"{PREFIX}\nSTATUS: ERROR\nERROR: front-month resolution failed: {e}"); return

    side = decide_side(trading_day_index(dt.date.today()), CFG.direction)
    direction_str = {1: "LONG", -1: "SHORT"}[side]
    st_before = _attempt_state(paper_log, intento)
    prog = _paper_progress(paper_log, today_str)
    pr_line = f"{prog['pass_rate']:.1%} ({prog['passes']} pases / {prog['blows']} quiebres) vs {THEORETICAL_PASS_RATE:.1%} teorico" if prog["pass_rate"] is not None else "sin intentos resueltos todavia"
    y = prog["yesterday"]
    y_line = f"{y['date']}: {y.get('direction','?')} -> {y['result']}  PnL=${y.get('pnl',0):+,.2f}" if y else "(sin ciclo previo registrado)"
    send(f"{PREFIX} | INICIO DE DIA\nDia {prog['days_elapsed']} de paper  |  Ciclos completados: {prog['n_cycles']}\n"
         f"Señal de hoy: {direction_str} (day_index={trading_day_index(dt.date.today())}, mode={CFG.direction})\nResultado de ayer: {y_line}\n"
         f"Pass rate acumulado: {pr_line}\nIntento #{intento}: ${st_before['pnl']:+,.2f} / target ${st_before['required_target']:,.0f} | dia {st_before['days']}\n{utc_now_str()}")

    open_min = RTH_OPEN_HOUR * 60 + RTH_OPEN_MINUTE
    while ct_now().hour * 60 + ct_now().minute < open_min + ENTRY_WAIT_MINUTES:
        time.sleep(15)

    bar = None
    for attempt in range(20):
        bar = fetch_latest_bar(ticker)
        if bar is not None: break
        time.sleep(30)
    if bar is None:
        gave_up = ct_now().strftime("%H:%M:%S")
        send(f"{PREFIX}\nSTATUS: ERROR\nERROR: no entry data available\nSe rindio tras {attempt + 1} intentos a las {gave_up} CT")
        paper_log.append({"date": today_str, "signal": True, "side": side, "pnl": 0, "note": "no_data_entry", "attempts_made": attempt + 1, "gave_up_at_ct": gave_up})
        save_log(paper_log); return

    entry_price = bar["close"]
    tp_price, sl_price = CFG.barrier_prices(entry_price, side)
    dist = _liquidation_distance_usd(paper_log, intento)
    liq_ticks = _liquidation_ticks(dist, CFG.nc, TICK_VALUE)
    liq_price = entry_price - side * liq_ticks * TICK_SIZE
    adverse_price = max(sl_price, liq_price) if side == 1 else min(sl_price, liq_price)
    liq_binds = liq_ticks < CFG.sl_ticks
    tp_usd, sl_usd = CFG.dollar_tp_sl()
    save_pending(_build_pending_record(side, direction_str, entry_price, tp_price, sl_price, liq_price, ticker, today_str, intento, CFG.nc, CFG.sl_ticks, CFG.tp_ticks, DRY_RUN))
    send(f"{PREFIX}\n[OPEN]\nSymbol: {CFG.spec.label} ({ticker})\nDirection: {direction_str}\nEntry: {entry_price:,.4f}\nContracts: {CFG.nc}\n"
         f"TP: {tp_price:,.4f} (+${tp_usd:,.0f})\nSL: {sl_price:,.4f} (-${sl_usd:,.0f})\n"
         f"Liquidacion MLL: {liq_price:,.4f} (a {liq_ticks} ticks, ${dist:,.0f} de distancia al piso){' -- VINCULANTE (antes del SL)' if liq_binds else ''}\n"
         f"Progreso a Target: ${st_before['pnl']:,.2f} / ${st_before['required_target']:,.0f} ({st_before['pnl']/st_before['required_target']*100:.1f}%)\n{utc_now_str()}")

    result, exit_price, liquidated = None, entry_price, False
    while True:
        now = ct_now()
        if is_flatten_time(now):
            b = fetch_latest_bar(ticker)
            exit_price = b["close"] if b else entry_price
            result = "FLATTEN"; break
        b = fetch_latest_bar(ticker)
        if b is None:
            time.sleep(POLL_INTERVAL); continue
        out = _bar_outcome(side, tp_price, adverse_price, b["high"], b["low"])
        if out == "ADVERSE":
            exit_price, result, liquidated = adverse_price, "SL", liq_binds and adverse_price == liq_price; break
        if out == "TP":
            exit_price, result = tp_price, "TP"; break
        time.sleep(POLL_INTERVAL)

    pnl = _trade_pnl(entry_price, exit_price, side, CFG.nc)
    send(f"{PREFIX}\n[CLOSE] [{result}{' - LIQUIDADO POR MLL' if liquidated else ''}]\nSymbol: {CFG.spec.label} ({ticker})\nContracts: {CFG.nc}\n"
         f"PnL: ${pnl:+,.2f} (neto de comision)\nDia de paper: {prog['days_elapsed']}\n{utc_now_str()}")
    paper_log.append({"date": today_str, "signal": True, "side": side, "direction": direction_str, "entry": entry_price, "exit": exit_price,
                      "result": result, "pnl": round(pnl, 2), "sl_ticks": CFG.sl_ticks, "tp_ticks": CFG.tp_ticks, "nc": CFG.nc,
                      "dry_run": DRY_RUN, "product": PRODUCT_KEY, "intento": intento, "liquidated_mll": liquidated})
    save_log(paper_log); save_pending({})

    st = _attempt_state(paper_log, intento)
    if st["status"] is not None:
        prog2 = _paper_progress(paper_log, today_str)
        pr2 = f"{prog2['pass_rate']:.1%} vs {THEORETICAL_PASS_RATE:.1%}" if prog2["pass_rate"] is not None else "—"
        send(f"{PREFIX} [INTENTO #{intento} COMPLETADO: {st['status']}]\nPnL final del intento: ${st['pnl']:+,.2f} | mejor dia ${st['best_day']:,.0f} | target ajustado ${st['required_target']:,.0f}\n"
             f"Dias que tomo este intento: {st['days']}\nPass rate acumulado: {pr2}\nIniciando intento #{intento + 1} desde $0\n{utc_now_str()}")
        intento = _current_intento(paper_log)

    prog = _paper_progress(paper_log, today_str); cur = _attempt_state(paper_log, intento)
    pr_line = f"{prog['pass_rate']:.1%} ({prog['passes']}/{prog['passes'] + prog['blows']}) vs {THEORETICAL_PASS_RATE:.1%} ({(prog['pass_rate'] - THEORETICAL_PASS_RATE) * 100:+.1f}pp)" if prog["pass_rate"] is not None else "—"
    send(f"{PREFIX}\nPass Rate: {pr_line}\nProgreso a Target: ${cur['pnl']:,.2f} / ${cur['required_target']:,.0f} ({cur['pnl']/cur['required_target']*100:.1f}%)\n"
         f"Peak: ${cur['peak']:,.2f}\nPnL Hoy: ${pnl:+,.2f}\nDias vs. Estimado: {cur['days']} / {DIAS_ESPERADOS} esperados\n{utc_now_str()}")
    log.info("Done — saliendo")


if __name__ == "__main__":
    run()
