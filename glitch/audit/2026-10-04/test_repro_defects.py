"""
Auditoria 04-oct-2026 -- REPRODUCCIONES de hallazgos (solo lectura sobre el repo; sin red, sin broker, sin Gist reales).
Cada test PASA cuando el defecto EXISTE (afirma el comportamiento defectuoso actual). Si un arreglo lo corrige,
el test deja de pasar -- ese es el punto: son evidencia, no regresion.
"""
import datetime as dt
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../glitch
for k, v in {"TOPSTEP_USERNAME": "u", "TOPSTEP_API_KEY": "k", "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c",
             "GITHUB_GIST_TOKEN": "g", "GIST_ID": "id", "GLITCH_PRODUCT": "MES", "MASSIVE_API_KEY": "m"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

import pytest
import pi.pi_executor as pe
import brokers.projectx as px
from test_pi_executor import FakeClient, _signal   # el FakeClient del propio repo

CT = pe.CT
MES = "CON.F.US.MES.Z26"


def clock(monkeypatch, hh, mm, day=(2026, 10, 5)):
    monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(*day, hh, mm, tzinfo=CT))


@pytest.fixture
def gist(monkeypatch):
    store, drops = {}, set()      # drops: (filename, valor-a-descartar) -> simula PATCH fallido SILENCIOSO (como gist_store._write_file)

    def save_state(f, d):
        if (f, json.dumps(d)) in drops:
            return
        store[f] = d
    monkeypatch.setattr(pe, "_gist_load_state", lambda f: store.get(f, {}))
    monkeypatch.setattr(pe, "_gist_save_state", save_state)
    monkeypatch.setattr(pe, "_gist_load_log", lambda f: store.get(f, []))
    monkeypatch.setattr(pe, "_gist_save_log", lambda f, d: store.__setitem__(f, d))
    store["__drops__"] = drops
    return store


@pytest.fixture
def sent(monkeypatch):
    m = []
    monkeypatch.setattr(pe, "send", lambda s: m.append(s))
    return m


def arm(monkeypatch, client):
    monkeypatch.setattr(pe, "authenticate", lambda: client)
    monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
    monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
    monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "555")
    monkeypatch.setattr(pe.time, "sleep", lambda s: None)


class TpFillsOnFirstPoll(FakeClient):
    """El TP se llena en el primer poll (desaparece de las ordenes abiertas); el SL sigue -> TP natural."""
    def __init__(self):
        super().__init__()
        self.polled = 0
    def get_open_orders(self, account_id):
        self.polled += 1
        if self.polled == 1:
            self.open_order_ids.discard(101)
        return super().get_open_orders(account_id)


# ── R1: una respuesta 200 con success=false en Order/searchOpen se lee como "no hay ordenes" ───────────────
def test_R1_api_error_on_searchOpen_looks_like_both_legs_closed_while_position_is_open(monkeypatch, gist, sent):
    clock(monkeypatch, 10, 0)
    c = px.ProjectXClient(px.ProjectXCredentials("u", "k"), verbose=False)
    monkeypatch.setattr(c, "ensure_auth", lambda: None)

    def fake_post(path, body, auth=True):
        if path == "/api/Order/searchOpen":
            return {"success": False, "errorCode": 9, "errorMessage": "transient"}        # HTTP 200 con error de negocio
        if path == "/api/Position/searchOpen":
            return {"positions": [{"id": 1, "accountId": 555, "contractId": MES, "type": 1, "size": 40}], "success": True}
        if path == "/api/Order/search":
            return {"orders": [], "success": True}
        raise AssertionError(path)
    monkeypatch.setattr(c, "_post", fake_post)
    assert c.get_open_orders(555) == []                                    # el error se vuelve lista vacia, en silencio

    gist[pe.PI_STATE_FILE] = {"phase": "bracket_open", "signal": _signal(date="2026-10-05"), "entry_price": 6000.0,
                              "entry_order_id": 100, "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101,
                              "sl_order_id": 102, "contract_id": MES, "account_id": 555, "opened_at": "x"}
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    monkeypatch.setattr(pe, "authenticate", lambda: c)
    pe.reconcile_if_needed()
    assert gist[pe.PI_STATE_FILE] == {} and gist[pe.ORDER_FILE] == {}      # estado Y señal borrados...
    last = gist["geometry_mes_log.json"][-1]
    assert last["result"] == "UNKNOWN" and last["pnl"] == 0.0
    assert pe._position_still_open(c, 555, MES) is True                    # ...con la posicion de 40 contratos TODAVIA abierta
    assert any("[CLOSE] [UNKNOWN]" in m for m in sent)


