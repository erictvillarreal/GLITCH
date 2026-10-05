"""
Glitch — Tests de pi/pi_executor.py (29-sep-2026)
====================================================
Cubre el hallazgo #1 del reporte 29-sep-2026: la version pseudocodigo de
este modulo (8 funciones con `raise NotImplementedError`) habria fallado
en el primer ciclo y mandado un error a Telegram cada POLL_SECONDS
indefinidamente. Estos tests prueban que la version real:
  - No toca el broker en absoluto si no hay señal pendiente.
  - No coloca ninguna orden si el gate de Fase 3 (22-sep-2026) no esta
    satisfecho -- y avisa UNA vez por dia, no cada ciclo.
  - Nunca decide compra/venta usando brokers.projectx.OrderSide (bloqueante
    #1, sin verificar) -- solo el mapeo YA verificado.
  - No apila una orden nueva sobre una posicion huerfana no rastreada.
  - No propaga excepciones no manejadas (nunca crashea el loop de main()).
  - Escribe al MISMO historico (geometry_{producto}_log.json) que
    scheduler/geometry_scheduler.py ya usa.

Sin red real en ningun test -- ProjectXClient se reemplaza por un fake
minimo, y execution/gist_store.py se reemplaza por un dict en memoria
(mismo patron que tests/test_geometry_parity.py::TestLoadSaveLogDelegatesToGistStore).
"""
import datetime as dt
import os
import sys

os.environ.setdefault("TOPSTEP_USERNAME", "test-user-not-real")
os.environ.setdefault("TOPSTEP_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
os.environ.setdefault("GLITCH_PRODUCT", "MES")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pi_executor


class FakeClient:
    """Minimo necesario de ProjectXClient para estos tests -- sin red."""

    def __init__(self):
        self.placed_orders = []
        self.cancelled = []
        self.open_order_ids = set()
        self.order_records = {}
        self.positions = []
        self.accounts = [{"id": 555}]
        self.contracts = [{"id": "CON.MES.Z26", "name": "MESZ6", "expirationDate": "2026-12-01"}]
        self.bars = [{"close": 6000.0}]
        self.flattened = False
        self.closed_contracts = []
        self.close_contract_error = None
        self.fail_order_type = None
        self._next_id = 100

    def get_accounts(self, only_active=True):
        return self.accounts

    def get_contracts(self, live=False):
        return self.contracts

    def get_recent_bars(self, contract_id, minutes_back=15, live=False, unit_number=1, limit=50):
        return self.bars

    def place_order(self, account_id, contract_id, order_type, side, size, price=None, stop_price=None):
        if self.fail_order_type is not None and order_type == self.fail_order_type:
            raise RuntimeError("Order failed: Invalid limit price. Limit price not set.")
        oid = self._next_id
        self._next_id += 1
        self.placed_orders.append({
            "id": oid, "account_id": account_id, "contract_id": contract_id,
            "order_type": order_type, "side": side, "size": size,
            "price": price, "stop_price": stop_price,
        })
        self.open_order_ids.add(oid)
        self.order_records[oid] = {"id": oid, "side": side}
        return oid

    def get_open_orders(self, account_id):
        return [{"id": i} for i in self.open_order_ids]

    def get_orders(self, account_id, only_open=False):
        return list(self.order_records.values())

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)
        self.open_order_ids.discard(order_id)
        return True

    def cancel_exit_orders(self, tp_id, sl_id):
        for oid in (tp_id, sl_id):
            try:
                self.cancel_order(oid)
            except Exception:
                pass

    def flatten_position(self, account_id, symbol):
        """El flatten VIEJO (decide el lado con el enum sin verificar) -- el ejecutor ya NO debe llamarlo."""
        raise AssertionError("pi_executor no debe usar flatten_position() (depende de OrderSide sin verificar y de netPos)")

    def close_contract(self, account_id, contract_id):
        if self.close_contract_error:
            raise RuntimeError(self.close_contract_error)
        self.flattened = True
        self.closed_contracts.append((account_id, contract_id))
        return {"success": True}

    def get_positions(self, account_id):
        return self.positions


