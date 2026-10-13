"""T3 (12-oct-2026) -- tests del paquete monitoring/ y de sus scripts. Sin red: Telegram, ProjectX y Gist se sustituyen por dobles. NADA aqui toca pi_executor.py."""
import datetime as dt
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("GLITCH_PRODUCT", "MES")

from monitoring import friction as F, margin as M, reminders as R, thresholds as TH, weekly as W  # noqa: E402
from monitoring.notify import parse_env_file, sanitize                                               # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


# ── umbrales ───────────────────────────────────────────────────────────────────
def test_classify_boundaries():
    assert TH.classify("entry_slip_ticks", 1.0) == TH.GREEN
    assert TH.classify("entry_slip_ticks", 1.01) == TH.YELLOW
    assert TH.classify("entry_slip_ticks", 2.0) == TH.YELLOW
    assert TH.classify("entry_slip_ticks", 2.01) == TH.RED
    assert TH.classify("entry_slip_ticks", None) == TH.NODATA
    assert TH.classify("cost_ratio", 1.12) == TH.RED


def test_gate_decision_rule():
    assert TH.gate_decision([TH.GREEN, TH.GREEN, TH.NODATA]) == TH.GREEN
    assert TH.gate_decision([TH.GREEN, TH.YELLOW]) == TH.GREEN            # a lo mas UN amarillo
    assert TH.gate_decision([TH.YELLOW, TH.YELLOW]) == TH.YELLOW
    assert TH.gate_decision([TH.GREEN, TH.RED]) == TH.RED
    assert TH.gate_decision([TH.GREEN], hard_red_events=1) == TH.RED      # evento rojo duro = rojo siempre


# ── friccion ────────────────────────────────────────────────────────────────────
def test_slip_signs_long_and_short():
    assert F.entry_slip_ticks(1, 5000.00, 5000.50, 0.25) == pytest.approx(2.0)     # compra que llena arriba = adverso
    assert F.entry_slip_ticks(-1, 5000.00, 4999.50, 0.25) == pytest.approx(2.0)    # venta que llena abajo = adverso
    assert F.entry_slip_ticks(1, 5000.00, 4999.75, 0.25) == pytest.approx(-1.0)    # mejora = negativo
    assert F.flatten_slip_ticks(1, 5010.00, 5009.50, 0.25) == pytest.approx(2.0)
    assert F.stop_slip_usd_per_contract(1, 990.0, 989.0, 1.0, 0.1) == pytest.approx(10.0)


def test_tp_cross():
    assert F.tp_cross_ticks(1, 5009.5, 5012.0, True, 0.25) == 0.0
    assert F.tp_cross_ticks(1, 5009.5, 5010.25, False, 0.25) == pytest.approx(3.0)
    assert F.tp_cross_ticks(1, 5009.5, 5009.0, False, 0.25) is None               # nunca llego al TP
    assert F.tp_cross_ticks(-1, 4990.0, 4989.0, False, 0.25) == pytest.approx(4.0)


def test_scan_executor_log_counts_only_that_day():
    lines = ["2026-10-19 09:45:01 INFO ok", "2026-10-19 09:46:00 ERROR get_positions fallo", "2026-10-19 10:00:00 CRITICAL entrada sin proteccion",
             "2026-10-20 09:45:01 ERROR otro dia", "2026-10-19 11:00:00 ERROR orden duplicada detectada"]
    s = F.scan_executor_log(lines, "2026-10-19")
    assert s["errors"] == 3 and s["hard"]["unprotected_bracket"] == 1 and s["hard"]["duplicate_order"] == 1


def test_build_record_missing_fields_stay_none():
    r = F.build_record("2026-10-19", "MES", 40, 1, 0.25, 1.25)
    assert r["entry_slip_ticks"] is None and r["tp_cross_ticks"] is None and r["flatten_slip_ticks"] is None
    assert F.record_colors(r)["entry_slip_ticks"] == TH.NODATA


