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
        self._next_id = 100

    def get_accounts(self, only_active=True):
        return self.accounts

    def get_contracts(self, live=False):
        return self.contracts

    def get_bars(self, contract_id, bar_type=1, bar_size=1, count=1, live=False):
        return self.bars

    def place_order(self, account_id, contract_id, order_type, side, size, price=None, stop_price=None):
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
        self.flattened = True
        return {"flattened_orders": []}

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
        client.positions = [{"contractId": "CON.MES.Z26", "netPos": 3}]
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