def _raise_if_called(*a, **k):
    raise AssertionError("no deberia autenticar / tocar el broker en este caso")


def _signal(**overrides):
    base = {
        "date": "2026-09-29", "side": 1, "direction": "LONG", "product_code": "MES",
        "nc": 40, "sl_ticks": 100, "tp_ticks": 40, "product": "MES", "intento": 1, "dry_run": False,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch):
    """Reloj fijo (29-sep-2026 10:00 CT): la guardia de señal vieja compara contra la fecha de hoy, y las señales
    de prueba traen esa fecha. Los tests que necesitan otra hora la sobreescriben con su propio monkeypatch."""
    monkeypatch.setattr(pi_executor, "ct_now", lambda: dt.datetime(2026, 9, 29, 10, 0, tzinfo=pi_executor.CT))


@pytest.fixture
def fake_gist(monkeypatch):
    store = {}

    def _load_state(filename):
        return store.get(filename, {})

    def _save_state(filename, data):
        store[filename] = data

    def _load_log(filename):
        return store.get(filename, [])

    def _save_log(filename, data):
        store[filename] = data

    monkeypatch.setattr(pi_executor, "_gist_load_state", _load_state)
    monkeypatch.setattr(pi_executor, "_gist_save_state", _save_state)
    monkeypatch.setattr(pi_executor, "_gist_load_log", _load_log)
    monkeypatch.setattr(pi_executor, "_gist_save_log", _save_log)
    return store


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(pi_executor, "send", lambda msg: messages.append(msg))
    return messages


class TestNoSignalIsQuiet:
    """Ciclo normal, sin señal -- ni Telegram ni el broker deben tocarse."""

    def test_no_pending_signal_never_touches_broker_or_telegram(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        pi_executor.run_once()
        assert sent == []


class TestReconcileNoop:
    def test_empty_pi_state_does_nothing(self, fake_gist, monkeypatch):
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        pi_executor.reconcile_if_needed()  # no debe lanzar, no debe tocar el broker


class TestGateBlocksWithoutTouchingBroker:
    """Gate de Fase 3 (22-sep-2026) -- ver docstring del modulo."""

    def test_blocked_when_phase3_disabled(self, fake_gist, sent, monkeypatch):
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", False)
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)

        pi_executor.run_once()

        assert len(sent) == 1
        assert "BLOCKED" in sent[0]
        assert fake_gist[pi_executor.ORDER_FILE] == _signal()  # señal intacta, nunca consumida

    def test_blocked_when_phase3_enabled_but_no_verified_map(self, fake_gist, sent, monkeypatch):
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map", lambda: None)
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)

        pi_executor.run_once()

        assert len(sent) == 1
        assert "BLOCKED" in sent[0]

    def test_blocked_notice_rate_limited_to_once_per_day(self, fake_gist, sent, monkeypatch):
        """Hallazgo #1 del reporte 29-sep-2026: la version pseudocodigo
        habria mandado esto cada POLL_SECONDS. Esta version avisa una vez
        por dia calendario por la misma razon."""
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", False)
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)

        pi_executor.run_once()
        pi_executor.run_once()
        pi_executor.run_once()

        assert len(sent) == 1


class TestVerifiedSideMap:
    """Bloqueante #1 -- el mapeo de compra/venta NUNCA sale de
    brokers.projectx.OrderSide (sin verificar), solo del artefacto
    verificado."""

    def test_missing_file_returns_none(self, monkeypatch):
        monkeypatch.setattr(pi_executor, "ORDERSIDE_VERIFIED_PATH", "/no/existe/orderside_verified.json")
        assert pi_executor._load_verified_side_map() is None

    def test_orderside_verified_requires_both_phase3_and_map(self, monkeypatch):
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", False)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0})
        assert pi_executor._orderside_verified() is False

        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        assert pi_executor._orderside_verified() is True

    def test_resolve_side_uses_verified_map_not_projectx_enum(self):
        """Sentinelas deliberadamente distintos de OrderSide.BID(0)/ASK(1)
        -- si esto pasara, seria porque el codigo cayo de vuelta al enum
        sin verificar en vez de usar el mapeo pasado explicitamente."""
        verified = {"BUY_SIDE_INT": 42, "SELL_SIDE_INT": 13}
        assert pi_executor._resolve_side(1, verified) == 42
        assert pi_executor._resolve_side(-1, verified) == 13


