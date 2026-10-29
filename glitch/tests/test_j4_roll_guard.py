"""
Glitch — Pruebas del parche J4-f (26-oct-2026): el Pi aplica la regla de roll del oro cuando la API no trae `activeContract`.
Motivo: sin la marca, el "vencimiento mas cercano" del oro en la semana del 28-oct es MGCV6 (aviso de entrega 30-sep, vence ~28-oct). NEEDS HUMAN REVIEW.
Sin red.
"""
import datetime as dt
import os
import sys

for k, v in (("TOPSTEP_USERNAME", "u"), ("TOPSTEP_API_KEY", "k"), ("TOPSTEP_ACCOUNT_ID", "555"), ("TELEGRAM_BOT_TOKEN", "t"), ("TELEGRAM_CHAT_ID", "c"),
             ("GITHUB_GIST_TOKEN", "g"), ("GIST_ID", "i"), ("GLITCH_PRODUCT", "MES")):
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pe
import strategies.geometry_pure as geo


class _C:
    def __init__(self, contracts): self._c = contracts
    def get_contracts(self, live=False): return list(self._c)


def _gold(flag):
    base = [{"id": "CON.F.US.MGC.V26", "name": "MGCV6", "expirationDate": "2026-10-28", "tickSize": 0.1, "tickValue": 1.0},
            {"id": "CON.F.US.MGC.Z26", "name": "MGCZ6", "expirationDate": "2026-12-29", "tickSize": 0.1, "tickValue": 1.0},
            {"id": "CON.F.US.MGC.G27", "name": "MGCG7", "expirationDate": "2027-02-24", "tickSize": 0.1, "tickValue": 1.0}]
    if flag is None:
        return base
    return [dict(c, activeContract=(c["name"] == flag)) for c in base]


@pytest.fixture
def at(monkeypatch):
    monkeypatch.setattr(pe, "CFG", geo.CANDIDATES["MGC"])
    monkeypatch.setattr(pe, "send", lambda m: None)
    pe._SPEC_WARNED.clear()

    def _set(y, m, d):
        monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(y, m, d, 8, 0, tzinfo=pe.CT))
    return _set


class TestGoldRollWithoutActiveFlag:
    def test_28_oct_without_flag_picks_december_not_the_expiring_october(self, at):
        at(2026, 10, 28)
        assert pe.resolve_contract_id(_C(_gold(None)), "MGC")["name"] == "MGCZ6"

    def test_26_oct_without_flag_picks_december(self, at):
        at(2026, 10, 26)
        assert pe.resolve_contract_id(_C(_gold(None)), "MGC")["name"] == "MGCZ6"

    def test_before_the_roll_window_the_nearest_is_still_chosen(self, at):
        at(2026, 9, 1)
        assert pe.resolve_contract_id(_C(_gold(None)), "MGC")["name"] == "MGCV6"

    def test_if_the_rule_would_empty_the_list_it_falls_back_to_all(self, at):
        at(2026, 10, 28)
        only_old = [c for c in _gold(None) if c["name"] == "MGCV6"]
        assert pe.resolve_contract_id(_C(only_old), "MGC")["name"] == "MGCV6"


class TestActiveFlagStillWins:
    def test_api_flag_is_trusted_even_if_it_marks_the_nearest(self, at):
        at(2026, 10, 28)
        assert pe.resolve_contract_id(_C(_gold("MGCV6")), "MGC")["name"] == "MGCV6"     # decision de la API; no se sobrescribe

    def test_api_flag_on_december(self, at):
        at(2026, 10, 28)
        assert pe.resolve_contract_id(_C(_gold("MGCZ6")), "MGC")["name"] == "MGCZ6"


class TestOtherProductsUnchanged:
    def test_mes_without_flag_still_picks_nearest(self, monkeypatch):
        monkeypatch.setattr(pe, "CFG", geo.CANDIDATES["MES"])
        monkeypatch.setattr(pe, "send", lambda m: None)
        monkeypatch.setattr(pe, "ct_now", lambda: dt.datetime(2026, 10, 28, 8, 0, tzinfo=pe.CT))
        pe._SPEC_WARNED.clear()
        mes = [{"id": "CON.MES.Z26", "name": "MESZ6", "expirationDate": "2026-12-18", "tickSize": 0.25, "tickValue": 1.25},
               {"id": "CON.MES.H27", "name": "MESH7", "expirationDate": "2027-03-19", "tickSize": 0.25, "tickValue": 1.25}]
        assert pe.resolve_contract_id(_C(mes), "MES")["name"] == "MESZ6"


class TestPiDoesNotNeedMassiveKey:
    """El Pi no tiene MASSIVE_API_KEY (ver el comentario de arranque de pi_executor.py): importar execution/contracts.py ahi lo tumbaria al arrancar."""

    def test_pi_executor_imports_without_massive_or_polygon_key(self):
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {k: v for k, v in os.environ.items() if k not in ("MASSIVE_API_KEY", "POLYGON_API_KEY")}
        env.update(TOPSTEP_USERNAME="u", TOPSTEP_API_KEY="k", TOPSTEP_ACCOUNT_ID="5", TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c",
                   GITHUB_GIST_TOKEN="g", GIST_ID="i", GLITCH_PRODUCT="MGC")
        r = subprocess.run([sys.executable, "-c", "import pi.pi_executor"], cwd=root, env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-400:]

    def test_roll_rules_module_has_no_env_requirement(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "test-not-real")      # execution.contracts SI la exige (Railway la tiene); solo se importa aqui para comparar
        import execution.roll_rules as rr
        import execution.contracts as ct
        assert ct.apply_roll_rule is rr.apply_roll_rule and ct.ROLL_RULES is rr.ROLL_RULES      # re-exportados: un solo codigo
