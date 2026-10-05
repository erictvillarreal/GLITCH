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
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent, _fixed_clock, _entry_deadline_off  # noqa: F401

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
            self.positions = []          # el TP cerro la posicion
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


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A5 -- el Pi NUNCA opera en una cuenta que no se fijo explicitamente; la Combine esta denegada por defecto
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
import subprocess

COMBINE = 28197705
PRACTICE = 28197753


class TestAccountPinIsMandatoryAndCombineIsDenied:
    def _accounts(self, *ids):
        c = FakeClient()
        c.accounts = [{"id": i} for i in ids]
        return c

    def test_blank_pin_with_only_the_combine_active_places_no_orders(self, fake_gist, sent, monkeypatch):
        """R6 invertido: Practice liquidada/reiniciada => la Combine queda como unica cuenta activa; ya NO se opera."""
        client = self._accounts(COMBINE)
        _arm(monkeypatch, client)
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", "")
        _set_clock(monkeypatch, 14, 31)
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        assert client.placed_orders == [] and client.closed_contracts == []
        assert any("TOPSTEP_ACCOUNT_ID" in m for m in sent)

    @pytest.mark.parametrize("pin", ["28197705", " 28197705 ", "28197705\n"])
    def test_pinning_the_combine_is_refused_even_though_it_is_active(self, monkeypatch, pin):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", pin)
        monkeypatch.delenv("TOPSTEP_ACCOUNT_DENY", raising=False)
        with pytest.raises(RuntimeError, match="denegacion"):
            pe._resolve_account_id(self._accounts(COMBINE, PRACTICE))

    def test_denylist_can_be_disabled_explicitly_for_phase3(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", str(COMBINE))
        monkeypatch.setenv("TOPSTEP_ACCOUNT_DENY", "")                    # vacia = sin lista (decision consciente)
        assert pe._resolve_account_id(self._accounts(COMBINE, PRACTICE)) == COMBINE

    def test_denylist_can_be_replaced(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", str(PRACTICE))
        monkeypatch.setenv("TOPSTEP_ACCOUNT_DENY", f"{PRACTICE}, 111")
        with pytest.raises(RuntimeError, match="denegacion"):
            pe._resolve_account_id(self._accounts(COMBINE, PRACTICE))

    @pytest.mark.parametrize("pin", ["28197705.0", "0x1ACCD99", "abc", "2819770", "281977053"])
    def test_a_mistyped_pin_never_matches_another_account(self, monkeypatch, pin):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", pin)
        monkeypatch.delenv("TOPSTEP_ACCOUNT_DENY", raising=False)
        with pytest.raises(RuntimeError):
            pe._resolve_account_id(self._accounts(COMBINE, PRACTICE))

    def test_numeric_vs_string_ids_match_only_when_equal(self, monkeypatch):
        monkeypatch.setenv("TOPSTEP_ACCOUNT_ID", str(PRACTICE))
        monkeypatch.delenv("TOPSTEP_ACCOUNT_DENY", raising=False)
        c = FakeClient(); c.accounts = [{"id": str(COMBINE)}, {"id": PRACTICE}]
        assert pe._resolve_account_id(c) == PRACTICE

    def test_service_refuses_to_start_without_the_variable(self):
        """require_env al importar el modulo: sin TOPSTEP_ACCOUNT_ID el proceso termina (systemd lo reportara)."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {k: v for k, v in os.environ.items() if not k.startswith(("TOPSTEP_", "TELEGRAM_"))}  # sin Telegram: no toca la red
        env.update({"TOPSTEP_USERNAME": "u", "TOPSTEP_API_KEY": "k", "GITHUB_GIST_TOKEN": "g", "GIST_ID": "i",
                    "GLITCH_PRODUCT": "MES", "PYTHONPATH": root})
        r = subprocess.run([sys.executable, "-c", "import pi.pi_executor"], env=env, capture_output=True, text=True,
                           timeout=60, cwd=root)
        assert r.returncode != 0
        assert "TOPSTEP_ACCOUNT_ID" in r.stderr

    def test_installer_requires_a_value_for_the_account(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "pi", "ops", "install_service.sh")) as f:
            src = f.read()
        line = next(l for l in src.splitlines() if l.startswith("REQUIRED_VARS="))
        assert "TOPSTEP_ACCOUNT_ID" in line


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A3 -- una señal real solo se ejecuta dentro de la ventana de entrada; fuera, se descarta con aviso
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
class TestEntryDeadline:
    @pytest.fixture(autouse=True)
    def _deadline_on(self, monkeypatch):
        monkeypatch.setattr(pe, "ENTRY_DEADLINE_MINUTES", 10 * 60)      # el default real: 10:00 CT

    @pytest.mark.parametrize("hh,mm", [(9, 36), (9, 50), (9, 59)])
    def test_signal_inside_the_window_is_executed(self, fake_gist, sent, monkeypatch, hh, mm):
        client = FakeClient()
        _arm(monkeypatch, client)
        _set_clock(monkeypatch, hh, mm)
        fake_gist[pe.ORDER_FILE] = _signal()
        monkeypatch.setattr(pe, "poll_position_until_closed",
                            lambda *a, **k: {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": True})
        pe.run_once()
        assert len(client.placed_orders) == 3

    @pytest.mark.parametrize("hh,mm", [(10, 0), (13, 0), (15, 30), (17, 5), (23, 50)])
    def test_late_signal_is_discarded_cleared_and_alerted_without_touching_the_broker(self, fake_gist, sent, monkeypatch, hh, mm):
        """R3 invertido: antes entraba a cualquier hora del mismo dia CT."""
        client = FakeClient()
        monkeypatch.setattr(pe, "authenticate", lambda: (_ for _ in ()).throw(AssertionError("no debe tocar el broker")))
        monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
        _set_clock(monkeypatch, hh, mm)
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        assert client.placed_orders == []
        assert fake_gist[pe.ORDER_FILE] == {}
        assert "geometry_mes_log.json" not in fake_gist                       # no entra al historial como trade
        assert len(sent) == 1 and "hora limite" in sent[0]

    def test_alert_is_not_repeated_every_cycle_if_clearing_keeps_failing(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        _set_clock(monkeypatch, 15, 30)
        fake_gist[pe.ORDER_FILE] = _signal()
        _drop_signal_clear(monkeypatch, fake_gist)
        for _ in range(5):
            pe.run_once()
        assert client.placed_orders == [] and len(sent) == 1

    def test_test_signals_are_exempt_so_after_hours_trials_still_work(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        _set_clock(monkeypatch, 15, 30)
        fake_gist[pe.ORDER_FILE] = _signal(product="MEStest", nc=1)
        pe.run_once()
        assert len([o for o in client.placed_orders if o["order_type"] == pe.OrderType.MARKET]) == 1

    def test_default_deadline_is_inside_what_paper_can_do(self):
        """El paper se rinde ~9:50 como tarde (compuerta 9:35 + 20 reintentos x 30 s): el limite no debe ser anterior a
        la entrada normal ni mucho mas tarde que lo que el paper podria hacer."""
        default_deadline = pe._parse_hhmm("10:00", 0)
        assert 9 * 60 + 50 <= default_deadline <= 11 * 60

    @pytest.mark.parametrize("value,expected", [("10:30", 630), (" 9:45 ", 585), ("00:00", 0), ("23:59", 1439)])
    def test_parse_hhmm_valid(self, value, expected):
        assert pe._parse_hhmm(value, -1) == expected

    @pytest.mark.parametrize("value", ["", "10", "24:00", "10:60", "abc", "10:xx", "-1:30"])
    def test_parse_hhmm_invalid_falls_back_to_default(self, value):
        assert pe._parse_hhmm(value, 600) == 600


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A7 -- el Pi no ejecuta lo que diga el Gist sin validarlo contra su config local (cota superior, no igualdad)
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
class TestSignalIsValidatedAgainstLocalConfig:
    def test_the_normal_railway_signal_is_valid(self):
        assert pe._validate_signal(_signal()) is None

    @pytest.mark.parametrize("nc", [41, 100, 400, 0, -1, True, "40", 40.0, None])
    def test_nc_must_be_an_int_between_1_and_the_configured_size(self, nc):
        assert pe._validate_signal(_signal(nc=nc)) is not None

    @pytest.mark.parametrize("nc", [1, 10, 39, 40])
    def test_smaller_or_equal_sizes_are_allowed(self, nc):
        assert pe._validate_signal(_signal(nc=nc)) is None

    @pytest.mark.parametrize("side", [0, 2, "1", None, True, 1.0])
    def test_side_must_be_plus_or_minus_one(self, side):
        assert pe._validate_signal(_signal(side=side)) is not None

    @pytest.mark.parametrize("key,val", [("sl_ticks", 0), ("sl_ticks", 401), ("sl_ticks", True), ("sl_ticks", "100"),
                                         ("tp_ticks", 0), ("tp_ticks", 161), ("tp_ticks", None)])
    def test_ticks_must_be_sane(self, key, val):
        assert pe._validate_signal(_signal(**{key: val})) is not None

    def test_ticks_up_to_4x_config_are_allowed(self):
        assert pe._validate_signal(_signal(sl_ticks=400, tp_ticks=160)) is None
        assert pe._validate_signal(_signal(sl_ticks=4, tp_ticks=4)) is None            # ensayos con TP/SL a ~4 ticks

    def test_product_code_must_match_the_service_product(self):
        assert pe._validate_signal(_signal(product_code="MNQ")) is not None
        assert pe._validate_signal({k: v for k, v in _signal().items() if k != "product_code"}) is not None

    def test_direction_if_present_must_agree_with_side(self):
        assert pe._validate_signal(_signal(side=1, direction="SHORT")) is not None
        assert pe._validate_signal(_signal(side=-1, direction="LONG")) is not None
        assert pe._validate_signal(_signal(side=-1, direction="SHORT")) is None

    def test_missing_fields_are_invalid_not_a_crash(self):
        for key in ("side", "nc", "sl_ticks", "tp_ticks"):
            assert pe._validate_signal({k: v for k, v in _signal().items() if k != key}) is not None

    def test_test_signals_are_capped_at_two_contracts(self):
        assert pe._validate_signal(_signal(product="MEStest", nc=1)) is None
        assert pe._validate_signal(_signal(product="MEStest", nc=2)) is None
        assert pe._validate_signal(_signal(product="MEStest", nc=3)) is not None
        assert pe._validate_signal(_signal(product="MEStest", nc=40)) is not None

    def test_invalid_signal_never_touches_the_broker_is_cleared_and_alerted_once(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        monkeypatch.setattr(pe, "authenticate", lambda: (_ for _ in ()).throw(AssertionError("no debe tocar el broker")))
        monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
        fake_gist[pe.ORDER_FILE] = _signal(nc=400)
        _drop_signal_clear(monkeypatch, fake_gist)                 # aun si la limpieza falla, el aviso no se repite
        for _ in range(3):
            pe.run_once()
        assert client.placed_orders == []
        assert len(sent) == 1 and "NO es valida" in sent[0] and "400" in sent[0]

    def test_invalid_signal_is_cleared(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pe, "authenticate", lambda: (_ for _ in ()).throw(AssertionError("no debe tocar el broker")))
        monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1})
        fake_gist[pe.ORDER_FILE] = _signal(nc=400)
        pe.run_once()
        assert fake_gist[pe.ORDER_FILE] == {}

    def test_a_valid_small_test_signal_still_executes(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        _arm(monkeypatch, client)
        _set_clock(monkeypatch, 14, 31)
        fake_gist[pe.ORDER_FILE] = _signal(product="MEStest", nc=1, sl_ticks=4, tp_ticks=4)
        pe.run_once()
        assert len([o for o in client.placed_orders if o["order_type"] == pe.OrderType.MARKET]) == 1
        assert client.placed_orders[0]["size"] == 1


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A4 -- el historial compartido NUNCA se sobrescribe a ciegas: lectura estricta, reintentos, spool local, alerta
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
import execution.gist_store as gs

HIST = "geometry_mes_log.json"


def _entry(**kw):
    e = {"date": "2026-09-29", "signal": True, "side": 1, "direction": "LONG", "entry": 6000.0, "exit": 6010.0,
         "result": "TP", "pnl": 2000.0, "sl_ticks": 100, "tp_ticks": 40, "nc": 40, "dry_run": False,
         "product": "MES", "intento": 1}
    e.update(kw)
    return e


def _old_history():
    return [{"date": f"2026-09-{d:02d}", "result": "TP", "pnl": 100.0, "intento": 1, "dry_run": True} for d in range(10, 20)]


@pytest.fixture
def strict_gist(monkeypatch):
    """Historial en memoria con fallos programables de lectura/escritura (estrictos: lanzan, como las nuevas gist_store)."""
    state = {"log": _old_history(), "read_fail": 0, "write_fail": 0, "write_lands_but_raises": False, "writes": 0}

    def load(filename):
        if state["read_fail"] > 0:
            state["read_fail"] -= 1
            raise gs.GistError("lectura fallo: timeout")
        return list(state["log"])

    def save(filename, data):
        state["writes"] += 1
        if state["write_fail"] > 0:
            state["write_fail"] -= 1
            if state["write_lands_but_raises"]:
                state["log"] = list(data)          # el PATCH SI llego, pero la respuesta no
            raise gs.GistError("escritura fallo: 502")
        state["log"] = list(data)
    monkeypatch.setattr(pe, "_gist_load_log_strict", load)
    monkeypatch.setattr(pe, "_gist_save_log_strict", save)
    monkeypatch.setattr(pe.time, "sleep", lambda s: None)
    return state


class TestHistoryIsNeverOverwrittenBlindly:
    def test_normal_append_keeps_all_previous_entries(self, strict_gist, sent):
        pe.append_to_historic_log("MES", _entry())
        assert len(strict_gist["log"]) == 11 and strict_gist["log"][-1]["result"] == "TP" and sent == []

    def test_empty_history_is_a_legitimate_first_write(self, strict_gist, sent):
        strict_gist["log"] = []
        pe.append_to_historic_log("MES", _entry())
        assert len(strict_gist["log"]) == 1

    def test_read_failure_never_overwrites_the_history_and_spools_and_alerts(self, strict_gist, sent):
        """R4 invertido: antes, 1 lectura fallida => el historial de 10 dias se reemplazaba por 1 entrada."""
        strict_gist["read_fail"] = 99
        pe.append_to_historic_log("MES", _entry())
        assert strict_gist["writes"] == 0                                   # NO hubo ningun PATCH
        assert len(strict_gist["log"]) == 10                                # historial intacto
        assert len(pe._spool_read(pe._spool_path("MES"))) == 1              # la entrada quedo guardada en el Pi
        assert len(sent) == 1 and "NO se sobrescribio" in sent[0] and '"pnl": 2000.0' in sent[0]

    def test_write_failure_spools_and_leaves_history_untouched(self, strict_gist, sent):
        strict_gist["write_fail"] = 99
        pe.append_to_historic_log("MES", _entry())
        assert len(strict_gist["log"]) == 10 and len(pe._spool_read(pe._spool_path("MES"))) == 1
        assert strict_gist["writes"] == pe.HISTORY_WRITE_ATTEMPTS

    def test_transient_failure_is_retried_and_succeeds_without_spool_or_alert(self, strict_gist, sent):
        strict_gist["read_fail"] = 1
        pe.append_to_historic_log("MES", _entry())
        assert len(strict_gist["log"]) == 11 and sent == []
        assert not os.path.exists(pe._spool_path("MES"))

    def test_a_write_that_landed_but_raised_is_not_duplicated_on_retry(self, strict_gist, sent):
        strict_gist["write_fail"] = 1
        strict_gist["write_lands_but_raises"] = True
        pe.append_to_historic_log("MES", _entry())
        assert len([e for e in strict_gist["log"] if e.get("dry_run") is False]) == 1

    def test_spooled_entries_are_merged_on_the_next_successful_close(self, strict_gist, sent):
        strict_gist["read_fail"] = 99
        pe.append_to_historic_log("MES", _entry(date="2026-09-29", entry=6000.0))
        strict_gist["read_fail"] = 0
        pe.append_to_historic_log("MES", _entry(date="2026-09-30", entry=6100.0, exit=6110.0))
        real = [e for e in strict_gist["log"] if e.get("dry_run") is False]
        assert [e["date"] for e in real] == ["2026-09-29", "2026-09-30"]    # primero la pendiente, luego la nueva
        assert len(strict_gist["log"]) == 12 and not os.path.exists(pe._spool_path("MES"))

    def test_if_even_the_spool_cannot_be_written_the_alert_carries_the_entry(self, strict_gist, sent, monkeypatch, tmp_path):
        strict_gist["read_fail"] = 99
        blocker = tmp_path / "es_un_archivo"
        blocker.write_text("x")
        monkeypatch.setenv("GLITCH_PI_STATE_DIR", str(blocker))
        pe.append_to_historic_log("MES", _entry())                          # no debe lanzar
        assert len(sent) == 1 and "copiar esta entrada a mano" in sent[0] and '"pnl": 2000.0' in sent[0]

    def test_finalize_still_completes_and_clears_state_when_history_is_spooled(self, fake_gist, strict_gist, sent, monkeypatch):
        """Un fallo del Gist no debe dejar el ciclo a medias (el bracket ya se cerro): se limpia estado y señal."""
        strict_gist["read_fail"] = 99
        state = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 100,
                 "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102,
                 "contract_id": MES, "account_id": 555, "opened_at": "x"}
        fake_gist[pe.PI_STATE_FILE] = state
        fake_gist[pe.ORDER_FILE] = _signal()
        pe._finalize_cycle(FakeClient(), 555, state, {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
        assert fake_gist[pe.PI_STATE_FILE] == {} and fake_gist[pe.ORDER_FILE] == {}
        assert any("[CLOSE] [TP]" in m for m in sent)

    def test_with_the_real_gist_store_a_read_failure_sends_no_patch(self, sent, monkeypatch):
        """El escenario EXACTO de R4, con gist_store real: GET falla -> ningun PATCH (antes: PATCH con 1 entrada)."""
        patches = []

        def bad_get(*a, **k):
            raise ConnectionError("timeout")

        class R:
            def raise_for_status(self): pass

        def fake_patch(url, headers=None, json=None, timeout=None):
            patches.append(json)
            return R()
        monkeypatch.setattr(gs.requests, "get", bad_get)
        monkeypatch.setattr(gs.requests, "patch", fake_patch)
        monkeypatch.setattr(gs, "GITHUB_GIST_TOKEN", "x"); monkeypatch.setattr(gs, "GIST_ID", "y")
        monkeypatch.setattr(pe, "_gist_load_log_strict", gs.load_log_strict)
        monkeypatch.setattr(pe, "_gist_save_log_strict", gs.save_log_strict)
        monkeypatch.setattr(pe.time, "sleep", lambda s: None)
        pe.append_to_historic_log("MES", _entry())
        assert patches == []


class TestStrictGistStore:
    @pytest.fixture(autouse=True)
    def _cfg(self, monkeypatch):
        monkeypatch.setattr(gs, "GITHUB_GIST_TOKEN", "x")
        monkeypatch.setattr(gs, "GIST_ID", "y")

    class _Resp:
        def __init__(self, payload=None, status_ok=True):
            self._p, self._ok = payload, status_ok

        def raise_for_status(self):
            if not self._ok:
                raise RuntimeError("HTTP 502")

        def json(self):
            return self._p

    def _get(self, monkeypatch, payload=None, ok=True, exc=None):
        def get(*a, **k):
            if exc:
                raise exc
            return self._Resp(payload, ok)
        monkeypatch.setattr(gs.requests, "get", get)

    def test_network_error_raises_instead_of_returning_empty(self, monkeypatch):
        self._get(monkeypatch, exc=ConnectionError("x"))
        with pytest.raises(gs.GistError):
            gs.load_log_strict("f.json")

    def test_http_error_raises(self, monkeypatch):
        self._get(monkeypatch, {"files": {}}, ok=False)
        with pytest.raises(gs.GistError):
            gs.load_log_strict("f.json")

    def test_missing_or_empty_file_is_a_legitimate_empty_list(self, monkeypatch):
        self._get(monkeypatch, {"files": {}})
        assert gs.load_log_strict("f.json") == []
        self._get(monkeypatch, {"files": {"f.json": {"content": "   "}}})
        assert gs.load_log_strict("f.json") == []

    def test_corrupt_json_or_wrong_type_raises(self, monkeypatch):
        self._get(monkeypatch, {"files": {"f.json": {"content": "{{{"}}})
        with pytest.raises(gs.GistError):
            gs.load_log_strict("f.json")
        self._get(monkeypatch, {"files": {"f.json": {"content": '{"a": 1}'}}})
        with pytest.raises(gs.GistError):
            gs.load_log_strict("f.json")

    def test_valid_list_is_returned(self, monkeypatch):
        self._get(monkeypatch, {"files": {"f.json": {"content": '[{"a": 1}]'}}})
        assert gs.load_log_strict("f.json") == [{"a": 1}]

    def test_write_failure_raises(self, monkeypatch):
        def patch(*a, **k):
            return self._Resp(None, status_ok=False)
        monkeypatch.setattr(gs.requests, "patch", patch)
        with pytest.raises(gs.GistError):
            gs.save_log_strict("f.json", [])

    def test_the_original_non_strict_functions_are_unchanged(self, monkeypatch):
        """Railway sigue con load_log/save_log: lectura fallida => [] y escritura fallida => sin excepcion."""
        self._get(monkeypatch, exc=ConnectionError("x"))
        assert gs.load_log("f.json") == []

        def patch(*a, **k):
            raise ConnectionError("x")
        monkeypatch.setattr(gs.requests, "patch", patch)
        gs.save_log("f.json", [])          # no debe lanzar


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A6 -- el precio de cierre "real" del flatten solo se acepta si es inequivoco y plausible; si no, estimado y marcado
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
class TestFlattenFillIsConservative:
    STATE = {"phase": "bracket_open", "signal": None, "entry_price": 6000.0, "entry_order_id": 100,
             "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102,
             "contract_id": MES, "account_id": 555, "opened_at": "x"}

    def _state(self):
        s = dict(self.STATE)
        s["signal"] = _signal()
        return s

    def _client(self, extra=None):
        c = FakeClient()
        c.order_records = {
            100: {"id": 100, "contractId": MES, "filledPrice": 6000.0},     # entrada
            101: {"id": 101, "contractId": MES}, 102: {"id": 102, "contractId": MES},   # TP/SL cancelados, sin fill
        }
        c.order_records.update(extra or {})
        return c

    def test_single_plausible_closing_fill_is_used_and_marked_real(self):
        c = self._client({105: {"id": 105, "contractId": MES, "filledPrice": 6004.25}})
        assert pe._find_flatten_fill(c, 555, self._state()) == 6004.25

    def test_a_price_far_outside_the_bracket_is_rejected(self):
        """R8 invertido: 7123 con bracket 5975-6010 es otra operacion, no el cierre de este ciclo."""
        c = self._client({117: {"id": 117, "contractId": MES, "filledPrice": 7123.0}})
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_slippage_slightly_beyond_the_bracket_is_tolerated(self):
        tol = pe.FLATTEN_FILL_TOLERANCE_TICKS * pe.CFG.spec.tick_size
        c = self._client({105: {"id": 105, "contractId": MES, "filledPrice": 5975.0 - tol}})
        assert pe._find_flatten_fill(c, 555, self._state()) == 5975.0 - tol
        c = self._client({105: {"id": 105, "contractId": MES, "filledPrice": 5975.0 - tol - 0.25}})
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_two_candidates_is_ambiguous_so_none(self):
        c = self._client({105: {"id": 105, "contractId": MES, "filledPrice": 6004.0},
                          106: {"id": 106, "contractId": MES, "filledPrice": 6003.0}})
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_orders_of_other_contracts_or_older_than_the_entry_are_ignored(self):
        c = self._client({90: {"id": 90, "contractId": MES, "filledPrice": 6001.0},            # anterior a la entrada
                          105: {"id": 105, "contractId": "CON.NQ", "filledPrice": 6002.0}})    # otro contrato
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_non_integer_ids_degrade_to_none_never_to_a_wrong_price(self):
        c = self._client({"105": {"id": "105", "contractId": MES, "filledPrice": 6004.0}})
        assert pe._find_flatten_fill(c, 555, self._state()) is None
        c = self._client({105: {"id": True, "contractId": MES, "filledPrice": 6004.0}})
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_api_failure_degrades_to_none(self):
        c = self._client()
        c.get_orders = lambda account_id, only_open=False: (_ for _ in ()).throw(RuntimeError("boom"))
        assert pe._find_flatten_fill(c, 555, self._state()) is None

    def test_a_rejected_fill_leaves_the_close_estimated_and_flagged_not_a_fake_pnl(self, fake_gist, monkeypatch):
        """R8 invertido de punta a punta: sin el parche, pnl = $224,600 con exit_price_estimated=False."""
        monkeypatch.setattr(pe, "send", lambda m: None)
        c = self._client({117: {"id": 117, "contractId": MES, "filledPrice": 7123.0}})
        pe._finalize_cycle(c, 555, self._state(), {"result": "FLATTEN", "exit_price": None, "exit_price_estimated": True})
        e = fake_gist["geometry_mes_log.json"][-1]
        assert e["exit_price_estimated"] is True and abs(e["pnl"]) < 1000


# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# M1 -- tras colocar entrada+TP+SL se CONFIRMA que la posicion existe; si la entrada no se ejecuto, se cancela todo
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
class TestEntryFillIsConfirmed:
    def _run(self, client, fake_gist, monkeypatch, sent):
        _arm(monkeypatch, client)
        monkeypatch.setattr(pe, "poll_position_until_closed",
                            lambda *a, **k: {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": True})
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()

    def test_a_normal_fill_sends_no_extra_alert_and_opens(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        self._run(client, fake_gist, monkeypatch, sent)
        assert any("[OPEN]" in m for m in sent) and not any("ALERTA" in m for m in sent)

    def test_entry_that_never_fills_cancels_everything_and_discards_the_signal(self, fake_gist, sent, monkeypatch):
        """R7 invertido: antes los exits se quedaban colocados sin posicion (el TP habria abierto un SHORT)."""
        client = FakeClient()
        client.auto_fill_market = False                              # la entrada se "acepta" pero NUNCA se ejecuta
        _arm(monkeypatch, client)
        monkeypatch.setattr(pe, "poll_position_until_closed",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe monitorear un bracket sin posicion")))
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        entry_id, tp_id, sl_id = [o["id"] for o in client.placed_orders]
        assert {entry_id, tp_id, sl_id} <= set(client.cancelled)
        assert client.open_order_ids == set()
        assert fake_gist[pe.ORDER_FILE] == {} and fake_gist[pe.PI_STATE_FILE] == {}
        assert not any("[OPEN]" in m for m in sent)
        assert any("no aparecio como posicion" in m and "no se reintenta" in m for m in sent)

    def test_aborted_entry_is_not_retried_next_cycle(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.auto_fill_market = False
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        n = len(client.placed_orders)
        fake_gist[pe.ORDER_FILE] = _signal()                           # aunque la señal reapareciera (limpieza fallida)
        pe.run_once()
        assert len(client.placed_orders) == n                          # el marcador (A1) impide el segundo intento

    def test_a_late_fill_within_the_wait_is_accepted_quietly(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.auto_fill_market = False
        calls = {"n": 0}
        orig = client.get_positions

        def late(account_id):
            calls["n"] += 1
            if calls["n"] == 4:         # 1 = guard pre-orden; 2,3 = confirmacion sin posicion; 4 = ya aparece
                client.positions = [{"id": 1, "accountId": 555, "contractId": MES, "type": 1, "size": 40, "averagePrice": 6000.0}]
            return orig(account_id)
        client.get_positions = late
        self._run(client, fake_gist, monkeypatch, sent)
        assert any("[OPEN]" in m for m in sent) and not any("ALERTA" in m for m in sent)

    def test_partial_fill_alerts_but_keeps_monitoring(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.auto_fill_market = False
        orig = client.get_positions

        def partial(account_id):
            if len(client.placed_orders) >= 3:
                client.positions = [{"id": 1, "accountId": 555, "contractId": MES, "type": 1, "size": 25, "averagePrice": 6000.0}]
            return orig(account_id)
        client.get_positions = partial
        self._run(client, fake_gist, monkeypatch, sent)
        assert any("PARCIAL" in m and "25 de 40" in m for m in sent) and any("[OPEN]" in m for m in sent)

    def test_unreadable_positions_do_not_abort_a_possibly_valid_position(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        orig = client.get_positions

        def flaky(account_id):
            if len(client.placed_orders) >= 3:
                raise RuntimeError("API caida")
            return orig(account_id)
        client.get_positions = flaky
        self._run(client, fake_gist, monkeypatch, sent)
        assert client.cancelled == [] and any("[OPEN]" in m for m in sent)
        assert any("No se pudo leer la posicion" in m for m in sent)

    def test_if_the_fill_lands_right_at_abort_and_close_fails_it_says_close_manually(self, fake_gist, sent, monkeypatch):
        client = FakeClient()
        client.auto_fill_market = False
        state = {"after_abort": False}
        orig = client.get_positions

        def sneaky(account_id):
            if state["after_abort"] or len(client.cancelled) >= 3:       # tras cancelar, aparece una posicion
                state["after_abort"] = True
                return [{"id": 1, "accountId": 555, "contractId": MES, "type": 1, "size": 40, "averagePrice": 6000.0}]
            return orig(account_id)
        client.get_positions = sneaky
        client.close_contract_error = "boom"
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal()
        pe.run_once()
        assert any("MANUALMENTE" in m for m in sent)
