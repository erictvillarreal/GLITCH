"""
Glitch -- Tests de los parches de la auditoria del 04-oct-2026 (rama audit/2026-10-04).

Cada clase cubre UN hallazgo de AUDIT_2026-10-04.md. Las reproducciones del defecto original viven en
audit/2026-10-04/test_repro_defects.py (afirman el comportamiento defectuoso y dejan de pasar al aplicar los parches);
aqui estan las versiones permanentes que afirman el comportamiento CORRECTO.

Sin red: ProjectXClient se reemplaza por un fake y gist_store por un dict en memoria (ver tests/test_pi_executor.py).
"""
import datetime as dt
import json
import os
import sys

os.environ.setdefault("TOPSTEP_USERNAME", "test-user-not-real")
os.environ.setdefault("TOPSTEP_API_KEY", "test-key-not-real")
os.environ.setdefault("TOPSTEP_ACCOUNT_ID", "555")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
os.environ.setdefault("GLITCH_PRODUCT", "MES")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pe
# Reutiliza el FakeClient/fixtures de la suite del ejecutor (mismos supuestos, un solo lugar donde mantenerlos)
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent, _fixed_clock  # noqa: F401

MES = "CON.MES.Z26"


def _arm(monkeypatch, client):
    """Gate de Fase 3 abierto, mapa de lados de ensayo, cuenta fijada en 555, sin dormir de verdad."""
    monkeypatch.setattr(pe, "authenticate", lambda: client)
    monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
    monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
    monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "555")
    monkeypatch.setattr(pe.time, "sleep", lambda s: None)


def _set_clock(monkeypatch, hh, mm):
    monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(2026, 9, 29, hh, mm, tzinfo=pe.CT))


def _drop_signal_clear(monkeypatch, store):
    """Simula gist_store._write_file: el PATCH que limpia la señal FALLA EN SILENCIO (nada se escribe, nadie lo sabe)."""
    orig = pe._gist_save_state

    def save(filename, data):
        if filename == pe.ORDER_FILE and data == {}:
            return
        store[filename] = data
    monkeypatch.setattr(pe, "_gist_save_state", save)
    return orig