class TestUntrackedPositionGuard:
    """Riesgo residual documentado en el modulo: si el broker ya muestra
    una posicion que PI_STATE_FILE no conoce, no se apila una orden nueva."""

    def test_refuses_new_order_when_broker_shows_untracked_position(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.positions = [{"contractId": "CON.MES.Z26", "type": 1, "size": 3, "averagePrice": 6000.0}]
        monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0})
        fake_gist[pi_executor.ORDER_FILE] = _signal()

        pi_executor.run_once()

        assert client.placed_orders == []
        assert any("BLOCKED" in m for m in sent)
        assert fake_gist[pi_executor.ORDER_FILE] == _signal()  # no se consumio


class TestHappyPathPlacesBracketAndLogs:
    def test_full_cycle_forced_flatten_at_session_close(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map",
                             lambda: {"BUY_SIDE_INT": 9, "SELL_SIDE_INT": 7})
        # 14:31 CT >= FLATTEN_HOUR:FLATTEN_MINUTE (14:30) -- fuerza el cierre
        # de sesion en el PRIMER poll, para no correr un loop real.
        monkeypatch.setattr(pi_executor, "ct_now",
                             lambda: dt.datetime(2026, 9, 29, 14, 31, tzinfo=pi_executor.CT))

        fake_gist[pi_executor.ORDER_FILE] = _signal()

        pi_executor.run_once()

        entry_order, tp_order, sl_order = client.placed_orders
        assert entry_order["side"] == 9   # BUY_SIDE_INT verificado -- direction=+1 (LONG)
        assert tp_order["side"] == 7       # SELL_SIDE_INT verificado -- salida de un LONG
        assert sl_order["side"] == 7
        assert entry_order["contract_id"] == "CON.MES.Z26"

        assert fake_gist[pi_executor.ORDER_FILE] == {}
        assert fake_gist[pi_executor.PI_STATE_FILE] == {}

        log_entries = fake_gist["geometry_mes_log.json"]
        assert len(log_entries) == 1
        assert log_entries[0]["result"] == "FLATTEN"
        assert log_entries[0]["product"] == "MES"
        assert log_entries[0]["intento"] == 1
        assert log_entries[0]["dry_run"] is False

        assert any("[OPEN]" in m for m in sent)
        assert any("[CLOSE]" in m for m in sent)
        assert client.flattened is True
        assert client.closed_contracts == [(555, "CON.MES.Z26")]


class TestReconcileResumesInterruptedBracket:
    """A diferencia de geometry_scheduler.py::_reconcile_pending_position
    (que adivina desde el precio), aqui se pregunta al broker directamente."""

    def test_resumes_using_broker_state_and_finalizes_as_tp(self, fake_gist, monkeypatch):
        client = FakeClient()
        tp_id, sl_id, entry_id = 201, 202, 200
        client.open_order_ids = {sl_id}  # TP ya no esta abierto -> se lleno
        client.order_records = {tp_id: {"id": tp_id, "avgFillPrice": 6050.0}}

        state = {
            "phase": "bracket_open",
            "signal": _signal(),
            "entry_price": 6000.0, "entry_order_id": entry_id,
            "tp_price": 6050.0, "sl_price": 5975.0,
            "tp_order_id": tp_id, "sl_order_id": sl_id, "contract_id": "CON.MES.Z26",
            "account_id": 555, "opened_at": "2026-09-29 10:00 UTC",
        }
        fake_gist[pi_executor.PI_STATE_FILE] = state
        monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
        monkeypatch.setattr(pi_executor, "ct_now",
                             lambda: dt.datetime(2026, 9, 29, 10, 5, tzinfo=pi_executor.CT))
        monkeypatch.setattr(pi_executor, "send", lambda msg: None)

        pi_executor.reconcile_if_needed()

        assert fake_gist[pi_executor.PI_STATE_FILE] == {}
        log_entries = fake_gist["geometry_mes_log.json"]
        assert len(log_entries) == 1
        assert log_entries[0]["result"] == "TP"
        assert log_entries[0]["exit"] == 6050.0
        assert sl_id in client.cancelled


