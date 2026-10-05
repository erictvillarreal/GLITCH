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