class TpFillsEachCycle(FakeClient):
    """El TP del bracket de cada ciclo se llena en el primer poll -> resolucion natural 'TP'."""
    def __init__(self):
        super().__init__()
        self.tp_pending = None

    def place_order(self, account_id, contract_id, order_type, side, size, price=None, stop_price=None):
        oid = super().place_order(account_id, contract_id, order_type, side, size, price=price, stop_price=stop_price)
        if order_type == pe.OrderType.LIMIT:
            self.tp_pending = oid
        return oid

    def get_open_orders(self, account_id):
        if self.tp_pending is not None:
            self.open_order_ids.discard(self.tp_pending)
            self.tp_pending = None
        return super().get_open_orders(account_id)


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A1 -- una señal real se ejecuta A LO MAS UNA VEZ aunque falle (en silencio) la escritura que la limpia
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
class TestSignalIsExecutedAtMostOnce:
    def test_second_cycle_does_not_reenter_when_the_signal_clear_write_fails(self, fake_gist, sent, monkeypatch):
        client = TpFillsEachCycle()
        _arm(monkeypatch, client)
        sig = _signal()
        fake_gist[pe.ORDER_FILE] = sig
        _drop_signal_clear(monkeypatch, fake_gist)

        pe.run_once()
        assert len(client.placed_orders) == 3                       # trade 1
        assert fake_gist[pe.ORDER_FILE] == sig                      # la limpieza fallo: la señal sigue en el Gist

        pe.run_once()
        pe.run_once()
        assert len(client.placed_orders) == 3                       # NO hay trade 2 ni 3
        assert len(fake_gist["geometry_mes_log.json"]) == 1

    def test_bracket_failure_does_not_loop_every_cycle_when_the_signal_clear_write_fails(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.fail_order_type = pe.OrderType.LIMIT                  # el TP se rechaza (como el ensayo real del 4-oct)
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal()
        _drop_signal_clear(monkeypatch, fake_gist)

        for _ in range(4):
            pe.run_once()

        entries = [o for o in client.placed_orders if o["order_type"] == pe.OrderType.MARKET]
        assert len(entries) == 1 and len(client.closed_contracts) == 1   # una sola entrada, no una por ciclo

    def test_marker_is_written_before_the_entry_order(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal()
        _set_clock(monkeypatch, 14, 31)
        seen = {}
        orig = client.place_order

        def spy(account_id, contract_id, order_type, side, size, **kw):
            seen.setdefault("marker_existed_at_first_order", os.path.exists(pe._executed_marker_path()))
            return orig(account_id, contract_id, order_type, side, size, **kw)
        client.place_order = spy

        pe.run_once()
        assert seen["marker_existed_at_first_order"] is True

    def test_marker_records_the_signal_date(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal()
        _set_clock(monkeypatch, 14, 31)
        pe.run_once()
        with open(pe._executed_marker_path()) as f:
            assert json.load(f)["date"] == "2026-09-29"

    def test_an_old_marker_does_not_block_a_new_day(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        os.makedirs(os.path.dirname(pe._executed_marker_path()), exist_ok=True)
        with open(pe._executed_marker_path(), "w") as f:
            json.dump({"date": "2026-09-28"}, f)                     # ayer
        fake_gist[pe.ORDER_FILE] = _signal()                         # hoy (29-sep)
        _set_clock(monkeypatch, 14, 31)
        pe.run_once()
        assert len(client.placed_orders) == 3

    def test_already_claimed_signal_is_discarded_cleared_and_alerted_once(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        os.makedirs(os.path.dirname(pe._executed_marker_path()), exist_ok=True)
        with open(pe._executed_marker_path(), "w") as f:
            json.dump({"date": "2026-09-29"}, f)
        fake_gist[pe.ORDER_FILE] = _signal()

        pe.run_once()
        assert client.placed_orders == []
        assert fake_gist[pe.ORDER_FILE] == {}                        # se limpia
        fake_gist[pe.ORDER_FILE] = _signal()                         # si la limpieza fallara y volviera a verse...
        pe.run_once()
        pe.run_once()
        assert client.placed_orders == []
        assert len([m for m in sent if "ya se ejecuto" in m]) == 1   # ...el aviso no se repite cada ciclo

    def test_unwritable_marker_means_no_trade(self, fake_gist, sent, monkeypatch, tmp_path):
        client = FakeClient()
        _arm(monkeypatch, client)
        blocker = tmp_path / "es_un_archivo"
        blocker.write_text("x")
        monkeypatch.setenv("GLITCH_PI_STATE_DIR", str(blocker))      # makedirs/open fallan -> no se puede reclamar
        fake_gist[pe.ORDER_FILE] = _signal()
        _set_clock(monkeypatch, 14, 31)
        pe.run_once()
        assert client.placed_orders == []                            # sin marcador no se opera
        assert any("excepcion no manejada" in m for m in sent)

    def test_unreadable_marker_fails_safe(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        os.makedirs(os.path.dirname(pe._executed_marker_path()), exist_ok=True)
        with open(pe._executed_marker_path(), "w") as f:
            f.write("{{{ no es json")
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        assert client.placed_orders == []

    def test_test_signals_are_exempt_from_the_marker_so_trials_can_repeat(self, fake_gist, sent, monkeypatch):
        """Los ensayos (product != GLITCH_PRODUCT, p. ej. MEStest) escriben a su propio historial y se repiten el mismo dia."""
        client = FakeClient()
        _arm(monkeypatch, client)
        _set_clock(monkeypatch, 14, 31)
        for _ in range(2):
            fake_gist[pe.ORDER_FILE] = _signal(product="MEStest", nc=1)
            pe.run_once()
        assert len([o for o in client.placed_orders if o["order_type"] == pe.OrderType.MARKET]) == 2
        assert "geometry_mestest_log.json" in fake_gist and "geometry_mes_log.json" not in fake_gist


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A2 -- un ciclo NO se da por cerrado sin comprobar que la cuenta quedo plana y sin ordenes huerfanas
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
import brokers.projectx as px

TP_ID, SL_ID = 101, 102


def _poll(client, monkeypatch, sent=None, max_polls=40):
    """Corre poll_position_until_closed con reloj de 10:00 que SALTA a 14:31 tras `max_polls` lecturas de reloj
    (red de seguridad: si algo entrara en bucle, el flatten de fin de sesion corta el poll en vez de colgar la suite)."""
    n = {"c": 0}

    def clk():
        n["c"] += 1
        hh, mm = (10, 0) if n["c"] <= max_polls else (14, 31)
        return dt.datetime(2026, 9, 29, hh, mm, tzinfo=pe.CT)
    monkeypatch.setattr(pe, "ct_now", clk)
    monkeypatch.setattr(pe.time, "sleep", lambda s: None)
    if sent is not None:
        monkeypatch.setattr(pe, "send", lambda m: sent.append(m))
    return pe.poll_position_until_closed(client, 555, MES, TP_ID, SL_ID, 6010.0, 5975.0, poll_interval=0)


def _open_position(size=40, type_=1):
    return {"id": 9, "accountId": 555, "contractId": MES, "type": type_, "size": size, "averagePrice": 6000.0}


class SeqOpenOrders(FakeClient):
    """get_open_orders devuelve, en orden, los conjuntos de `seq` (el ultimo se repite). Un elemento Exception se lanza."""
    def __init__(self, seq):
        super().__init__()
        self.seq, self.i = list(seq), 0

    def get_open_orders(self, account_id):
        item = self.seq[min(self.i, len(self.seq) - 1)]
        self.i += 1
        if isinstance(item, Exception):
            raise item
        return [{"id": x} for x in item]


class TestStrictBrokerReaders:
    def _client(self, monkeypatch, resp):
        c = px.ProjectXClient(px.ProjectXCredentials("u", "k"), verbose=False)
        monkeypatch.setattr(c, "ensure_auth", lambda: None)
        monkeypatch.setattr(c, "_post", lambda path, body, auth=True: resp)
        return c

    @pytest.mark.parametrize("reader,args", [("get_open_orders", (555,)), ("get_positions", (555,)), ("get_orders", (555,))])
    def test_success_false_raises_instead_of_looking_empty(self, monkeypatch, reader, args):
        c = self._client(monkeypatch, {"success": False, "errorCode": 9, "errorMessage": "transient"})
        with pytest.raises(RuntimeError, match="transient"):
            getattr(c, reader)(*args)

    def test_valid_empty_response_is_still_an_empty_list(self, monkeypatch):
        assert self._client(monkeypatch, {"orders": [], "success": True}).get_open_orders(555) == []
        assert self._client(monkeypatch, {"positions": [], "success": True}).get_positions(555) == []

    def test_plain_list_and_missing_success_flag_keep_working(self, monkeypatch):
        assert self._client(monkeypatch, [{"id": 1}]).get_open_orders(555) == [{"id": 1}]
        assert self._client(monkeypatch, {"orders": [{"id": 2}]}).get_open_orders(555) == [{"id": 2}]

    def test_unexpected_shape_raises(self, monkeypatch):
        with pytest.raises(RuntimeError):
            self._client(monkeypatch, "boom").get_open_orders(555)


class TestAmbiguousDisappearanceIsVerifiedNotAssumed:
    def test_api_error_on_open_orders_never_finalizes_a_live_position(self, monkeypatch):
        """R1 invertido: el error de lectura reintenta; el bracket sigue vivo y luego se resuelve como TP real."""
        client = SeqOpenOrders([RuntimeError("Order/searchOpen fallo: transient")] * 3 + [{SL_ID}])   # luego TP ausente, SL vivo
        out = _poll(client, monkeypatch)
        assert out["result"] == "TP"

    def test_both_legs_gone_but_position_still_open_is_closed_and_alerted(self, monkeypatch):
        """Posicion INVERTIDA / parcial: ambas patas ausentes pero la cuenta NO esta plana."""
        client = SeqOpenOrders([set()])
        client.positions = [_open_position(40, type_=2)]
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["result"] == "UNKNOWN" and out["position_forced_flat"] is True
        assert client.closed_contracts == [(555, MES)]
        assert any("NO estaba plana" in m and "CERRO" in m for m in sent)

    def test_if_the_forced_close_also_fails_it_says_close_manually(self, monkeypatch):
        client = SeqOpenOrders([set()])
        client.positions = [_open_position(40, type_=2)]
        client.close_contract_error = "boom"
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["flatten_failed"] is True and "position_forced_flat" not in out
        assert any("MANUALMENTE" in m for m in sent)

    def test_both_legs_gone_and_account_flat_is_unknown_without_forcing_anything(self, monkeypatch):
        """Cierre manual (Flatten All) o liquidacion: se respeta, sin tocar la cuenta."""
        client = SeqOpenOrders([set()])
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["result"] == "UNKNOWN"
        assert not out.get("position_forced_flat") and client.closed_contracts == []
        assert sent == []

    def test_a_one_off_empty_read_is_not_taken_as_both_legs_gone(self, monkeypatch):
        """Glitch transitorio: una lectura vacia y las siguientes muestran el bracket vivo -> no es UNKNOWN."""
        client = SeqOpenOrders([set(), {TP_ID, SL_ID}, {TP_ID, SL_ID}, {SL_ID}])
        assert _poll(client, monkeypatch)["result"] == "TP"

    def test_if_position_cannot_be_read_it_keeps_polling_instead_of_finalizing(self, monkeypatch):
        client = SeqOpenOrders([set()])
        client.get_positions = lambda account_id: (_ for _ in ()).throw(RuntimeError("API caida"))
        out = _poll(client, monkeypatch, max_polls=6)
        assert out["result"] == "FLATTEN"            # no UNKNOWN: siguio hasta el flatten de fin de sesion


class TestNaturalResolutionVerifiesCleanup:
    def test_orphan_stop_after_tp_is_reported(self, monkeypatch):
        """R5 invertido: si cancelar la pata sobrante falla, hay aviso y queda registrado."""
        client = SeqOpenOrders([{SL_ID}])
        client.cancel_order = lambda oid, account_id=None: False          # la API no cancela
        client.open_order_ids = {SL_ID}
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["result"] == "TP" and out["orphan_orders"] == [SL_ID]
        assert any("ABIERTAS" in m and str(SL_ID) in m for m in sent)

    def test_clean_natural_tp_sends_no_alert_and_adds_no_flags(self, monkeypatch):
        client = SeqOpenOrders([{SL_ID}, set()])        # tras cancelar el SL, searchOpen ya no lo lista
        client.open_order_ids = {SL_ID}
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["result"] == "TP" and sent == []
        assert not ({"orphan_orders", "position_forced_flat", "flatten_failed", "flat_unverified"} & set(out))

    def test_tp_with_position_still_open_closes_it(self, monkeypatch):
        """TP detectado pero quedan contratos abiertos (fill parcial del bracket): se cierran y se avisa."""
        client = SeqOpenOrders([{SL_ID}, set()])
        client.open_order_ids = {SL_ID}
        client.positions = [_open_position(15, type_=1)]
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["result"] == "TP" and out["position_forced_flat"] is True
        assert client.closed_contracts == [(555, MES)]

    def test_unreadable_position_after_resolution_is_flagged_unverified(self, monkeypatch):
        client = SeqOpenOrders([{SL_ID}, set()])
        client.open_order_ids = {SL_ID}
        client.get_positions = lambda account_id: (_ for _ in ()).throw(RuntimeError("API caida"))
        sent = []
        out = _poll(client, monkeypatch, sent)
        assert out["flat_unverified"] is True and any("no se pudo confirmar" in m for m in sent)


class TestUnknownDayIsLoudAndFlagged:
    def _state(self):
        return {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 100,
                "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": TP_ID, "sl_order_id": SL_ID,
                "contract_id": MES, "account_id": 555, "opened_at": "x"}

    def test_unknown_message_says_pnl_is_not_real_and_entry_needs_review(self, fake_gist, monkeypatch):
        sent = []
        monkeypatch.setattr(pe, "send", lambda m: sent.append(m))
        pe._finalize_cycle(FakeClient(), 555, self._state(),
                           {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True})
        assert any("[UNKNOWN]" in m and "NO es real" in m for m in sent)
        e = fake_gist["geometry_mes_log.json"][-1]
        assert e["needs_review"] is True and e["result"] == "UNKNOWN"

    def test_flags_from_verification_reach_the_historic_log(self, fake_gist, monkeypatch):
        monkeypatch.setattr(pe, "send", lambda m: None)
        pe._finalize_cycle(FakeClient(), 555, self._state(),
                           {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False,
                            "position_forced_flat": True, "orphan_orders": [SL_ID], "flat_unverified": True})
        e = fake_gist["geometry_mes_log.json"][-1]
        assert e["position_forced_flat"] is True and e["orphan_orders"] == [SL_ID] and e["flat_unverified"] is True
        assert "needs_review" not in e

    def test_a_normal_close_adds_no_flags(self, fake_gist, monkeypatch):
        monkeypatch.setattr(pe, "send", lambda m: None)
        pe._finalize_cycle(FakeClient(), 555, self._state(),
                           {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
        e = fake_gist["geometry_mes_log.json"][-1]
        assert not ({"needs_review", "position_forced_flat", "orphan_orders", "flat_unverified", "flatten_failed"} & set(e))
