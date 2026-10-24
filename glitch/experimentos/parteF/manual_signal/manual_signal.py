"""
Glitch — Señal manual SEGURA para el plan B (24-oct-2026) -- PROPUESTA, NEEDS HUMAN REVIEW (CLAUDE.md regla 4: escribe una orden real).

Uso: si el scheduler de Railway no puede correr (builds pausados, cron caido, llaves muertas), escribir la señal desde el Mac/Pi con ESTA herramienta,
NUNCA a mano en el editor del Gist. Escribe EXACTAMENTE el mismo payload que geometry_scheduler.save_order_signal (el Pi lo consume igual).

    python -m pi.manual_signal                       # DRY-RUN (default): imprime el JSON exacto y las verificaciones; no escribe nada
    python -m pi.manual_signal --write               # pide teclear la palabra de confirmacion (p. ej. LUNES-LONG-40)
    python -m pi.manual_signal --write --confirm LUNES-LONG-40

Variables necesarias: GITHUB_GIST_TOKEN, GIST_ID (y TELEGRAM_BOT_TOKEN/CHAT_ID solo para avisar; sin ellas avisa por consola). No importa el scheduler
(su require_env mata el proceso) ni telegram_bot (hace sys.exit al importarse sin variables): se copia lo minimo y se prueba la paridad en tests/test_manual_signal.py.

RECHAZA (exit 2, nada escrito): dia no habil; --date distinto de hoy (CT); lado distinto de decide_side(trading_day_index(hoy)); nc fuera de 1..tope;
antes de 9:35 CT (el Pi entraria de inmediato, antes de la referencia del diseño) o desde las 10:00 CT (deadline del Pi) o 14:30 CT (flatten);
orden ya pendiente en el Gist; posicion registrada por el Pi (pi_position_<producto>.json); ya hay un ciclo de HOY en el historial; cualquier fallo de lectura del Gist
(incluido el historial: si no se puede leer NO se asume intento 1). Tras escribir, verifica por lectura posterior y avisa por Telegram.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prop_firm import TOPSTEP_50K
from execution import gist_store
from execution.gist_store import GistError
from strategies.geometry_pure import CANDIDATES, decide_side, trading_day_index

CT = ZoneInfo("America/Chicago")
ENTRY_GATE_MINUTES = 9 * 60 + 35          # igual que geometry_scheduler.ENTRY_GATE_MINUTES
SESSION_FLATTEN_MINUTES = 14 * 60 + 30    # igual que geometry_scheduler.SESSION_FLATTEN_MINUTES / pi_executor
DEFAULT_DEADLINE_MINUTES = 10 * 60        # pi_executor.ENTRY_DEADLINE_MINUTES (default; GLITCH_PI_ENTRY_DEADLINE_CT)
PROFIT_TARGET = TOPSTEP_50K.profit_target
MLL_THRESHOLD = -TOPSTEP_50K.mll_distance
# Copia del calendario de geometry_scheduler.is_trading_day (test de paridad en tests/test_manual_signal.py)
HOLIDAYS = {(2026, 1, 1), (2026, 1, 19), (2026, 2, 16), (2026, 4, 3), (2026, 5, 25), (2026, 7, 3), (2026, 9, 7), (2026, 11, 26), (2026, 12, 25)}
DAY_WORD = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]


# ── copia de la logica de intento de geometry_scheduler (funciones puras) ──────────────────────────────────────────────
def _attempt_entries(log, intento):
    return [e for e in log if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(log, intento):
    return sum(e.get("pnl", 0) for e in _attempt_entries(log, intento))


def _attempt_peak(log, intento):
    peak = running = 0.0
    for e in _attempt_entries(log, intento):
        running += e.get("pnl", 0)
        peak = max(peak, running)
    return peak


def _attempt_trailing_floor(log, intento):
    return min(_attempt_peak(log, intento) + MLL_THRESHOLD, 0.0)


def _check_attempt_reset(pnl, profit_target, floor):
    if pnl >= profit_target:
        return "PASE"
    if pnl <= floor:
        return "QUIEBRE"
    return None


def current_intento(log: list) -> int:
    """Misma logica que geometry_scheduler._current_intento (derivada solo del historial)."""
    tags = [e.get("intento") for e in log if e.get("intento") is not None]
    if not tags:
        return 1
    latest = max(tags)
    if _check_attempt_reset(_attempt_pnl(log, latest), PROFIT_TARGET, _attempt_trailing_floor(log, latest)) is not None:
        return latest + 1
    return latest


def is_trading_day(d: dt.date) -> bool:
    return d.weekday() < 5 and (d.year, d.month, d.day) not in HOLIDAYS


def deadline_minutes() -> int:
    raw = os.environ.get("GLITCH_PI_ENTRY_DEADLINE_CT", "10:00")
    try:
        h, m = raw.strip().split(":"); h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except Exception:
        pass
    return DEFAULT_DEADLINE_MINUTES


def confirmation_word(d: dt.date, side: int, nc: int) -> str:
    return f"{DAY_WORD[d.weekday()]}-{'LONG' if side == 1 else 'SHORT'}-{nc}"


def build_payload(product: str, d: dt.date, side: int, nc: int, intento: int) -> dict:
    cfg = CANDIDATES[product]
    return {"date": str(d), "side": side, "direction": "LONG" if side == 1 else "SHORT", "ticker": cfg.spec.yf_ticker,
            "product_code": cfg.spec.product_code, "nc": nc, "sl_ticks": cfg.sl_ticks, "tp_ticks": cfg.tp_ticks,
            "product": product, "intento": intento, "dry_run": False}


def nc_cap(product: str, nc_max_arg: Optional[int] = None) -> int:
    cap = CANDIDATES[product].nc
    for v in (nc_max_arg, os.environ.get("GLITCH_PI_NC_MAX")):
        try:
            if v not in (None, "") and int(v) >= 1:
                cap = min(cap, int(v))
        except ValueError:
            pass
    return cap


def check(now: dt.datetime, product: str, nc: int, side_asserted: Optional[int], date_asserted: Optional[str], log: list, order: dict, pi_state: dict,
          nc_max_arg: Optional[int] = None) -> list:
    """Lista de razones de rechazo ([] = se puede escribir). Funcion pura (sin red)."""
    bad, today = [], now.date()
    t = now.hour * 60 + now.minute
    if not is_trading_day(today):
        bad.append(f"{today} no es dia habil (fin de semana o feriado de la lista del scheduler)")
    if date_asserted is not None and date_asserted != str(today):
        bad.append(f"--date {date_asserted} no es hoy en CT ({today})")
    side = decide_side(trading_day_index(today), CANDIDATES[product].direction)
    if side_asserted is not None and side_asserted != side:
        bad.append(f"el lado pedido ({'LONG' if side_asserted == 1 else 'SHORT'}) no es el de la estrategia hoy ({'LONG' if side == 1 else 'SHORT'}; day_index={trading_day_index(today)})")
    cap = nc_cap(product, nc_max_arg)
    if not (1 <= nc <= cap):
        bad.append(f"nc={nc} fuera de 1..{cap} (tope = min(config, GLITCH_PI_NC_MAX, --nc-max))")
    dl = deadline_minutes()
    if t < ENTRY_GATE_MINUTES:
        bad.append(f"son las {now.strftime('%H:%M')} CT, antes de la compuerta de entrada 09:35 CT: el Pi entraria de inmediato, antes de la referencia del diseño")
    if t >= dl:
        bad.append(f"son las {now.strftime('%H:%M')} CT, desde la hora limite de entrada del Pi ({dl // 60:02d}:{dl % 60:02d} CT): el Pi descartaria la señal")
    if t >= SESSION_FLATTEN_MINUTES:
        bad.append(f"son las {now.strftime('%H:%M')} CT, desde el flatten (14:30 CT)")
    if order:
        bad.append(f"ya hay una orden pendiente en el Gist (fecha {order.get('date')}): no se sobreescribe")
    if pi_state:
        bad.append(f"el Pi tiene una posicion registrada ({pi_state.get('phase')}): no se escribe otra señal")
    if any(str(e.get("date")) == str(today) for e in log):
        bad.append(f"el historial ya tiene un ciclo con fecha {today}")
    return bad


def notify(text: str) -> bool:
    """Telegram best-effort (sin importar scheduler.telegram_bot, que hace sys.exit sin variables). True si se envio."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("(Telegram no configurado: aviso solo por consola)")
        return False
    try:
        import requests
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": text}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"(no se pudo avisar por Telegram: {e})")
        return False


