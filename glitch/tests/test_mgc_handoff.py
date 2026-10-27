"""T4 (12-oct-2026) -- handoff real de Cerebro 2 (MGC) al Pi, alineacion de geometria y regla de roll del oro. Sin red: Gist, Telegram y Massive se sustituyen por dobles."""
import datetime as dt
import importlib
import os
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import strategies.geometry_pure as geo
from execution import contracts as C


class TestGeometryAlignment:
    def test_mgc_is_the_xfa_50k_geometry(self):
        c = geo.CANDIDATES["MGC"]
        assert (c.sl_ticks, c.tp_ticks, c.nc) == (364, 364, 3)

    def test_sizes_and_paper_alias(self):
        assert geo.CANDIDATES["MGC_XFA_100K"].nc == 4 and geo.CANDIDATES["MGC_XFA_150K"].nc == 6
        assert all(geo.CANDIDATES[k].sl_ticks == geo.CANDIDATES[k].tp_ticks == 364 for k in ("MGC", "MGC_XFA_100K", "MGC_XFA_150K"))

    def test_never_above_official_cap(self):
        """El tope oficial de MGC en Combine/XFA es 30 micros (Risk Adjustments); SPECS['MGC'].nc_cap = 30."""
        for k in ("MGC", "MGC_XFA_100K", "MGC_XFA_150K"):
            assert geo.CANDIDATES[k].nc <= geo.CANDIDATES[k].spec.nc_cap == 30

    def test_legacy_combine_candidate_kept_only_as_reference(self):
        l = geo.CANDIDATES["MGC_COMBINE_LEGACY"]
        assert (l.sl_ticks, l.tp_ticks, l.nc) == (136, 45, 30)

    def test_invalid_size_rejected(self):
        with pytest.raises(ValueError):
            geo.xfa_mgc_config("25K")


class TestGoldRollRule:
    CANDS = [("MGCV6", "2026-10-28"), ("MGCX6", "2026-11-25"), ("MGCZ6", "2026-12-29"), ("MGCG7", "2027-02-24")]

    def test_first_notice_day(self):
        assert C.first_notice_day(2026, 10) == dt.date(2026, 9, 30)
        assert C.first_notice_day(2026, 12) == dt.date(2026, 11, 30)
        assert C.first_notice_day(2027, 2) == dt.date(2027, 1, 29)       # 31-ene-2027 es domingo -> viernes 29

    def test_october_contract_dropped_before_its_fnd(self):
        pick = lambda d: C.apply_roll_rule("MGC", self.CANDS, d)[0][0]
        assert pick(dt.date(2026, 9, 25)) == "MGCV6"
        assert pick(dt.date(2026, 9, 28)) == "MGCZ6"            # FND 30-sep, 2 dias habiles antes
        assert pick(dt.date(2026, 10, 1)) == "MGCZ6"            # el dia del incidente: MGCV6 sin barras, el front es Z6
        assert pick(dt.date(2026, 10, 28)) == "MGCZ6"

    def test_non_active_months_are_skipped(self):
        assert all(t != "MGCX6" for t, _ in C.apply_roll_rule("MGC", self.CANDS, dt.date(2026, 9, 1)))

    def test_december_rolls_to_february(self):
        assert C.apply_roll_rule("MGC", self.CANDS, dt.date(2026, 11, 20))[0][0] == "MGCZ6"
        assert C.apply_roll_rule("MGC", self.CANDS, dt.date(2026, 12, 1))[0][0] == "MGCG7"

    def test_falls_back_when_filter_would_empty_the_list(self):
        only_v6 = [("MGCV6", "2026-10-28")]
        assert C.apply_roll_rule("MGC", only_v6, dt.date(2026, 10, 1)) == only_v6

    def test_other_products_untouched(self):
        mes = [("MESZ6", "2026-12-18"), ("MESH7", "2027-03-19")]
        assert C.apply_roll_rule("MES", mes, dt.date(2026, 12, 17)) == mes

    def test_resolve_front_month_uses_the_rule(self, monkeypatch):
        monkeypatch.setattr(C, "_get", lambda path, params, max_pages=20: [
            {"ticker": t, "last_trade_date": l, "type": "single"} for t, l in self.CANDS] + [{"ticker": "MGCV6-MGCZ6", "last_trade_date": "2026-10-28", "type": "spread"}])
        assert C.resolve_front_month("MGC", today=dt.date(2026, 10, 1))[0] == "MGCZ6"
        assert C.resolve_front_month("MGC", today=dt.date(2026, 9, 24))[0] == "MGCV6"


@pytest.fixture
def real_sched(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "false"); monkeypatch.setenv("GLITCH_PRODUCT", "MGC")
    import scheduler.geometry_mgc_scheduler as s
    s = importlib.reload(s)
    yield s
    monkeypatch.delenv("DRY_RUN", raising=False); monkeypatch.delenv("GLITCH_PRODUCT", raising=False)
    importlib.reload(s)


