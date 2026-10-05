"""
Glitch -- Tests del tope local de contratos del Pi (GLITCH_PI_NC_MAX, 04-oct-2026).

El tope solo REDUCE el tamaño operado: lado, hora y SL/TP en ticks vienen de la señal, sin cambios. Todo lo que sigue a
la entrada (ordenes, confirmacion del fill, P&L, historial, estado) debe usar los contratos realmente operados.
Sin red (mismos fakes que tests/test_pi_audit_patches.py).
"""
import json
import os
import sys

for _k, _v in (("TOPSTEP_USERNAME", "test-user-not-real"), ("TOPSTEP_API_KEY", "test-key-not-real"),
               ("TOPSTEP_ACCOUNT_ID", "555"), ("TELEGRAM_BOT_TOKEN", "test-token-not-real"),
               ("TELEGRAM_CHAT_ID", "test-chat-not-real"), ("GITHUB_GIST_TOKEN", "test-gist-token-not-real"),
               ("GIST_ID", "test-gist-id-not-real"), ("GLITCH_PRODUCT", "MES")):
    os.environ.setdefault(_k, _v)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pe
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent, _fixed_clock, _entry_deadline_off  # noqa: F401
from tests.test_pi_audit_patches import TpFillsEachCycle, _arm


def _sizes(client):
    return [o["size"] for o in client.placed_orders]


class TestParse:
    def test_unset_or_blank_means_no_cap(self):
        assert pe._parse_nc_cap(None) is None
        assert pe._parse_nc_cap("") is None
        assert pe._parse_nc_cap("   ") is None

    def test_valid_value(self):
        assert pe._parse_nc_cap("10") == 10
        assert pe._parse_nc_cap(" 5 ") == 5

    @pytest.mark.parametrize("bad", ["0", "-3", "abc", "10.5", "diez"])
    def test_invalid_value_fails_small_not_big(self, bad):
        assert pe._parse_nc_cap(bad) == 1


class TestApply:
    def test_caps_and_keeps_original(self, monkeypatch):
        monkeypatch.setattr(pe, "NC_MAX", 10)
        sig = _signal(nc=40)
        out = pe._apply_nc_cap(sig)
        assert out["nc"] == 10 and out["nc_signal"] == 40
        assert sig["nc"] == 40 and "nc_signal" not in sig          # no muta la señal original

    def test_no_cap_when_smaller_or_unset(self, monkeypatch):
        monkeypatch.setattr(pe, "NC_MAX", 10)
        small = _signal(nc=4)
        assert pe._apply_nc_cap(small) is small
        monkeypatch.setattr(pe, "NC_MAX", None)
        big = _signal(nc=40)
        assert pe._apply_nc_cap(big) is big

    def test_label(self):
        assert pe._nc_label(_signal(nc=40)) == "40"
        assert pe._nc_label({**_signal(nc=10), "nc_signal": 40}) == "10 (señal: 40, tope local)"


class TestEndToEnd:
    def test_orders_use_the_capped_size_and_pnl_scales(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pe, "NC_MAX", 10)
        client = TpFillsEachCycle()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal(nc=40)

        pe.run_once()

        assert _sizes(client) == [10, 10, 10]                       # entrada, TP y SL: todo por 10
        (entry,) = fake_gist["geometry_mes_log.json"]
        assert entry["result"] == "TP"
        assert entry["nc"] == 10 and entry["nc_signal"] == 40
        # TP = 40 ticks * $1.25 * 10 contratos = $500 (con 40 serian $2,000)
        assert entry["pnl"] == pytest.approx(500.0)
        texts = "\n".join(sent) if isinstance(sent, list) else str(sent)
        assert "señal: 40, tope local" in texts

    def test_no_cap_keeps_the_old_behavior(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pe, "NC_MAX", None)
        client = TpFillsEachCycle()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal(nc=40)

        pe.run_once()

        assert _sizes(client) == [40, 40, 40]
        (entry,) = fake_gist["geometry_mes_log.json"]
        assert entry["nc"] == 40 and "nc_signal" not in entry
        assert entry["pnl"] == pytest.approx(2000.0)

    def test_signal_above_local_config_is_still_rejected_not_capped(self, fake_gist, sent, monkeypatch):
        """A7 manda: nc=400 es una señal invalida y se descarta; el tope no la 'rescata' operando 10."""
        monkeypatch.setattr(pe, "NC_MAX", 10)
        client = TpFillsEachCycle()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal(nc=400)

        pe.run_once()

        assert client.placed_orders == []
        assert fake_gist[pe.ORDER_FILE] == {}

    def test_test_signals_are_unaffected(self, fake_gist, sent, monkeypatch):
        monkeypatch.setattr(pe, "NC_MAX", 10)
        client = TpFillsEachCycle()
        _arm(monkeypatch, client)
        fake_gist[pe.ORDER_FILE] = _signal(product="MEStest", nc=1)

        pe.run_once()

        assert _sizes(client) == [1, 1, 1]