def test_aggregate_semaforo_and_hard_red():
    recs = [{"entry_slip_ticks": 0.5, "tp_cross_ticks": 0.0, "api_errors": 0, "hard_red": {}},
            {"entry_slip_ticks": 2.5, "tp_cross_ticks": None, "api_errors": 1, "hard_red": {"open_after_1435": 1}}]
    a = F.aggregate(recs)
    assert a["entry_slip_ticks"] == pytest.approx(1.5) and a["colors"]["entry_slip_ticks"] == TH.YELLOW
    assert a["api_failures_per_20"] == pytest.approx(10.0) and a["colors"]["api_failures_per_20"] == TH.RED
    assert a["hard_red_events"] == 1


# ── margen ───────────────────────────────────────────────────────────────────────
def test_mll_floor_trailing_and_lock():
    assert M.mll_floor("combine", 50000, 50000, 2000) == 48000
    assert M.mll_floor("combine", 51500, 50000, 2000) == 49500
    assert M.mll_floor("combine", 53000, 50000, 2000) == 50000            # se traba en el saldo inicial


def test_eod_ledger_updates_once_per_day():
    l = M.update_eod_ledger({}, 50400, "2026-10-19", 50000)
    assert l["eod_high"] == 50400
    l = M.update_eod_ledger(l, 51000, "2026-10-19", 50000)                 # mismo dia: no cambia
    assert l["eod_high"] == 50400
    l = M.update_eod_ledger(l, 50100, "2026-10-20", 50000)
    assert l["eod_high"] == 50400


def test_levels():
    assert M.level("practice", 1499.0) == "rojo" and M.level("practice", 1500.0) == "verde"
    assert M.level("combine", 2000.0, 40, 1.25) == "verde"                 # 40 ticks
    assert M.level("combine", 1050.0, 40, 1.25) == "verde"                 # 21 ticks
    assert M.level("combine", 1000.0, 40, 1.25) == "amarillo"              # 20 ticks: limite inclusivo
    assert M.level("combine", 900.0, 40, 1.25) == "amarillo"
    assert M.level("combine", 400.0, 40, 1.25) == "rojo"
    assert M.level("combine", 100.0, 0, 1.25) == "verde"                   # sin posicion no hay exposicion


def test_decide_dedupes_and_recovers():
    prev = {}
    lvl, act, st = M.decide("practice", 1000.0, 0, 1.25, "2026-10-19", 1000.0, prev)
    assert (lvl, act) == ("rojo", "alert")
    lvl, act, st2 = M.decide("practice", 900.0, 0, 1.25, "2026-10-19", 1000.0 + 60, st)
    assert act == "none"                                                   # mismo dia y nivel: no repite
    lvl, act, st3 = M.decide("practice", 900.0, 0, 1.25, "2026-10-19", 1000.0 + 7 * 3600, st)
    assert act == "alert"                                                  # re-aviso a las 6 h si sigue en rojo
    lvl, act, st4 = M.decide("practice", 5000.0, 0, 1.25, "2026-10-19", 2000.0, st3)
    assert (lvl, act) == ("verde", "recovered")
    lvl, act, _ = M.decide("combine", 800.0, 40, 1.25, "2026-10-19", 3000.0, {})
    assert (lvl, act) == ("amarillo", "alert")
    lvl, act, _ = M.decide("combine", 300.0, 40, 1.25, "2026-10-19", 3001.0, {"date": "2026-10-19", "level": "amarillo", "last_alert_ts": 3000.0})
    assert (lvl, act) == ("rojo", "escalate")