class Env:
    """Dobles: Gist en memoria, Telegram, reloj."""
    def __init__(self, s, monkeypatch, hh=7, mm=20, flatten_min=14 * 60 + 30, existing=None):
        self.sent = []; self.store = {s.ORDER_FILE: existing or {}}
        monkeypatch.setattr(s, "send", lambda m: self.sent.append(m))
        monkeypatch.setattr(s, "_gist_load_state", lambda f: dict(self.store.get(f, {})))
        monkeypatch.setattr(s, "_gist_save_state", lambda f, d: self.store.__setitem__(f, d))
        monkeypatch.setattr(s, "ct_now", lambda: dt.datetime(2026, 10, 19, hh, mm, tzinfo=s.CT))
        monkeypatch.setattr(s, "flatten_minutes_ct", lambda d: flatten_min)
        monkeypatch.setattr(s, "is_trading_day", lambda: True)
        monkeypatch.setattr(s, "load_log", lambda: [])
        monkeypatch.setattr(s, "save_log", lambda l: None)
        monkeypatch.setattr(s, "load_pending", lambda: {})
        monkeypatch.setattr(s, "get_front_month", lambda *a, **k: "MGCZ6")
        monkeypatch.setattr(s, "check_expiry_alerts", lambda *a, **k: None)
        monkeypatch.setattr(s.time, "sleep", lambda *_: None)


class TestHandoff:
    def test_writes_signal_with_pi_contract(self, real_sched, monkeypatch):
        e = Env(real_sched, monkeypatch)
        real_sched.run()
        sig = e.store["orden_pendiente_mgc.json"]
        assert sig["product"] == "MGC" and sig["product_code"] == "MGC" and sig["dry_run"] is False
        assert (sig["nc"], sig["sl_ticks"], sig["tp_ticks"]) == (3, 364, 364)
        assert sig["side"] in (1, -1) and sig["direction"] == ("LONG" if sig["side"] == 1 else "SHORT") and sig["date"] == str(dt.date.today())
        assert set(sig) == {"date", "side", "direction", "ticker", "product_code", "nc", "sl_ticks", "tp_ticks", "product", "intento", "dry_run"}   # mismo contrato que MES
        assert any("SEÑAL ENVIADA AL PI" in m for m in e.sent)

    def test_product_matches_the_pi_product_key(self, real_sched, monkeypatch):
        """pi_executor._is_test_signal compara signal['product'] con GLITCH_PRODUCT: si difieren, el Pi la trata como ensayo (<= 2 contratos, sin marcador)."""
        e = Env(real_sched, monkeypatch); real_sched.run()
        assert e.store[real_sched.ORDER_FILE]["product"] == real_sched.REAL_PRODUCT_KEY == os.environ["GLITCH_PRODUCT"]

    def test_never_overwrites_an_unconsumed_signal(self, real_sched, monkeypatch):
        prev = {"date": "2026-10-16", "side": 1, "nc": 3}
        e = Env(real_sched, monkeypatch, existing=prev)
        real_sched.run()
        assert e.store[real_sched.ORDER_FILE] == prev and any("BLOCKED" in m for m in e.sent)

    def test_refuses_after_flatten_including_early_close(self, real_sched, monkeypatch):
        e = Env(real_sched, monkeypatch, hh=11, mm=45, flatten_min=11 * 60 + 30)       # cierre anticipado 27-nov / 24-dic
        real_sched.run()
        assert e.store[real_sched.ORDER_FILE] == {} and any("despues del cierre" in m for m in e.sent)

    def test_front_month_failure_does_not_block_the_signal(self, real_sched, monkeypatch):
        e = Env(real_sched, monkeypatch)
        def boom(*a, **k): raise RuntimeError("Massive caido")
        monkeypatch.setattr(real_sched, "get_front_month", boom)
        real_sched.run()
        assert e.store[real_sched.ORDER_FILE].get("product") == "MGC"

    def test_waits_for_the_entry_gate(self, real_sched, monkeypatch):
        e = Env(real_sched, monkeypatch, hh=7, mm=5)
        ticks = {"n": 0}
        def sleep(_):
            ticks["n"] += 1
            monkeypatch.setattr(real_sched, "ct_now", lambda: dt.datetime(2026, 10, 19, 7, 14, tzinfo=real_sched.CT))
        monkeypatch.setattr(real_sched.time, "sleep", sleep)
        real_sched.run()
        assert ticks["n"] >= 1 and e.store[real_sched.ORDER_FILE].get("product") == "MGC"
        assert real_sched.ENTRY_GATE_MINUTES == 7 * 60 + 13

    def test_real_mode_uses_50k_thresholds_paper_keeps_150k(self, real_sched):
        from core.prop_firm import TOPSTEP_50K
        assert real_sched.PROFIT_TARGET == TOPSTEP_50K.profit_target == 3_000 and real_sched.MLL_THRESHOLD == -TOPSTEP_50K.mll_distance == -2_000

    def test_paper_mode_unchanged(self, monkeypatch):
        monkeypatch.delenv("DRY_RUN", raising=False); monkeypatch.delenv("GLITCH_PRODUCT", raising=False)
        import scheduler.geometry_mgc_scheduler as s
        s = importlib.reload(s)
        assert s.DRY_RUN is True and s.PROFIT_TARGET == 9_000 and s.MLL_THRESHOLD == -4_500 and s.CFG.nc == 6
