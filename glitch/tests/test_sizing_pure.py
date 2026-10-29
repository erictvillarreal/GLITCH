"""
Glitch — Pruebas de las tres palancas de tamaño (28-oct-2026; NEEDS HUMAN REVIEW): finish-line del Combine, regla de tamaño de la XFA y bracket 728.
Todas APAGADAS por defecto; estas pruebas fijan (a) la formula, (b) que el default no cambia nada, (c) los limites de seguridad. Sin red.
"""
import dataclasses
import math
import os
import subprocess
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
for _k, _v in (("TOPSTEP_USERNAME", "test-user-not-real"), ("TOPSTEP_API_KEY", "test-key-not-real"), ("TOPSTEP_ACCOUNT_ID", "555"),
               ("GLITCH_PRODUCT", "MES")):
    os.environ.setdefault(_k, _v)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

from strategies.geometry_pure import CANDIDATES
from strategies import sizing_pure as sp

MES = CANDIDATES["MES"]
KW = dict(tp_ticks=MES.tp_ticks, tick_value_usd=MES.spec.tick_value_usd, commission_roundturn=MES.spec.commission_roundturn)
PER = sp.tp_net_per_contract(MES.tp_ticks, MES.spec.tick_value_usd, MES.spec.commission_roundturn, 3.0)       # (32-3)*1.25-1.22 = 35.03
TARGET = 3000.0


class TestFinishLine:
    def test_fixed_is_the_current_behaviour(self):
        for need in (-500.0, 0.0, 50.0, 3000.0):
            assert sp.nc_for_day("fixed", 40, need_usd=need, **KW) == 40

    def test_invalid_mode_and_cap(self):
        with pytest.raises(ValueError):
            sp.nc_for_day("otro", 40, need_usd=100, **KW)
        with pytest.raises(ValueError):
            sp.nc_for_day("finish_line", 0, need_usd=100, **KW)

    def test_per_contract_value(self):
        assert PER == pytest.approx(29 * 1.25 - 1.22)

    @pytest.mark.parametrize("need", [1.0, 35.0, 36.0, 100.0, 500.0, 1000.0, 1400.0])
    def test_formula_and_one_tp_covers_the_shortfall(self, need):
        n = sp.nc_for_day("finish_line", 40, need_usd=need, **KW)
        assert n == min(max(math.ceil(need / PER - 1e-9), 1), 40)
        if n < 40:
            assert n * PER >= need - 1e-9                      # un TP del tamaño de hoy cubre el faltante
            assert (n - 1) * PER < need or n == 1             # y es el MINIMO que lo cubre

    def test_never_exceeds_cap_nor_drops_below_one(self):
        assert sp.nc_for_day("finish_line", 40, need_usd=3000, **KW) == 40            # falta mucho: todo el tamaño
        assert sp.nc_for_day("finish_line", 40, need_usd=-200, **KW) == 1             # ya paso: 1 contrato
        assert sp.nc_for_day("finish_line", 10, need_usd=3000, **KW) == 10            # cap menor que el de la config
        assert sp.nc_for_day("finish_line", 40, need_usd=1e9, **KW) == 40

    def test_tp_that_does_not_cover_costs_keeps_the_validated_size(self):
        assert sp.nc_for_day("finish_line", 40, need_usd=100, tp_ticks=2, tick_value_usd=1.25, commission_roundturn=1.22) == 40

    def test_need_includes_the_consistency_rule(self):
        assert sp.combine_need_usd(1000, 0, TARGET) == 2000                           # sin dias ganadores: la meta
        assert sp.combine_need_usd(1000, 1650, TARGET) == 2000                        # mejor dia = 55 % de la meta: exacto, sin cambio
        assert sp.combine_need_usd(2000, 1800, TARGET) == pytest.approx(1800 / 0.55 - 2000)   # 3272.73: la meta SUBE
        assert sp.combine_need_usd(3100, 1000, TARGET) == -100                        # ya cruzo la meta

    def test_finish_line_never_reduces_below_what_passes_when_consistency_binds(self):
        # mejor dia de $1,800 -> meta efectiva $3,272.73; con $2,000 de P&L el faltante es $1,272.73 -> 37 contratos, no 29 (que serian los de una meta de $3,000)
        need = sp.combine_need_usd(2000, 1800, TARGET)
        n = sp.nc_for_day("finish_line", 40, need_usd=need, **KW)
        assert n == 37 and n > sp.nc_for_day("finish_line", 40, need_usd=TARGET - 2000, **KW)

    def test_reduced_tp_keeps_the_best_day_within_55pct_of_the_final_profit(self):
        # propiedad: si el dia de hoy se reduce (n < cap) y sale TP, el P&L resultante cumple la meta Y la consistencia (hoy no se vuelve un mejor dia excesivo)
        for bal in range(0, 2900, 50):
            for best in (0, 600, 1200, 1650, 1800):
                if best > bal and bal > 0:
                    continue
                need = sp.combine_need_usd(bal, best, TARGET)
                n = sp.nc_for_day("finish_line", 40, need_usd=need, **KW)
                if n >= 40 or need <= 0:
                    continue
                gain = n * PER
                new_bal = bal + gain
                new_best = max(best, gain)
                assert new_bal >= TARGET - 1e-6
                assert new_best <= 0.55 * new_bal + 1e-6, (bal, best, n)