# ── recordatorios ─────────────────────────────────────────────────────────────────
def test_reminders_by_date_and_predicate():
    ctx = {"attempts_started": 0, "attempts_resolved": 0}
    assert R.due_reminders(dt.date(2026, 10, 15), [], ctx) == []           # antes del arranque nada
    assert [i for i, _ in R.due_reminders(dt.date(2026, 11, 9), [], ctx)] == ["r_2026-11-09_resumen"]
    ids = [i for i, _ in R.due_reminders(dt.date(2026, 11, 16), ["r_2026-11-09_resumen"], ctx)]
    assert "r_presupuesto_5_intentos" in ids and "r_2026-11-16_segunda" in ids and "r_2026-11-09_resumen" not in ids
    early = [i for i, _ in R.due_reminders(dt.date(2026, 10, 28), [], {"attempts_started": 5, "attempts_resolved": 4})]
    assert "r_presupuesto_5_intentos" in early                             # >= 5 intentos adelanta la revision de presupuesto
    n10 = [i for i, _ in R.due_reminders(dt.date(2026, 11, 30), [], {"attempts_resolved": 10})]
    assert "r_n10_prueba" in n10
    assert "r_2027-02-16_n20" in [i for i, _ in R.due_reminders(dt.date(2027, 2, 16), [], ctx)]


def test_render_fills_placeholders():
    out = R.render("Evaluar: {semaforo} | {pass_test}", {"semaforo_text": "VERDE", "pass_test_text": "ok"})
    assert out == "Evaluar: VERDE | ok"


# ── resumen semanal ───────────────────────────────────────────────────────────────
def _log(*attempts):
    out = []; d = dt.date(2026, 10, 19)
    for k, pnls in enumerate(attempts, 1):
        for p in pnls:
            out.append({"date": d.isoformat(), "result": "TP" if p > 0 else "SL", "intento": k, "pnl": p}); d += dt.timedelta(days=1)
    return out


def test_attempt_outcomes():
    log = _log([1551.2, 1551.2], [-2000.0], [500.0, -100.0])
    oc = W.attempt_outcomes(log)
    assert oc == {1: "PASE", 2: "QUIEBRE", 3: "en curso"}
    s = W.summarize_attempts(log)
    assert s == {"started": 3, "passed": 1, "busted": 1, "resolved": 2}


def test_pass_test_power_and_rejection():
    assert W.pass_test(0, 3)["status"] == "sin poder"
    assert W.pass_test(0, 10)["status"] == "rojo"                          # P(0 pases en 10 | 30.8%) = 2.5%
    assert W.pass_test(3, 10)["status"] == "verde"
    assert W.pass_test(2, 20)["status"] == "rojo" and W.pass_test(3, 20)["status"] == "verde"   # k* = 2 en N=20 (REPORT_STACKING_TIMING)
    assert W.pass_test(0, 0)["status"] == "sin datos"


def test_weekly_message_contains_gate_and_costs():
    friction = [{"entry_slip_ticks": 0.4, "tp_cross_ticks": 0.0, "flatten_slip_ticks": 0.0, "api_errors": 0, "hard_red": {}}] * 5
    msg = W.weekly_message(dt.date(2026, 11, 9), _log([1551.2, 1551.2], [-2000.0]), friction, {"attempt_fee_actual": 135.0, "attempt_fee_model": 127.0})
    assert "RESUMEN SEMANAL 2026-11-09" in msg and "1 pases" in msg and "LUZ VERDE" in msg and "VERDE" in msg and "x1.06" in msg


# ── notify ────────────────────────────────────────────────────────────────────────
def test_sanitize_removes_bot_token_and_parse_env(tmp_path):
    assert "123456:ABC-def_x" not in sanitize("error en https://api.telegram.org/bot123456:ABC-def_x/sendMessage")
    p = tmp_path / "env"; p.write_text("# c\nexport TELEGRAM_BOT_TOKEN='abc'\nTELEGRAM_CHAT_ID=42\n")
    assert parse_env_file(str(p)) == {"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_CHAT_ID": "42"}


# ── scripts ───────────────────────────────────────────────────────────────────────
class FakeStore:
    def __init__(self, logs=None, states=None):
        self.logs = logs or {}; self.states = states or {}; self.saved = []

    def load_log(self, name): return self.logs.get(name, [])
    def load_state(self, name): return self.states.get(name, {})
    def save_state(self, name, data): self.states[name] = data; self.saved.append(name)