def _read(filename: str, kind):
    data = gist_store._read_file_strict(filename)
    if data is None:
        return kind()
    if not isinstance(data, kind):
        raise GistError(f"{filename} no contiene {kind.__name__}")
    return data


def main(argv=None, now: Optional[dt.datetime] = None, input_fn=input, notify_fn=notify) -> int:
    ap = argparse.ArgumentParser(description="Señal manual segura (dry-run por defecto)")
    ap.add_argument("--product", default=os.environ.get("GLITCH_PRODUCT", "MES"))
    ap.add_argument("--nc", type=int, default=None)
    ap.add_argument("--nc-max", type=int, default=None)
    ap.add_argument("--side", choices=["LONG", "SHORT"], default=None, help="opcional: afirma el lado; se rechaza si no es el de la estrategia")
    ap.add_argument("--date", default=None, help="opcional: afirma la fecha (YYYY-MM-DD); se rechaza si no es hoy en CT")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--confirm", default=None, help="palabra de confirmacion (si no se da con --write, se pide por teclado)")
    a = ap.parse_args(argv)
    now = now or dt.datetime.now(CT)
    if a.product not in CANDIDATES or CANDIDATES[a.product].spec.yf_ticker is None:
        print(f"RECHAZADO: producto {a.product!r} no valido"); return 2
    cfg = CANDIDATES[a.product]
    order_file, log_file, pi_file = f"orden_pendiente_{a.product.lower()}.json", f"geometry_{a.product.lower()}_log.json", f"pi_position_{a.product.lower()}.json"
    try:
        log = _read(log_file, list)            # lectura ESTRICTA: si no se puede leer, NO se asume intento 1
        order = _read(order_file, dict)
        pi_state = _read(pi_file, dict)
    except (GistError, RuntimeError) as e:
        print(f"ABORTADO: no se pudo leer el Gist ({e}). No se escribio nada."); return 2
    today = now.date()
    side = decide_side(trading_day_index(today), cfg.direction)
    nc = a.nc if a.nc is not None else cfg.nc
    bad = check(now, a.product, nc, {"LONG": 1, "SHORT": -1}.get(a.side), a.date, log, order, pi_state, a.nc_max)
    intento = current_intento(log)
    payload = build_payload(a.product, today, side, nc, intento)
    print(f"Hoy {today} ({DAY_WORD[today.weekday()]}) {now.strftime('%H:%M')} CT | day_index={trading_day_index(today)} | intento={intento} (de {len(log)} entradas del historial)")
    print("JSON que se escribiria en", order_file, ":"); print(json.dumps(payload, indent=2, ensure_ascii=False))
    if bad:
        print("RECHAZADO:"); [print("  -", b) for b in bad]; return 2
    if not a.write:
        print(f"DRY-RUN: nada escrito. Para escribir: --write y teclear {confirmation_word(today, side, nc)}"); return 0
    word = confirmation_word(today, side, nc)
    typed = a.confirm if a.confirm is not None else input_fn(f"Escribe {word} para confirmar: ")
    if typed.strip() != word:
        print("CONFIRMACION INCORRECTA: nada escrito."); return 3
    try:
        gist_store.save_log_strict(order_file, payload)       # PATCH estricto (lanza GistError); acepta cualquier JSON
        back = _read(order_file, dict)
    except (GistError, RuntimeError) as e:
        print(f"ERROR al escribir/verificar: {e}"); notify_fn(f"S10GLITCH - MANUAL - {a.product}\nSTATUS: ERROR\nno se pudo escribir/verificar la señal manual: {e}"); return 4
    if back != json.loads(json.dumps(payload)):
        print("ERROR: la lectura posterior NO coincide; revisar el Gist a mano."); notify_fn(f"S10GLITCH - MANUAL - {a.product}\nSTATUS: ERROR\nla orden NO quedo escrita (lectura posterior distinta)"); return 4
    print("OK: orden escrita y verificada por lectura posterior.")
    notify_fn(f"S10GLITCH - MANUAL - {a.product}\n[SEÑAL MANUAL ENVIADA AL PI]\nDirection: {payload['direction']}\nContracts: {nc}\nSL/TP: {cfg.sl_ticks}/{cfg.tp_ticks} ticks\nIntento #{intento}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