class TestUnhandledExceptionDoesNotCrash:
    def test_exception_is_caught_and_reported_not_raised(self, fake_gist, sent, monkeypatch):
        def _boom():
            raise RuntimeError("network exploded")

        monkeypatch.setattr(pi_executor, "authenticate", _boom)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map",
                             lambda: {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0})
        fake_gist[pi_executor.ORDER_FILE] = _signal()

        pi_executor.run_once()  # NO debe propagar la excepcion

        assert any("excepcion no manejada" in m for m in sent)


class TestAppendToHistoricLog:
    def test_appends_to_same_filename_geometry_scheduler_uses(self, fake_gist):
        fake_gist["geometry_mes_log.json"] = [{"date": "2026-09-01", "result": "TP", "pnl": 100}]
        pi_executor.append_to_historic_log("MES", {"date": "2026-09-29", "result": "SL", "pnl": -50})
        assert fake_gist["geometry_mes_log.json"] == [
            {"date": "2026-09-01", "result": "TP", "pnl": 100},
            {"date": "2026-09-29", "result": "SL", "pnl": -50},
        ]


class TestResolveContractId:
    def test_matches_by_product_code_substring_and_picks_front_month(self):
        client = FakeClient()
        client.contracts = [
            {"id": "CON.MES.H27", "name": "MESH7", "expirationDate": "2027-03-01"},
            {"id": "CON.MES.Z26", "name": "MESZ6", "expirationDate": "2026-12-01"},
        ]
        contract = pi_executor.resolve_contract_id(client, "MES")
        assert contract["id"] == "CON.MES.Z26"  # vencimiento mas cercano

    def test_raises_when_no_match(self):
        client = FakeClient()
        client.contracts = [{"id": "CON.MGC.Z26", "name": "MGCZ6", "expirationDate": "2026-12-01"}]
        with pytest.raises(RuntimeError):
            pi_executor.resolve_contract_id(client, "MES")