def test_weekly_summary_only_mondays_and_sends(monkeypatch):
    mod = _load("scheduler/weekly_summary.py", "weekly_summary")
    sent = []
    store = FakeStore(logs={"geometry_mes_log.json": _log([1551.2, 1551.2])}, states={"friction_mes_log.json": {"entries": []}})
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t"); monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    assert mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 10), sender=lambda *a: sent.append(a) or True) == 0   # martes
    assert sent == []
    assert mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: sent.append(a) or True) == 0    # lunes
    assert len(sent) == 1 and "RESUMEN SEMANAL" in sent[0][2]


def test_reminders_job_marks_sent_only_if_delivered(monkeypatch):
    mod = _load("scheduler/reminders_job.py", "reminders_job")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t"); monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    store = FakeStore(logs={"geometry_mes_log.json": []}, states={})
    mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: False)           # Telegram falla
    assert store.saved == []
    mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: True)
    assert store.states["reminders_sent.json"]["ids"] == ["r_2026-11-09_resumen"]
    sent = []
    mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: sent.append(a) or True)   # segunda corrida el mismo dia: idempotente
    assert sent == []
    assert mod.main(["--any-hour"], store=store, today=dt.date(2026, 11, 14), sender=lambda *a: True) == 0         # sabado: no hace nada


class FakeSpec:
    tick_size = 0.25; tick_value_usd = 1.25


class FakeMarginClient:
    def get_accounts(self, only_active=True): return [{"id": 77, "balance": 49000.0}]
    def get_positions(self, account_id): return [{"type": 1, "size": 40, "averagePrice": 5000.0, "contractId": "C"}]
    def get_recent_bars(self, cid, minutes_back=15, live=False): return [{"close": 4990.0}]


def test_margin_alert_computes_cushion_and_sends(tmp_path, monkeypatch, capsys):
    mod = _load("pi/ops/margin_alert.py", "margin_alert")
    sent = []
    monkeypatch.setattr(mod, "send", lambda tok, chat, text: sent.append(text) or True)
    env = tmp_path / "env"; env.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
    args = ["--kind", "combine", "--account-id", "77", "--start-balance", "50000", "--mll", "2000", "--force-window", "--env-file", str(env),
            "--state-file", str(tmp_path / "st.json"), "--ledger-file", str(tmp_path / "led.json")]
    assert mod.main(args, client=FakeMarginClient()) == 0
    out = capsys.readouterr().out
    assert "no_realizado=-2,000" in out and "cojin=-1,000" in out and "nivel=rojo" in out
    assert len(sent) == 1 and "MARGEN COMBINE" in sent[0] and "ROJO" in sent[0]
    assert mod.main(args, client=FakeMarginClient()) == 0                  # segunda corrida: estado guardado -> no repite
    assert len(sent) == 1


def test_margin_alert_missing_account_and_outside_window(tmp_path, capsys):
    mod = _load("pi/ops/margin_alert.py", "margin_alert2")
    class NoAcct(FakeMarginClient):
        def get_accounts(self, only_active=True): return [{"id": 1, "balance": 1.0}]
    env = tmp_path / "env"; env.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
    base = ["--kind", "practice", "--account-id", "77", "--start-balance", "150000", "--mll", "4500", "--env-file", str(env),
            "--state-file", str(tmp_path / "s"), "--ledger-file", str(tmp_path / "l")]
    assert mod.main(base + ["--force-window"], client=NoAcct()) == 3
    sat = dt.datetime(2026, 10, 17, 10, 0, tzinfo=mod.CT)
    assert mod.in_window(sat) is False and mod.in_window(dt.datetime(2026, 10, 19, 10, 0, tzinfo=mod.CT)) is True


UTC = dt.timezone.utc


def _t(h, m, s=0): return dt.datetime(2026, 10, 19, h, m, s, tzinfo=UTC).isoformat()


