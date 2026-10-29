"""PROPUESTA (NO DESPLEGAR) -- C3: registrar slippage REAL de entrada (ref_price, fill_price, slip_ticks)."""
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
from pi.slippage_pure import slippage_ticks
from tests.test_pi_executor import FakeClient, _entry_deadline_off, _signal, fake_gist, sent  # noqa: F401

TICK = 0.25


@pytest.mark.parametrize("side,ref,fill,exp", [
    (1, 6000.00, 6000.25, 1.0),      # LONG compra 1 tick por encima de la referencia -> adverso
    (1, 6000.00, 5999.75, -1.0),     # LONG mejora
    (-1, 6000.00, 5999.25, 3.0),     # SHORT vende 3 ticks por debajo -> adverso
    (-1, 6000.00, 6000.50, -2.0),    # SHORT mejora
    (1, 6000.00, 6000.00, 0.0),
])
def test_slippage_ticks_convencion(side, ref, fill, exp):
    assert slippage_ticks(side, ref, fill, TICK) == exp


@pytest.mark.parametrize("args", [(0, 6000.0, 6000.25, TICK), (1, None, 6000.25, TICK), (1, 6000.0, None, TICK),
                                  (1, 6000.0, 0.0, TICK), (1, 6000.0, 6000.25, 0.0), (1, True, 6000.25, TICK)])
def test_slippage_ticks_entradas_invalidas_dan_none(args):
    assert slippage_ticks(*args) is None


def _state(**over):
    st = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 100,
          "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102,
          "contract_id": "CON.MES.Z26", "account_id": 555, "opened_at": "x"}
    st.update(over); return st


def test_finalize_registra_ref_fill_y_slip(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    c = FakeClient(); c.order_records[100] = {"id": 100, "side": 9, "filledPrice": 6000.75}   # LONG: 3 ticks adversos
    pe._finalize_cycle(c, 555, _state(), {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["ref_price"] == 6000.0 and e["fill_price"] == 6000.75 and e["slip_ticks"] == 3.0
    assert e["entry"] == 6000.75 and e["entry_price_estimated"] is False


def test_finalize_sin_fill_no_inventa_slippage(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    pe._finalize_cycle(FakeClient(), 555, _state(), {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
    e = fake_gist["geometry_mes_log.json"][-1]
    assert not ({"ref_price", "fill_price", "slip_ticks"} & set(e)) and e["entry_price_estimated"] is True


def test_finalize_usa_el_fill_guardado_al_abrir_si_la_consulta_posterior_falla(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    st = _state(ref_price=6000.0, fill_price=5999.5, slip_ticks=-2.0)
    pe._finalize_cycle(FakeClient(), 555, st, {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["fill_price"] == 5999.5 and e["slip_ticks"] == -2.0


def test_run_once_incluye_slippage_en_el_mensaje_open_y_en_el_estado(fake_gist, sent, _entry_deadline_off, monkeypatch):
    class FillingClient(FakeClient):
        def place_order(self, account_id, contract_id, order_type, side, size, price=None, stop_price=None):
            oid = super().place_order(account_id, contract_id, order_type, side, size, price=price, stop_price=stop_price)
            if order_type == pe.OrderType.MARKET:
                self.order_records[oid]["filledPrice"] = 6000.25      # referencia 6000.0 (FakeClient.bars) -> +1 tick
            return oid
    client = FillingClient()
    monkeypatch.setattr(pe, "authenticate", lambda: client)
    monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
    monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 9, "SELL_SIDE_INT": 7})
    monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(2026, 9, 29, 14, 31, tzinfo=pe.CT))
    fake_gist[pe.ORDER_FILE] = _signal()
    pe.run_once()
    opens = [m for m in sent if "[OPEN]" in m]
    assert opens and "slippage de entrada: +1.00 ticks" in opens[0]
    assert fake_gist["geometry_mes_log.json"][-1]["slip_ticks"] == 1.0