class TestSessionEndFlattenUsesCloseContract:
    """03-oct-2026: client.flatten_position() decidia el lado de cierre con brokers.projectx.OrderSide (enum SIN
    verificar, bloqueante #1) y leia `netPos` (campo tampoco verificado). Con el enum invertido, "cerrar" un LONG
    compraria MAS; con `netPos` ausente no cerraria nada y aun asi reportaria FLATTEN. El cierre ahora usa
    closeContract, que no depende del lado."""

    def _poll_at_close(self, client, monkeypatch, sent):
        monkeypatch.setattr(pi_executor, "ct_now", lambda: dt.datetime(2026, 10, 1, 14, 31, tzinfo=pi_executor.CT))
        monkeypatch.setattr(pi_executor, "send", lambda m: sent.append(m))
        return pi_executor.poll_position_until_closed(client, 555, "CON.MES.Z26", 1, 2, 6050.0, 5975.0,
                                                       poll_interval=0)

    def test_flatten_calls_close_contract_and_cancels_exit_orders(self, monkeypatch):
        client, sent = FakeClient(), []
        out = self._poll_at_close(client, monkeypatch, sent)
        assert out["result"] == "FLATTEN"
        assert "flatten_failed" not in out
        assert client.closed_contracts == [(555, "CON.MES.Z26")]
        assert set(client.cancelled) == {1, 2}
        assert sent == []

    def test_flatten_failure_alerts_loudly_and_is_flagged(self, monkeypatch):
        client, sent = FakeClient(), []
        client.close_contract_error = "closeContract fallo: boom"
        out = self._poll_at_close(client, monkeypatch, sent)
        assert out["result"] == "FLATTEN" and out["flatten_failed"] is True
        assert len(sent) == 1 and "ABIERTA" in sent[0] and "MANUALMENTE" in sent[0]

    def test_flatten_failure_is_recorded_in_the_historic_log(self, fake_gist, monkeypatch):
        client = FakeClient()
        state = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 200,
                 "tp_price": 6050.0, "sl_price": 5975.0, "tp_order_id": 1, "sl_order_id": 2,
                 "contract_id": "CON.MES.Z26", "account_id": 555, "opened_at": "2026-10-01 10:00 UTC"}
        monkeypatch.setattr(pi_executor, "send", lambda m: None)
        pi_executor._finalize_cycle(client, 555, state, {"result": "FLATTEN", "exit_price": None,
                                                         "exit_price_estimated": True, "flatten_failed": True})
        assert fake_gist["geometry_mes_log.json"][0]["flatten_failed"] is True

    def test_normal_close_does_not_add_the_flag_to_the_log(self, fake_gist, monkeypatch):
        client = FakeClient()
        state = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 200,
                 "tp_price": 6050.0, "sl_price": 5975.0, "tp_order_id": 1, "sl_order_id": 2,
                 "contract_id": "CON.MES.Z26", "account_id": 555, "opened_at": "2026-10-01 10:00 UTC"}
        monkeypatch.setattr(pi_executor, "send", lambda m: None)
        pi_executor._finalize_cycle(client, 555, state, {"result": "FLATTEN", "exit_price": None, "exit_price_estimated": True})
        assert "flatten_failed" not in fake_gist["geometry_mes_log.json"][0]

    def test_executor_source_no_longer_calls_the_unverified_flatten(self):
        """Ninguna LINEA DE CODIGO (los comentarios que explican el cambio no cuentan) llama flatten_position()."""
        import inspect
        code_lines = [l for l in inspect.getsource(pi_executor).splitlines() if not l.lstrip().startswith("#")]
        assert not any("flatten_position(" in l for l in code_lines)


class TestOpenBracketHeartbeat:
    """Sin heartbeat el log queda mudo durante todo un trade y el watchdog daria falsa alarma."""

    def test_heartbeat_logged_every_n_polls_while_bracket_is_open(self, monkeypatch, caplog):
        import logging
        client = FakeClient()
        client.open_order_ids = {1, 2}            # TP y SL siguen abiertos: la posicion no se resuelve
        calls = {"n": 0}

        def _clock():
            calls["n"] += 1
            hh, mm = (10, 0) if calls["n"] <= 25 else (14, 31)    # 25 polls, luego cierre de sesion
            return dt.datetime(2026, 10, 1, hh, mm, tzinfo=pi_executor.CT)

        monkeypatch.setattr(pi_executor, "ct_now", _clock)
        monkeypatch.setattr(pi_executor, "send", lambda m: None)
        monkeypatch.setattr(pi_executor.time, "sleep", lambda s: None)
        with caplog.at_level(logging.INFO):
            out = pi_executor.poll_position_until_closed(client, 555, "CON.MES.Z26", 1, 2, 6050.0, 5975.0,
                                                          poll_interval=0)
        beats = [r for r in caplog.records if "heartbeat" in r.getMessage()]
        assert out["result"] == "FLATTEN"
        assert len(beats) == 25 // pi_executor.HEARTBEAT_EVERY_POLLS     # polls 10 y 20

    def test_heartbeat_interval_is_well_inside_the_watchdog_threshold(self):
        import watchdog  # noqa: F401 -- pi/ops en sys.path via test_pi_ops
        heartbeat_s = pi_executor.HEARTBEAT_EVERY_POLLS * pi_executor.POSITION_POLL_INTERVAL
        assert heartbeat_s < 10 * 60


# ── Arreglos del 4-oct-2026 (hallazgos de la primera corrida real de verify_orderside_demo.py) ──────────────
from brokers import projectx as px