# ── R2: si el PATCH que limpia la señal falla (silencioso), el Pi la re-ejecuta -> segunda entrada ──────────
def test_R2_signal_clear_write_failure_causes_a_second_full_trade(monkeypatch, gist, sent):
    clock(monkeypatch, 10, 0)
    client = TpFillsOnFirstPoll()
    arm(monkeypatch, client)
    sig = _signal(date="2026-10-05")
    gist[pe.ORDER_FILE] = sig
    gist["__drops__"].add((pe.ORDER_FILE, json.dumps({})))               # gist_store._write_file traga el error: la señal NO se limpia

    pe.run_once()
    assert len(client.placed_orders) == 3                                  # trade 1 (entrada+TP+SL)
    assert gist[pe.ORDER_FILE] == sig                                      # la señal sigue ahi

    client.polled = 0
    client.open_order_ids = set()
    monkeypatch.setattr(pe, "poll_position_until_closed",
                        lambda *a, **k: {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": True})
    pe.run_once()
    assert len(client.placed_orders) == 6                                  # trade 2 de la MISMA señal, la cuenta ya estaba plana
    assert len(gist["geometry_mes_log.json"]) == 2


# ── R3: sin ventana horaria de entrada en el Pi: una señal "de hoy" se ejecuta a cualquier hora ─────────────
@pytest.mark.parametrize("hh,mm", [(15, 30), (17, 5), (23, 50)])
def test_R3_pi_enters_outside_the_strategy_window(monkeypatch, gist, sent, hh, mm):
    clock(monkeypatch, hh, mm)
    client = FakeClient()
    arm(monkeypatch, client)
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    pe.run_once()
    assert len(client.placed_orders) == 3                                  # abrio una posicion de 40 contratos fuera de horario
    assert gist["geometry_mes_log.json"][0]["result"] == "FLATTEN"         # ...y se aplana al instante: entrada espuria en el historial


# ── R4: leer el historial falla -> se REEMPLAZA todo el historial por una sola entrada ───────────────────────
def test_R4_gist_read_failure_overwrites_entire_history(monkeypatch):
    import execution.gist_store as gs
    sent_patch = {}

    def bad_get(*a, **k):
        raise ConnectionError("timeout")

    class R:
        def raise_for_status(self): pass
    def fake_patch(url, headers=None, json=None, timeout=None):
        sent_patch["payload"] = json
        return R()
    monkeypatch.setattr(gs.requests, "get", bad_get)
    monkeypatch.setattr(gs.requests, "patch", fake_patch)
    monkeypatch.setattr(gs, "GITHUB_GIST_TOKEN", "x"); monkeypatch.setattr(gs, "GIST_ID", "y")
    monkeypatch.setattr(pe, "_gist_load_log", gs.load_log); monkeypatch.setattr(pe, "_gist_save_log", gs.save_log)

    pe.append_to_historic_log("MES", {"date": "2026-10-05", "result": "TP", "pnl": 2000.0})
    written = json.loads(sent_patch["payload"]["files"]["geometry_mes_log.json"]["content"])
    assert len(written) == 1            # el historial real (todos los dias de paper, el contador de intento) se habria perdido


# ── R5: tras un TP natural, si cancelar el SL falla, nadie avisa y queda un stop huerfano ───────────────────
def test_R5_orphan_stop_after_tp_is_not_reported(monkeypatch, gist, sent):
    clock(monkeypatch, 10, 0)
    client = TpFillsOnFirstPoll()
    client.cancel_order = lambda oid, account_id=None: False               # la API no cancela (success=false)
    arm(monkeypatch, client)
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    pe.run_once()
    assert 102 in client.open_order_ids                                    # el SL sigue vivo con la cuenta ya plana
    assert not any("ABIERTAS" in m or "ALERTA" in m for m in sent)         # ningun aviso de orden huerfana
    assert any("[CLOSE] [TP]" in m for m in sent)


# ── R6: la fijacion de cuenta es opcional: pin vacio + una sola cuenta activa = opera en ESA cuenta ─────────
def test_R6_blank_pin_with_single_active_account_trades_it(monkeypatch, gist, sent):
    clock(monkeypatch, 14, 31)      # cierra el ciclo de inmediato; aqui solo importa EN QUE CUENTA se colocan las ordenes
    client = FakeClient()
    client.accounts = [{"id": 28197705, "name": "150KTC-V2-COMBINE"}]       # solo la Combine activa (p. ej. Practice liquidada/reiniciada)
    arm(monkeypatch, client)
    monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "")                           # variable vacia (asi la crea la plantilla del instalador)
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    pe.run_once()
    assert {o["account_id"] for o in client.placed_orders} == {28197705}   # ordenes REALES en la cuenta Combine


# ── R7: no hay confirmacion del fill de entrada antes/despues de colocar TP y SL ────────────────────────────
def test_R7_exits_are_placed_with_no_check_that_the_entry_filled(monkeypatch, gist, sent):
    clock(monkeypatch, 10, 0)
    client = FakeClient()                                                  # su MARKET "se acepta" pero NUNCA crea una posicion
    calls = {"positions": 0}
    orig = client.get_positions
    def counting(account_id):
        calls["positions"] += 1
        return orig(account_id)
    client.get_positions = counting
    arm(monkeypatch, client)
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    monkeypatch.setattr(pe, "poll_position_until_closed", lambda *a, **k: {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True})
    pe.run_once()
    assert len(client.placed_orders) == 3 and calls["positions"] == 1      # 1 sola lectura de posiciones: la PRE-orden del guard


# ── R8: _find_flatten_fill puede devolver un precio fuera del rango del bracket como "real" ────────────────
def test_R8_flatten_fill_picks_unrelated_order_and_marks_it_real(monkeypatch, gist, sent):
    client = FakeClient()
    client.order_records = {
        100: {"id": 100, "contractId": MES, "filledPrice": 6000.0},        # entrada
        101: {"id": 101, "contractId": MES}, 102: {"id": 102, "contractId": MES},
        117: {"id": 117, "contractId": MES, "filledPrice": 7123.0},        # otra orden del contrato (p. ej. manual) -- precio absurdo
    }
    state = {"phase": "bracket_open", "signal": _signal(date="2026-10-05"), "entry_price": 6000.0, "entry_order_id": 100,
             "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102, "contract_id": MES,
             "account_id": 555, "opened_at": "x"}
    pe._finalize_cycle(client, 555, state, {"result": "FLATTEN", "exit_price": None, "exit_price_estimated": True})
    e = gist["geometry_mes_log.json"][-1]
    assert e["exit"] == 7123.0 and e["exit_price_estimated"] is False      # precio imposible, etiquetado como REAL
    assert e["pnl"] > 100_000                                              # P&L falso gigantesco en el historial


# ── R9: el precio de referencia no revisa la antiguedad de la barra (misma clase del incidente de MGC del 1-oct) ──
def test_R9_reference_price_accepts_a_14_minute_old_bar(monkeypatch):
    client = FakeClient()
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=14)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    client.bars = [{"t": old, "c": 6000.0}]
    assert pe._reference_price(client, MES) == 6000.0                      # TP/SL se anclan a un precio de hace 14 min