class FakeFrictionClient:
    def __init__(self, tp_fill=False):
        self.tp_fill = tp_fill
    def get_orders(self, account_id, only_open=False, hours_back=30):
        return [{"id": 1, "contractId": "C", "type": 2, "status": 2, "filledPrice": 5001.50, "size": 40, "creationTimestamp": _t(14, 45, 10), "updateTimestamp": _t(14, 45, 11)},
                {"id": 2, "contractId": "C", "type": 1, "status": 2 if self.tp_fill else 3, "limitPrice": 5009.50, "filledPrice": 5009.50 if self.tp_fill else None,
                 "creationTimestamp": _t(14, 45, 12), "updateTimestamp": _t(15, 10)},
                {"id": 3, "contractId": "C", "type": 4, "status": 3, "stopPrice": 4991.50, "creationTimestamp": _t(14, 45, 12), "updateTimestamp": _t(19, 30)},
                {"id": 4, "contractId": "C", "type": 2, "status": 2, "filledPrice": 5008.75, "size": 40, "creationTimestamp": _t(19, 30, 5), "updateTimestamp": _t(19, 30, 6)}]
    def get_recent_bars(self, cid, minutes_back=15, live=False, limit=50):
        bars = [{"t": _t(14, 43), "c": 5000.75, "h": 5001.0, "l": 5000.0}, {"t": _t(14, 44), "c": 5001.00, "h": 5001.25, "l": 5000.5}]
        bars += [{"t": _t(15, m), "c": 5005.0, "h": 5010.25 if m == 30 else 5006.0, "l": 5004.0} for m in range(0, 60, 5)]
        bars += [{"t": _t(19, 28), "c": 5009.25, "h": 5009.5, "l": 5008.5}, {"t": _t(19, 29), "c": 5009.00, "h": 5009.25, "l": 5008.75}]
        return bars
    def get_positions(self, account_id): return []
    def _post(self, path, body): return {"trades": [{"fees": 1.22 * 20, "voided": False}, {"fees": 1.22 * 20, "voided": False}]}


class MemStore:
    def __init__(self): self.entries = []
    def load(self): return list(self.entries)
    def save(self, entries): self.entries = list(entries)


def test_friction_collect_reconstructs_session(tmp_path):
    mod = _load("pi/ops/friction_collect.py", "friction_collect")
    log = tmp_path / "pi_executor.log"; log.write_text("2026-10-19 09:45:01 INFO entrada\n2026-10-19 09:50:00 ERROR get_orders 400\n")
    store = MemStore()
    now = dt.datetime(2026, 10, 19, 14, 41, tzinfo=mod.CT)
    args = ["--account-id", "77", "--product", "MES", "--log-file", str(log), "--env-file", str(tmp_path / "none")]
    assert mod.main(args, client=FakeFrictionClient(), store=store, now=now) == 0
    assert len(store.entries) == 1
    r = store.entries[0]
    assert r["date"] == "2026-10-19" and r["nc"] == 40 and r["side"] == 1 and r["exit_type"] == "FLATTEN"
    assert r["entry_slip_ticks"] == pytest.approx(2.0)                     # (5001.50 - 5001.00) / 0.25
    assert r["tp_cross_ticks"] == pytest.approx(3.0)                       # maximo 5010.25 vs TP 5009.50, sin llenar
    assert r["flatten_slip_ticks"] == pytest.approx(1.0)                   # ref 5009.00 vs fill 5008.75
    assert r["commission_per_contract_rt"] == pytest.approx(1.22)
    assert r["api_errors"] == 1 and r["hard_red"] == {}
    assert mod.main(args, client=FakeFrictionClient(), store=store, now=now) == 0
    assert len(store.entries) == 1                                         # ya existe el registro del dia: no duplica