class TestPositionShapeIsTypeAndSize:
    """La forma REAL de una posicion (4-oct-2026) es type(1=Long,2=Short)+size; `netPos` no existe."""

    def test_position_net_reads_type_and_size(self):
        assert px.position_net({"type": 1, "size": 2}) == 2
        assert px.position_net({"type": 2, "size": 3}) == -3

    def test_position_net_still_accepts_netpos_for_compat(self):
        assert px.position_net({"netPos": -4}) == -4

    def test_position_net_is_zero_when_undeterminable(self):
        assert px.position_net({}) == 0
        assert px.position_net({"type": 3, "size": 1}) == 0
        assert px.position_net({"type": 1, "size": 0}) == 0

    def test_real_open_position_record_counts_as_open(self):
        real = {"id": 868047983, "accountId": 28197753, "contractId": "CON.F.US.MES.Z26",
                "contractDisplayName": "MESZ26", "type": 1, "size": 1, "averagePrice": 7788.5}
        assert px.position_is_open(real) is True

    def test_recognized_zero_size_is_flat(self):
        assert px.position_is_open({"type": 1, "size": 0}) is False
        assert px.position_is_open({"netPos": 0}) is False

    def test_unrecognized_shape_in_an_open_listing_is_treated_as_open(self):
        """Ante la duda, abstenerse: el endpoint solo lista posiciones abiertas."""
        assert px.position_is_open({"contractId": "X"}) is True


class TestUntrackedGuardWithRealShape:
    def test_detects_real_shaped_position_on_this_contract(self):
        c = FakeClient()
        c.positions = [{"contractId": "CON.MES.Z26", "type": 2, "size": 1}]
        assert pi_executor._has_untracked_position(c, 555, "CON.MES.Z26") is True

    def test_ignores_positions_on_other_contracts(self):
        c = FakeClient()
        c.positions = [{"contractId": "CON.F.US.MGC.Z26", "type": 1, "size": 1}]
        assert pi_executor._has_untracked_position(c, 555, "CON.MES.Z26") is False

    def test_flat_account_is_clean(self):
        assert pi_executor._has_untracked_position(FakeClient(), 555, "CON.MES.Z26") is False

    def test_broker_error_abstains_for_safety(self):
        c = FakeClient()
        c.get_positions = lambda account_id: (_ for _ in ()).throw(RuntimeError("boom"))
        assert pi_executor._has_untracked_position(c, 555, "CON.MES.Z26") is True


class TestClientUsesVerifiedEndpoints:
    def _client(self, monkeypatch, response):
        c = px.ProjectXClient(px.ProjectXCredentials("u", "k"), verbose=False)
        calls = []
        monkeypatch.setattr(c, "ensure_auth", lambda: None)
        monkeypatch.setattr(c, "_post", lambda path, payload: (calls.append((path, payload)), response)[1])
        return c, calls

    def test_get_positions_hits_searchopen(self, monkeypatch):
        c, calls = self._client(monkeypatch, {"positions": [{"size": 1, "type": 1}], "success": True})
        assert c.get_positions(7) == [{"size": 1, "type": 1}]
        assert calls == [("/api/Position/searchOpen", {"accountId": 7})]

    def test_get_open_orders_hits_searchopen(self, monkeypatch):
        c, calls = self._client(monkeypatch, {"orders": [], "success": True})
        assert c.get_open_orders(7) == []
        assert calls == [("/api/Order/searchOpen", {"accountId": 7})]

    def test_is_flat_uses_real_shape(self, monkeypatch):
        c, _ = self._client(monkeypatch, {"positions": [{"type": 1, "size": 1}], "success": True})
        assert c.is_flat(7) is False
        c2, _ = self._client(monkeypatch, {"positions": [], "success": True})
        assert c2.is_flat(7) is True


