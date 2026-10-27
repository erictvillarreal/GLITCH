"""G1a (24-oct-2026) -- PROPUESTA (NO DESPLEGAR): registro de tiempos de ejecucion de la entrada (t_ref, t_envio, t_fill, latencias)."""
import datetime as dt
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
from pi.slippage_pure import build_exec_record, exit_slip_ticks, extract_fill_time, parse_iso
from tests.test_pi_executor import FakeClient, _entry_deadline_off, _signal, fake_gist, sent  # noqa: F401


def test_parse_iso_y_extract_fill_time():
    assert parse_iso("2026-10-26T14:35:02Z") == dt.datetime(2026, 10, 26, 14, 35, 2, tzinfo=dt.timezone.utc).timestamp()
    assert parse_iso("basura") is None and parse_iso(None) is None
    assert extract_fill_time({"updateTimestamp": "2026-10-26T14:35:03Z"}) == "updateTimestamp=2026-10-26T14:35:03Z"
    assert extract_fill_time({"filledPrice": 1}) is None and extract_fill_time(None) is None


def test_build_exec_record_latencias():
    t0 = dt.datetime(2026, 10, 26, 14, 35, 2, tzinfo=dt.timezone.utc).timestamp()
    r = build_exec_record(side=1, nc=40, tick_size=0.25, ref_price=7780.50, t_signal_seen=t0, t_ref_bar="2026-10-26T14:35:00Z", t_ref_local=t0 + 0.4,
                          t_send=t0 + 0.9, t_ack=t0 + 1.3, fill_price=7781.25, fill_time="updateTimestamp=2026-10-26T14:35:04Z", t_prev_empty_poll=t0 - 61)
    assert r["slip_ticks"] == 3.0 and r["lat_ref_to_send_ms"] == 500 and r["lat_send_to_ack_ms"] == 400 and r["lat_signal_to_send_ms"] == 900
    assert r["lat_send_to_fill_ms"] == 1100 and r["ref_bar_age_s"] == 2.4 and r["poll_window_s"] == 61.0 and r["bid"] is None and r["ask"] is None


def test_build_exec_record_sin_fill_no_inventa():
    r = build_exec_record(side=-1, nc=40, tick_size=0.25, ref_price=7743.25, t_signal_seen=1.0, t_ref_bar=None, t_ref_local=1.1, t_send=1.2, t_ack=1.5,
                          fill_price=None, fill_time=None)
    assert r["slip_ticks"] is None and r["lat_send_to_fill_ms"] is None and r["ref_bar_age_s"] is None and r["poll_window_s"] is None


def test_reference_quote_conserva_la_marca_de_la_barra_y_reference_price_no_cambia():
    class C(FakeClient):
        def get_recent_bars(self, *a, **k): return [{"t": "2026-10-26T14:34:00Z", "c": 6000.0}, {"t": "2026-10-26T14:35:00Z", "c": 6000.25}]
    assert pe._reference_quote(C(), "X") == (6000.25, "2026-10-26T14:35:00Z") and pe._reference_price(C(), "X") == 6000.25


def test_run_once_guarda_exec_en_estado_historial_y_mensaje(fake_gist, sent, _entry_deadline_off, monkeypatch):
    class C(FakeClient):
        def __init__(self): super().__init__(); self.bars = [{"t": "2026-09-29T15:00:00Z", "c": 6000.0}]
        def place_order(self, account_id, contract_id, order_type, side, size, price=None, stop_price=None):
            oid = super().place_order(account_id, contract_id, order_type, side, size, price=price, stop_price=stop_price)
            if order_type == pe.OrderType.MARKET:
                self.order_records[oid].update({"filledPrice": 6000.75, "updateTimestamp": "2026-09-29T15:00:02Z"})
            return oid
    client = C(); placed_before = None
    monkeypatch.setattr(pe, "authenticate", lambda: client); monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
    monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 9, "SELL_SIDE_INT": 7})
    monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(2026, 9, 29, 14, 31, tzinfo=pe.CT))
    pe._LAST_EMPTY_POLL = None
    fake_gist[pe.ORDER_FILE] = _signal()
    pe.run_once()
    assert len(client.placed_orders) == 3                                           # el comportamiento de ordenes no cambia: entrada + TP + SL
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["slip_ticks"] == 3.0 and e["exec"]["ref_price"] == 6000.0 and e["exec"]["fill_price"] == 6000.75
    assert e["exec"]["t_fill"] == "updateTimestamp=2026-09-29T15:00:02Z" and e["exec"]["lat_send_to_ack_ms"] >= 0 and e["exec"]["t_ref_bar"] == "2026-09-29T15:00:00Z"
    op = [m for m in sent if "[OPEN]" in m][0]
    assert "Latencia: referencia→envío" in op and "slippage de entrada: +3.00 ticks" in op


def test_poll_sin_señal_marca_el_ultimo_poll_vacio(fake_gist, monkeypatch):
    pe._LAST_EMPTY_POLL = None
    pe.run_once()
    assert pe._LAST_EMPTY_POLL is not None


def test_exit_slip_ticks_convencion():
    assert exit_slip_ticks(1, "SL", 6010.0, 5975.0, 5974.50, 0.25) == 2.0          # stop de un LARGO lleno 2 ticks abajo: adverso
    assert exit_slip_ticks(-1, "SL", 5990.0, 6025.0, 6025.50, 0.25) == 2.0         # stop de un CORTO lleno arriba: adverso
    assert exit_slip_ticks(1, "TP", 6010.0, 5975.0, 6010.25, 0.25) == -1.0         # limite lleno 1 tick mejor: mejora
    assert exit_slip_ticks(1, "FLATTEN", 6010.0, 5975.0, 6001.0, 0.25) is None and exit_slip_ticks(1, "SL", None, None, 6000.0, 0.25) is None
    assert exit_slip_ticks(0, "SL", 1.0, 1.0, 1.0, 0.25) is None


def test_finalize_registra_exec_exit(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    st = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 100, "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102,
          "contract_id": "CON.MES.Z26", "account_id": 555, "opened_at": "x"}
    pe._finalize_cycle(FakeClient(), 555, st, {"result": "SL", "exit_price": 5974.5, "exit_price_estimated": False})
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["exec_exit"] == {"result": "SL", "trigger": 5975.0, "exit_price": 5974.5, "slip_exit_ticks": 2.0}
    pe._finalize_cycle(FakeClient(), 555, st, {"result": "SL", "exit_price": 5975.0, "exit_price_estimated": True})
    assert "exec_exit" not in fake_gist["geometry_mes_log.json"][-1]            # un precio estimado no se registra como medición