class TestXfaSizeRule:
    def test_parse(self):
        assert sp.parse_xfa_size_rule(None) is None
        assert sp.parse_xfa_size_rule("") is None
        assert sp.parse_xfa_size_rule("  ") is None
        assert sp.parse_xfa_size_rule("5:1500:1") == (5, 1500.0, 1)
        assert sp.parse_xfa_size_rule(" 4:1000:2 ") == (4, 1000.0, 2)

    @pytest.mark.parametrize("bad", ["5:1500", "5:1500:1:2", "a:b:c", "1:1500:1", "5:1500:5", "13:1500:1", "5:0:1", "5:99999:1", "5:1500:0"])
    def test_parse_rejects_malformed_or_out_of_bounds(self, bad):
        with pytest.raises(ValueError):
            sp.parse_xfa_size_rule(bad)

    def test_rule_uses_balance_above_start(self):
        assert sp.xfa_nc_for_balance(50_000, 50_000, 5, 1500, 1) == 5
        assert sp.xfa_nc_for_balance(51_499.99, 50_000, 5, 1500, 1) == 5
        assert sp.xfa_nc_for_balance(51_500, 50_000, 5, 1500, 1) == 1                 # `b < U` estricto, igual que la regla evaluada
        assert sp.xfa_nc_for_balance(49_000, 50_000, 5, 1500, 1) == 5

    def test_max_five_micros_is_inside_topsteps_xfa_scaling(self):
        # escalado de MGC (help.topstep.com): 12 micros con saldo < $1,500; la regla evaluada nunca pasa de 5 y el parser tope es 12
        assert max(sp.parse_xfa_size_rule("5:1500:1")[0], 1) <= 12


class TestBracket:
    def test_default_and_unset(self):
        assert sp.xfa_bracket_from_env(None) == 364
        assert sp.xfa_bracket_from_env("") == 364
        assert sp.xfa_bracket_from_env("364") == 364

    def test_728_accepted(self):
        assert sp.xfa_bracket_from_env("728") == 728
        assert sp.xfa_bracket_from_env(" 728 ") == 728

    @pytest.mark.parametrize("raw", ["500", "1456", "abc", "7.28", "-728", "0"])
    def test_unevaluated_values_fall_back(self, raw):
        assert sp.xfa_bracket_from_env(raw) == 364