class TestRecentBarsRequestFormat:
    def _client(self, monkeypatch, response):
        c = px.ProjectXClient(px.ProjectXCredentials("u", "k"), verbose=False)
        calls = []
        monkeypatch.setattr(c, "ensure_auth", lambda: None)
        monkeypatch.setattr(c, "_post", lambda path, payload: (calls.append((path, payload)), response)[1])
        return c, calls

    def test_request_uses_real_api_fields(self, monkeypatch):
        c, calls = self._client(monkeypatch, {"bars": [], "success": True})
        c.get_recent_bars("CON.F.US.MES.Z26", minutes_back=15)
        path, body = calls[0]
        assert path == "/api/History/retrieveBars"
        assert set(body) == {"contractId", "live", "startTime", "endTime", "unit", "unitNumber", "limit",
                             "includePartialBar"}
        assert body["unit"] == 2 and body["unitNumber"] == 1 and body["live"] is False
        assert body["startTime"] < body["endTime"] and body["endTime"].endswith("Z")

    def test_bars_sorted_oldest_to_newest_whatever_the_api_order(self, monkeypatch):
        newest_first = [{"t": "2026-10-04T23:59:00+00:00", "c": 6100.0}, {"t": "2026-10-04T23:58:00+00:00", "c": 6099.0}]
        c, _ = self._client(monkeypatch, {"bars": newest_first, "success": True})
        assert c.get_recent_bars("X")[-1]["c"] == 6100.0

    def test_reference_price_reads_c_from_last_bar(self):
        cl = FakeClient(); cl.bars = [{"t": "1", "c": 6099.0}, {"t": "2", "c": 6100.25}]
        assert pi_executor._reference_price(cl, "X") == 6100.25

    def test_reference_price_refuses_without_bars(self):
        cl = FakeClient(); cl.bars = []
        with pytest.raises(RuntimeError, match="no se coloca la orden"):
            pi_executor._reference_price(cl, "X")


class TestLimitOrderPayloadUsesLimitPrice:
    def test_limit_order_sends_limitPrice_not_price(self, monkeypatch):
        c = px.ProjectXClient(px.ProjectXCredentials("u", "k"), verbose=False)
        calls = []
        monkeypatch.setattr(c, "ensure_auth", lambda: None)
        monkeypatch.setattr(c, "_post", lambda path, payload: (calls.append((path, payload)),
                                                                {"success": True, "orderId": 5})[1])
        c.place_order(1, "CON.X", px.OrderType.LIMIT, px.OrderSide.ASK, 1, price=7800.25)
        _, body = calls[0]
        assert body["limitPrice"] == 7800.25 and "price" not in body


class TestBracketFailureNeverLeavesNakedPosition:
    def _setup(self, monkeypatch, client):
        monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map",
                             lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})

    def test_tp_rejected_after_entry_flattens_clears_signal_and_alerts(self, fake_gist, sent, monkeypatch):
        client = FakeClient(); client.fail_order_type = px.OrderType.LIMIT
        self._setup(monkeypatch, client)
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        pi_executor.run_once()
        assert len(client.placed_orders) == 1                      # solo la entrada
        assert client.closed_contracts == [(555, "CON.MES.Z26")]   # aplanada
        assert fake_gist[pi_executor.ORDER_FILE] == {}             # sin bucle de reintentos
        assert not fake_gist.get(pi_executor.PI_STATE_FILE)        # nada a medias
        assert any("ALERTA" in m and "aplano automaticamente" in m for m in sent)

    def test_sl_rejected_cancels_tp_and_flattens(self, fake_gist, sent, monkeypatch):
        client = FakeClient(); client.fail_order_type = px.OrderType.STOP
        self._setup(monkeypatch, client)
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        pi_executor.run_once()
        assert len(client.placed_orders) == 2
        assert client.cancelled == [client.placed_orders[1]["id"]]  # el TP que si se coloco
        assert client.closed_contracts == [(555, "CON.MES.Z26")]
        assert fake_gist[pi_executor.ORDER_FILE] == {}

    def test_if_emergency_flatten_also_fails_alert_says_close_manually(self, fake_gist, sent, monkeypatch):
        client = FakeClient(); client.fail_order_type = px.OrderType.LIMIT
        client.close_contract_error = "boom"
        self._setup(monkeypatch, client)
        fake_gist[pi_executor.ORDER_FILE] = _signal()
        pi_executor.run_once()
        assert any("MANUALMENTE" in m and "boom" in m for m in sent)
        assert fake_gist[pi_executor.ORDER_FILE] == {}