def test_friction_collect_tp_filled_and_early_exit(tmp_path):
    mod = _load("pi/ops/friction_collect.py", "friction_collect2")
    store = MemStore()
    assert mod.main(["--account-id", "77", "--env-file", str(tmp_path / "x"), "--log-file", str(tmp_path / "y")], client=FakeFrictionClient(True), store=store,
                    now=dt.datetime(2026, 10, 19, 12, 0, tzinfo=mod.CT)) == 0
    assert store.entries == []                                             # antes de las 14:40 CT no actua
    mod.main(["--account-id", "77", "--env-file", str(tmp_path / "x"), "--log-file", str(tmp_path / "y"), "--force-window"], client=FakeFrictionClient(True), store=store,
             now=dt.datetime(2026, 10, 19, 14, 41, tzinfo=mod.CT))
    r = store.entries[0]
    assert r["exit_type"] == "TP" and r["tp_cross_ticks"] == 0.0 and r["flatten_slip_ticks"] is None


def test_scripts_never_import_executor_or_place_orders():
    """Garantia de 'solo lectura' (AST, ignora docstrings y comentarios): ningun script de monitoreo importa pi_executor ni LLAMA metodos que colocan/cancelan ordenes."""
    import ast
    banned_calls = {"place_order", "place_market_order", "place_limit_order", "place_stop_order", "cancel_order", "cancel_all_orders", "close_contract", "flatten_position",
                    "execute_orb_bracket", "cancel_exit_orders"}
    files = ["pi/ops/margin_alert.py", "pi/ops/friction_collect.py", "scheduler/weekly_summary.py", "scheduler/reminders_job.py"] + [
        os.path.join("monitoring", f) for f in os.listdir(os.path.join(ROOT, "monitoring")) if f.endswith(".py")]
    for rel in files:
        tree = ast.parse(open(os.path.join(ROOT, rel)).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any("pi_executor" in a.name for a in node.names), rel
            if isinstance(node, ast.ImportFrom):
                assert "pi_executor" not in (node.module or "") and not any("pi_executor" in a.name for a in node.names), rel
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                assert name not in banned_calls, f"{rel} llama a {name}"
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "_post" and node.args:
                a0 = node.args[0]
                if isinstance(a0, ast.Constant):
                    assert a0.value.rsplit("/", 1)[-1].lower() in ("search", "searchopen", "balance", "available", "retrievebars"), f"{rel}: _post a {a0.value} (solo lectura)"


def test_cron_hour_guard_dst(tmp_path):
    """Railway programa 13:00 y 14:00 UTC; solo debe actuar cuando en Chicago son las 8:00 (CDT hasta el 1-nov-2026, CST despues)."""
    mod = _load("scheduler/reminders_job.py", "reminders_job_guard")
    store = FakeStore(logs={"geometry_mes_log.json": []}, states={})
    sent = []
    cdt_13utc = dt.datetime(2026, 10, 26, 13, 0, tzinfo=dt.timezone.utc).astimezone(mod.CT)        # 8:00 CDT
    cdt_14utc = dt.datetime(2026, 10, 26, 14, 0, tzinfo=dt.timezone.utc).astimezone(mod.CT)        # 9:00 CDT
    cst_14utc = dt.datetime(2026, 11, 9, 14, 0, tzinfo=dt.timezone.utc).astimezone(mod.CT)         # 8:00 CST
    cst_13utc = dt.datetime(2026, 11, 9, 13, 0, tzinfo=dt.timezone.utc).astimezone(mod.CT)         # 7:00 CST
    assert cdt_13utc.hour == 8 and cdt_14utc.hour == 9 and cst_14utc.hour == 8 and cst_13utc.hour == 7
    os.environ["TELEGRAM_BOT_TOKEN"] = "t"; os.environ["TELEGRAM_CHAT_ID"] = "c"
    assert mod.main([], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: sent.append(a) or True, now_ct=cst_13utc) == 0
    assert sent == []                                                       # 7:00 CST: no actua
    assert mod.main([], store=store, today=dt.date(2026, 11, 9), sender=lambda *a: sent.append(a) or True, now_ct=cst_14utc) == 0
    assert len(sent) == 1                                                   # 8:00 CST: actua
