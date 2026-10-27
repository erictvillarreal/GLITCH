"""
Glitch — Pruebas del parche J4-a (26-oct-2026): guardia de colchon del MLL (apagada por defecto). NEEDS HUMAN REVIEW. Sin red.
"""
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
from execution import mll_guard as mg
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent, _fixed_clock, _entry_deadline_off  # noqa: F401


class TestPureFunctions:
    def test_risk_per_contract_mgc(self):
        assert mg.risk_per_contract(364, 1.0, 1.92) == pytest.approx(364 + 1.92 + 3.0)

    def test_cushion_never_negative(self):
        assert mg.cushion_usd(49_000, 49_500) == 0.0 and mg.cushion_usd(50_000, 48_000) == 2_000.0

    @pytest.mark.parametrize("cushion,expected", [(2000, 5), (1100, 2), (368.0, 0), (0, 0)])
    def test_max_contracts(self, cushion, expected):
        assert mg.max_contracts_for_cushion(cushion, 364, 1.0, 1.92) == expected

    def test_strict_inequality_at_the_boundary(self):
        # riesgo por contrato = 100 + 0 + 3 = 103 (enteros: sin ambiguedad de punto flotante)
        assert mg.max_contracts_for_cushion(206.0, 100, 1.0, 0.0) == 1          # 2 contratos perderian EXACTAMENTE el colchon: no caben
        assert mg.max_contracts_for_cushion(206.01, 100, 1.0, 0.0) == 2

    def test_decide_ok_reduce_block(self):
        assert mg.decide(3, 2000, 364, 1.0, 1.92) == (3, "ok")
        nc, why = mg.decide(3, 908, 364, 1.0, 1.92); assert nc == 2 and "reduce" in why
        nc, why = mg.decide(3, 300, 364, 1.0, 1.92); assert nc == 0 and "colchon" in why


class TestPiHook:
    def _setup(self, monkeypatch, fake_gist, balance, floor, guard=True):
        client = FakeClient()
        client.accounts = [{"id": 555, "balance": balance}]
        monkeypatch.setattr(pe, "authenticate", lambda: client)
        monkeypatch.setattr(pe, "PHASE3_ENABLED", True)
        monkeypatch.setattr(pe, "_load_verified_side_map", lambda: {"BUY_SIDE_INT": 9, "SELL_SIDE_INT": 7})
        monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(2026, 9, 29, 14, 31, tzinfo=pe.CT))      # corta el poll de inmediato
        monkeypatch.setattr(pe, "MLL_GUARD", guard)
        if floor is None:
            monkeypatch.delenv("GLITCH_PI_MLL_FLOOR_USD", raising=False)
        else:
            monkeypatch.setenv("GLITCH_PI_MLL_FLOOR_USD", str(floor))
        fake_gist[pe.ORDER_FILE] = _signal()                                                            # MES: nc 40, SL 100
        return client

    def test_guard_is_off_by_default(self):
        assert pe.MLL_GUARD is False or os.environ.get("GLITCH_PI_MLL_GUARD") == "si"

    def test_off_leaves_the_signal_untouched(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=50_000.0, floor=49_999.0, guard=False)
        pe.run_once()
        assert client.placed_orders[0]["size"] == 40

    def test_on_with_room_trades_full_size(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=60_000.0, floor=50_000.0)             # colchon 10,000 > 40 · 129.97
        pe.run_once()
        assert client.placed_orders[0]["size"] == 40

    def test_on_reduces_contracts_to_what_fits(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=54_000.0, floor=50_000.0)             # colchon 4,000 -> 30 contratos de MES
        pe.run_once()
        assert client.placed_orders[0]["size"] == 30
        assert fake_gist["geometry_mes_log.json"][0]["nc"] == 30

    def test_on_blocks_when_not_even_one_fits(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=50_050.0, floor=50_000.0)             # colchon 50 < 129.97
        pe.run_once()
        assert client.placed_orders == []
        assert fake_gist[pe.ORDER_FILE] == {}                                                       # se descarta la señal del dia
        assert any("Guardia de colchon" in m for m in sent)

    def test_on_without_floor_fails_closed(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=60_000.0, floor=None)
        pe.run_once()
        assert client.placed_orders == []
        assert any("falta un dato" in m for m in sent)

    def test_on_without_balance_fails_closed(self, fake_gist, sent, monkeypatch):
        client = self._setup(monkeypatch, fake_gist, balance=60_000.0, floor=50_000.0)
        client.accounts = [{"id": 555}]                                                             # sin `balance`
        pe.run_once()
        assert client.placed_orders == []