# ── R10: dia de liquidacion / posicion cerrada a mano -> mensaje y registro enganosos ───────────────────────
def test_R10_unknown_close_reports_zero_pnl_and_is_invisible_to_the_railway_accounting(monkeypatch, gist, sent):
    client = FakeClient()
    state = {"phase": "bracket_open", "signal": _signal(date="2026-10-05"), "entry_price": 6000.0, "entry_order_id": 100,
             "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102, "contract_id": MES,
             "account_id": 555, "opened_at": "x"}
    pe._finalize_cycle(client, 555, state, {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True})
    assert any("PnL: $+0.00" in m and "[UNKNOWN]" in m for m in sent)
    from scheduler.geometry_scheduler import _attempt_entries, _attempt_pnl
    log_ = gist["geometry_mes_log.json"]
    assert _attempt_entries(log_, 1) == [] and _attempt_pnl(log_, 1) == 0   # Railway no lo cuenta en WR ni en PnL del intento


# ── R2b: bucle abrir -> TP rechazado -> aplanar -> (limpiar señal falla en silencio) -> repetir cada ciclo ──────
def test_R2b_bracket_failure_loops_every_cycle_when_signal_clear_is_dropped(monkeypatch, gist, sent):
    clock(monkeypatch, 10, 0)
    client = FakeClient()
    client.fail_order_type = pe.OrderType.LIMIT           # el TP se rechaza (como el ensayo real del 4-oct)
    arm(monkeypatch, client)
    gist[pe.ORDER_FILE] = _signal(date="2026-10-05")
    gist["__drops__"].add((pe.ORDER_FILE, json.dumps({})))
    for _ in range(4):                                     # 4 ciclos de 120 s = 8 minutos
        pe.run_once()
    entries = [o for o in client.placed_orders if o["order_type"] == pe.OrderType.MARKET]
    assert len(entries) == 4 and len(client.closed_contracts) == 4     # 4 entradas de 40 contratos abiertas y aplanadas
