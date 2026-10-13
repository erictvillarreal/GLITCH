#!/usr/bin/env python3
"""GLITCH -- Registro diario de friccion (T3, 12-oct-2026). SOLO LECTURA. Corre EN EL PI una vez por sesion, despues del flatten (cron cada 5 min; solo actua a partir de las 14:40 CT y
si el registro del dia aun no existe). Reconstruye, SIN tocar pi_executor.py, lo que paso en la sesion a partir de ProjectX (ordenes, barras de 1 min, posiciones, trades) y del log del
ejecutor, y lo agrega a `friction_<producto>_log.json` en el Gist (archivo SEPARADO del historial de trades: un solo escritor, sin riesgo de pisar geometry_<producto>_log.json).
Campos (positivo = adverso): entry_slip_ticks (fill vs cierre de la barra de 1 min previa a la orden), tp_cross_ticks (ticks que el precio cruzo el TP sin llenarlo),
flatten_slip_ticks, stop_slip_usd_per_ct, comision real por contrato RT, fallos en el log, eventos rojos duros, plana a las 14:35.
NO VERIFICADO contra la API real: nombres de campos de Order/search y Trade/search (segun la documentacion de ProjectX) y los patrones del log; el primer ensayo en Practice los confirma
(el registro guarda `raw` con ids y marcas de tiempo para depurar). NEEDS HUMAN REVIEW. Uso: python3 pi/ops/friction_collect.py --account-id N --product MES [--dry-run] [--date YYYY-MM-DD]"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from monitoring.friction import build_record, scan_executor_log   # noqa: E402
from monitoring.notify import parse_env_file                        # noqa: E402

CT = ZoneInfo("America/Chicago")
ST_FILLED = 2
TYPE_LIMIT, TYPE_MARKET, TYPE_STOP = 1, 2, 4
_PRICE_KEYS = ("filledPrice", "avgFillPrice", "averageFillPrice", "fillPrice")


def parse_ts(s) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def fill_price(o: dict) -> Optional[float]:
    for k in _PRICE_KEYS:
        v = o.get(k)
        try:
            if v is not None and not isinstance(v, bool) and float(v) > 0:
                return float(v)
        except (TypeError, ValueError):
            continue
    return None


def classify_orders(orders: list, date: str) -> dict:
    """Ordenes del dia (fecha CT) de UN contrato: entrada (mercado, la primera llenada), TP (limite), SL (stop) y una posible salida a mercado posterior (flatten)."""
    day = []
    for o in orders:
        t = parse_ts(o.get("creationTimestamp"))
        if t is not None and t.astimezone(CT).date().isoformat() == date:
            day.append((t, o))
    day.sort(key=lambda x: x[0])
    mk = [(t, o) for t, o in day if o.get("type") == TYPE_MARKET and o.get("status") == ST_FILLED and fill_price(o)]
    if not mk:
        return {}
    t_entry, entry = mk[0]
    out = {"entry": entry, "t_entry": t_entry}
    out["tp"] = next((o for t, o in day if o.get("type") == TYPE_LIMIT), None)
    out["sl"] = next((o for t, o in day if o.get("type") == TYPE_STOP), None)
    later = [(t, o) for t, o in mk[1:]]
    out["flat"] = later[-1] if later else None
    return out


def bar_close_before(bars: list, ts: dt.datetime) -> Optional[float]:
    """Cierre de la ultima barra de 1 min COMPLETA al momento ts (inicio + 60 s <= ts)."""
    best = None
    for b in bars:
        t = parse_ts(b.get("t") or b.get("timestamp"))
        if t is not None and t + dt.timedelta(seconds=60) <= ts:
            best = b
    return None if best is None else float(best["c"] if "c" in best else best["close"])


def extreme_between(bars: list, side: int, t0: dt.datetime, t1: dt.datetime) -> Optional[float]:
    vals = []
    for b in bars:
        t = parse_ts(b.get("t") or b.get("timestamp"))
        if t is not None and t0 - dt.timedelta(seconds=60) <= t <= t1:
            vals.append(float(b["h"] if "h" in b else b["high"]) if side == 1 else float(b["l"] if "l" in b else b["low"]))
    if not vals:
        return None
    return max(vals) if side == 1 else min(vals)


def build_day_record(date, product, spec, orders, bars, positions_after_1435_open, log_lines, fees_total, nc_hint=None) -> Optional[dict]:
    c = classify_orders(orders, date)
    if not c:
        return None
    entry, t_entry = c["entry"], c["t_entry"]
    efill = fill_price(entry)
    tp = c.get("tp"); sl = c.get("sl")
    tp_price = float(tp["limitPrice"]) if tp and tp.get("limitPrice") is not None else None
    sl_price = float(sl["stopPrice"]) if sl and sl.get("stopPrice") is not None else None
    side = 1 if (tp_price is not None and tp_price > efill) else -1
    if tp_price is None and sl_price is not None:
        side = 1 if sl_price < efill else -1
    tp_filled = bool(tp and tp.get("status") == ST_FILLED)
    sl_filled = bool(sl and sl.get("status") == ST_FILLED)
    flat = c.get("flat")
    if tp_filled:
        exit_type, exit_fill, t_exit = "TP", fill_price(tp), parse_ts(tp.get("updateTimestamp")) or t_entry
    elif sl_filled:
        exit_type, exit_fill, t_exit = "SL", fill_price(sl), parse_ts(sl.get("updateTimestamp")) or t_entry
    elif flat is not None:
        exit_type, exit_fill, t_exit = "FLATTEN", fill_price(flat[1]), flat[0]
    else:
        exit_type, exit_fill, t_exit = None, None, None
    ref = bar_close_before(bars, t_entry)
    exit_ref = bar_close_before(bars, t_exit) if (t_exit is not None and exit_type == "FLATTEN") else None
    extreme = extreme_between(bars, side, t_entry, t_exit) if t_exit is not None else None
    nc = int(entry.get("size") or nc_hint or 0)
    rec = build_record(date, product, nc, side, spec.tick_size, spec.tick_value_usd, ref_price=ref, entry_fill=efill, tp_price=tp_price, tp_filled=tp_filled if tp_price is not None else None,
                       extreme_after_entry=extreme, exit_type=exit_type, exit_fill=exit_fill, exit_ref=exit_ref, stop_price=sl_price, commission_total=fees_total,
                       log_scan=scan_executor_log(log_lines, date), flat_by_1435=not positions_after_1435_open)
    rec["raw"] = {"entry_order": entry.get("id"), "tp_order": tp.get("id") if tp else None, "sl_order": sl.get("id") if sl else None, "t_entry": t_entry.isoformat(),
                  "t_exit": None if t_exit is None else t_exit.isoformat(), "ref_price": ref, "entry_fill": efill}
    return rec


def read_fees(client, account_id, date) -> Optional[float]:
    """Suma de `fees` de Trade/search del dia (NO VERIFICADO: nombre del endpoint y del campo). None si falla."""
    try:
        start = dt.datetime.fromisoformat(date).replace(tzinfo=CT).astimezone(dt.timezone.utc)
        resp = client._post("/api/Trade/search", {"accountId": account_id, "startTimestamp": start.strftime("%Y-%m-%dT%H:%M:%SZ")})
        trades = resp.get("trades", []) if isinstance(resp, dict) else resp
        vals = [abs(float(t["fees"])) for t in trades if t.get("fees") is not None and not t.get("voided")]
        return sum(vals) if vals else None
    except Exception:
        return None


class GistStore:
    def __init__(self, product):
        from execution.gist_store import load_state, save_state         # noqa: E402 (requiere el venv y GIST_ID/GITHUB_GIST_TOKEN)
        self.name = f"friction_{product.lower()}_log.json"; self._l, self._s = load_state, save_state

    def load(self):
        return self._l(self.name).get("entries", [])

    def save(self, entries):
        self._s(self.name, {"entries": entries})


def main(argv=None, client=None, store=None, now: Optional[dt.datetime] = None) -> int:
    ap = argparse.ArgumentParser(description="Registro diario de friccion (solo lectura)")
    ap.add_argument("--account-id", type=int, required=True)
    ap.add_argument("--product", default="MES")
    ap.add_argument("--date", default=None, help="fecha CT YYYY-MM-DD (default: hoy)")
    ap.add_argument("--env-file", default=os.path.expanduser("~/.glitch_pi.env"))
    ap.add_argument("--log-file", default=os.path.expanduser("~/glitch-logs/pi_executor.log"))
    ap.add_argument("--spool", default=os.path.expanduser("~/.glitch_friction_unsynced.jsonl"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-window", action="store_true")
    args = ap.parse_args(argv)
    now = now or dt.datetime.now(CT)
    date = args.date or now.date().isoformat()
    if not args.force_window and (now.weekday() >= 5 or now.hour * 60 + now.minute < 14 * 60 + 40):
        return 0
    for k, v in parse_env_file(args.env_file).items():
        os.environ.setdefault(k, v)
    store = store or GistStore(args.product)
    existing = store.load()
    if any(e.get("date") == date and e.get("product") == args.product for e in existing):
        return 0
    if client is None:
        from brokers.projectx import ProjectXClient, ProjectXCredentials   # noqa: E402
        client = ProjectXClient(ProjectXCredentials.from_env(), verbose=False)
    from strategies.geometry_pure import CANDIDATES                          # noqa: E402
    spec = CANDIDATES[args.product].spec
    orders = client.get_orders(args.account_id, only_open=False, hours_back=30)
    cid = next((o.get("contractId") for o in orders if o.get("contractId")), None)
    bars = client.get_recent_bars(cid, minutes_back=600, live=False, limit=700) if cid else []
    open_pos = bool(client.get_positions(args.account_id))
    try:
        with open(args.log_file, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    rec = build_day_record(date, args.product, spec, orders, bars, open_pos, lines, read_fees(client, args.account_id, date))
    if rec is None:
        print(f"friction_collect: {date} sin operaciones del ejecutor en {args.account_id} (nada que registrar)")
        return 0
    print("friction_collect:", {k: v for k, v in rec.items() if k != "raw"})
    if args.dry_run:
        return 0
    try:
        store.save(existing + [rec])
    except Exception as e:
        with open(args.spool, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"friction_collect: Gist fallo ({e}) -- registro guardado en {args.spool}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