class TestMesSchedulerHook:
    def test_best_day_aggregates_by_date_and_ignores_losses_and_other_attempts(self):
        import scheduler.geometry_scheduler as gs
        log = [{"date": "2026-10-01", "result": "TP", "pnl": 900.0, "intento": 1},
               {"date": "2026-10-02", "result": "SL", "pnl": -1300.0, "intento": 1},
               {"date": "2026-10-05", "result": "TP", "pnl": 1500.0, "intento": 2},
               {"date": "2026-10-06", "result": "RECONCILED", "pnl": 9999.0, "intento": 1}]
        assert gs._attempt_best_day(log, 1) == 900.0
        assert gs._attempt_best_day(log, 2) == 1500.0
        assert gs._attempt_best_day([], 1) == 0.0
        assert gs._attempt_best_day([{"date": "d", "result": "SL", "pnl": -50.0, "intento": 1}], 1) == 0.0

    def test_default_mode_is_fixed(self):
        import scheduler.geometry_scheduler as gs
        assert gs.ADAPTIVE_NC_MODE == "fixed" or os.environ.get("GLITCH_ADAPTIVE_NC")
        assert set(gs._NC_MODES) == {"fixed", "finish_line"}


def _run(code, **env):
    e = {k: v for k, v in os.environ.items() if k not in ("DRY_RUN", "GLITCH_XFA_BRACKET_TICKS", "GLITCH_PRODUCT")}
    e.update(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c", GITHUB_GIST_TOKEN="g", GIST_ID="i", MASSIVE_API_KEY="m")
    e.update(env)
    pre = "import requests\nrequests.post = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('sin red en pruebas'))\n"
    return subprocess.run([sys.executable, "-c", pre + code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)


class TestMgcSchedulerBracket:
    CODE = "import scheduler.geometry_mgc_scheduler as m; print(m.REAL_CFG.sl_ticks, m.REAL_CFG.tp_ticks, m.REAL_CFG.nc)"

    def test_default_keeps_364x3(self):
        r = _run(self.CODE, GLITCH_PRODUCT="MGC")
        assert r.returncode == 0, r.stderr[-400:]
        assert r.stdout.split()[-3:] == ["364", "364", "3"]

    def test_env_728_changes_only_the_bracket(self):
        r = _run(self.CODE, GLITCH_PRODUCT="MGC", GLITCH_XFA_BRACKET_TICKS="728")
        assert r.returncode == 0, r.stderr[-400:]
        assert r.stdout.split()[-3:] == ["728", "728", "3"]

    def test_unevaluated_value_is_ignored(self):
        r = _run(self.CODE, GLITCH_PRODUCT="MGC", GLITCH_XFA_BRACKET_TICKS="999")
        assert r.returncode == 0, r.stderr[-400:]
        assert r.stdout.split()[-3:] == ["364", "364", "3"]


class TestPiSizeRule:
    @pytest.fixture
    def pe(self, monkeypatch):
        import pi.pi_executor as pe
        monkeypatch.setattr(pe, "CFG", CANDIDATES["MGC"])
        monkeypatch.setattr(pe, "XFA_START_BALANCE", 50_000.0)
        monkeypatch.setattr(pe, "_is_test_signal", lambda s: s.get("product") != "MGC")      # el Pi de las pruebas corre con GLITCH_PRODUCT=MES
        return pe

    class _C:
        def __init__(self, balance):
            self.accounts = [{"id": 555, "balance": balance}] if balance is not None else [{"id": 555}]

        def get_accounts(self, only_active=True):
            return self.accounts

    def _sig(self, **kw):
        s = {"date": "2026-10-29", "side": 1, "direction": "LONG", "product_code": "MGC", "nc": 3, "sl_ticks": 728, "tp_ticks": 728,
             "product": "MGC", "intento": 1, "dry_run": False}
        s.update(kw)
        return s

    def test_off_by_default_leaves_the_signal_intact(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", None)
        sig = self._sig()
        assert pe._apply_xfa_size_rule(self._C(50_000.0), 555, sig) is sig

    def test_high_below_threshold_low_above(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", (5, 1500.0, 1))
        out = pe._apply_xfa_size_rule(self._C(50_400.0), 555, self._sig())
        assert out["nc"] == 5 and out["nc_signal"] == 3
        out = pe._apply_xfa_size_rule(self._C(51_700.0), 555, self._sig())
        assert out["nc"] == 1 and out["nc_signal"] == 3

    def test_does_not_mutate_the_original(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", (5, 1500.0, 1))
        sig = self._sig()
        pe._apply_xfa_size_rule(self._C(50_000.0), 555, sig)
        assert sig["nc"] == 3 and "nc_signal" not in sig

    def test_missing_balance_keeps_the_signal_size(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", (5, 1500.0, 1))
        sig = self._sig()
        assert pe._apply_xfa_size_rule(self._C(None), 555, sig) is sig

    def test_test_signals_and_other_products_are_untouched(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", (5, 1500.0, 1))
        test_sig = self._sig(product="MES")                                         # product != GLITCH_PRODUCT -> señal de ensayo
        assert pe._apply_xfa_size_rule(self._C(50_000.0), 555, test_sig) is test_sig
        monkeypatch.setattr(pe, "CFG", CANDIDATES["MES"])
        sig = self._sig()
        assert pe._apply_xfa_size_rule(self._C(50_000.0), 555, sig) is sig

    def test_local_cap_still_wins_after_the_rule(self, pe, monkeypatch):
        monkeypatch.setattr(pe, "XFA_SIZE_RULE", (5, 1500.0, 1))
        monkeypatch.setattr(pe, "NC_MAX", 2)
        out = pe._apply_nc_cap(pe._apply_xfa_size_rule(self._C(50_000.0), 555, self._sig()))
        assert out["nc"] == 2

    def test_bad_env_rule_is_off_not_crash(self):
        r = _run("import pi.pi_executor as p; print(p.XFA_SIZE_RULE)", GLITCH_PRODUCT="MGC", TOPSTEP_USERNAME="u", TOPSTEP_API_KEY="k",
                 TOPSTEP_ACCOUNT_ID="555", GLITCH_PI_XFA_SIZE_RULE="9:1500")
        assert r.returncode == 0, r.stderr[-500:]
        assert r.stdout.strip().endswith("None")


class TestMesSignalEndToEnd:
    """scheduler.run() en modo real con un intento a $2,400 (mejor dia $1,500): el faltante efectivo es max(3000, 1500/0.55) − 2400 = $600."""

    LOG = [{"date": "2026-09-25", "result": "TP", "pnl": 900.0, "intento": 1, "nc": 40},
           {"date": "2026-09-26", "result": "TP", "pnl": 1500.0, "intento": 1, "nc": 40}]

    def _go(self, monkeypatch, mode):
        import scheduler.geometry_scheduler as scheduler
        import tests.test_geometry_parity as tgp
        monkeypatch.setattr(scheduler, "DRY_RUN", False)
        monkeypatch.setattr(scheduler, "ADAPTIVE_NC_MODE", mode)
        sent = []
        tgp.TestDryRunFalseDelegatesToPi()._patch_common(monkeypatch, sent)
        monkeypatch.setattr(scheduler, "load_log", lambda: list(self.LOG))
        monkeypatch.setattr(scheduler, "load_order_signal", lambda: {})
        captured = {}
        monkeypatch.setattr(scheduler, "save_order_signal", lambda d: captured.update(d))
        scheduler.run()
        return captured, sent

    def test_fixed_sends_the_configured_size(self, monkeypatch):
        sig, _ = self._go(monkeypatch, "fixed")
        assert sig["nc"] == 40 and sig["sl_ticks"] == 100 and sig["tp_ticks"] == 32

    def test_finish_line_sends_the_reduced_size_and_leaves_the_bracket_alone(self, monkeypatch):
        sig, sent = self._go(monkeypatch, "finish_line")
        need = sp.combine_need_usd(2400.0, 1500.0, TARGET)
        assert need == pytest.approx(600.0)                                     # la consistencia no muerde aqui: 1500/0.55 = 2727 < 3000
        assert sig["nc"] == sp.nc_for_day("finish_line", 40, need_usd=need, **KW) == 18
        assert sig["sl_ticks"] == 100 and sig["tp_ticks"] == 32
        assert any("Contracts: 18" in m for m in sent)

    def test_invalid_mode_falls_back_to_fixed(self, monkeypatch):
        sig, _ = self._go(monkeypatch, "agresivo")
        assert sig["nc"] == 40