class TestTickRounding:
    def test_prices_are_rounded_to_tick(self):
        assert pi_executor._round_to_tick(7788.8) == 7788.75
        assert pi_executor._round_to_tick(7788.9) == 7789.0


class TestResolveAccountId:
    TWO = [{"id": 28197705}, {"id": 28197753}]

    def test_pinned_account_is_used_even_with_two_active(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "28197753")
        c = FakeClient(); c.accounts = list(self.TWO)
        assert pi_executor._resolve_account_id(c) == 28197753

    def test_two_active_without_pin_refuses_to_guess(self, monkeypatch):
        monkeypatch.delenv("TOPSTEP_ACCOUNT_ID", raising=False)
        c = FakeClient(); c.accounts = list(self.TWO)
        with pytest.raises(RuntimeError, match="TOPSTEP_ACCOUNT_ID"):
            pi_executor._resolve_account_id(c)

    def test_pin_not_among_active_accounts_refuses(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "999")
        c = FakeClient(); c.accounts = list(self.TWO)
        with pytest.raises(RuntimeError, match="no esta entre las cuentas activas"):
            pi_executor._resolve_account_id(c)

    def test_single_active_account_needs_no_pin(self, monkeypatch):
        monkeypatch.delenv("TOPSTEP_ACCOUNT_ID", raising=False)
        c = FakeClient(); c.accounts = [{"id": 555}]
        assert pi_executor._resolve_account_id(c) == 555

    def test_blank_pin_is_ignored(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "  ")
        c = FakeClient(); c.accounts = [{"id": 555}]
        assert pi_executor._resolve_account_id(c) == 555

    def test_no_active_accounts_raises(self, monkeypatch):
        monkeypatch.delenv("TOPSTEP_ACCOUNT_ID", raising=False)
        c = FakeClient(); c.accounts = []
        with pytest.raises(RuntimeError, match="Sin cuentas activas"):
            pi_executor._resolve_account_id(c)


class TestStaleSignalIsDiscarded:
    """El viernes 2-oct quedo una señal LONG 40 sin consumir; con el gate abierto se habria ejecutado dias
    despues, y ademas el scheduler del lunes se habria negado a escribir la nueva."""

    def test_old_signal_is_cleared_and_announced_without_touching_broker(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
        fake_gist[pi_executor.ORDER_FILE] = _signal(date="2026-09-26")

        pi_executor.run_once()

        assert fake_gist[pi_executor.ORDER_FILE] == {}
        assert len(sent) == 1 and "VIEJA" in sent[0] and "2026-09-26" in sent[0]

    def test_old_signal_is_cleared_even_while_gate_is_closed(self, fake_gist, sent, monkeypatch):
        """Si no se limpiara con el gate cerrado, la señal vieja bloquearia al scheduler de Railway."""
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", False)
        fake_gist[pi_executor.ORDER_FILE] = _signal(date="2026-09-26")

        pi_executor.run_once()

        assert fake_gist[pi_executor.ORDER_FILE] == {}

    def test_todays_signal_is_not_touched_by_the_guard(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", False)
        fake_gist[pi_executor.ORDER_FILE] = _signal()  # fecha de hoy segun el reloj fijo

        pi_executor.run_once()

        assert fake_gist[pi_executor.ORDER_FILE] == _signal()
        assert "BLOCKED" in sent[0] and "VIEJA" not in sent[0]

    @pytest.mark.parametrize("bad_date", ["2026-09-30", "", "ayer", None])
    def test_future_or_garbled_date_is_neither_executed_nor_cleared(self, bad_date, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pi_executor, "authenticate", _raise_if_called)
        monkeypatch.setattr(pi_executor, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pi_executor, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
        sig = _signal(date=bad_date)
        fake_gist[pi_executor.ORDER_FILE] = sig

        pi_executor.run_once()

        assert fake_gist[pi_executor.ORDER_FILE] == sig
        assert len(sent) == 1 and "BLOCKED" in sent[0]
