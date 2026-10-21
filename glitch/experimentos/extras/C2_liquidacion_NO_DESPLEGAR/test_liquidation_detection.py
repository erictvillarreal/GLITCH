"""PROPUESTA (NO DESPLEGAR) -- C2: deteccion determinista de liquidacion por MLL en el Pi.

Reproduce el caso del 19-oct-2026: ambas patas ausentes + cuenta plana -> hoy result=UNKNOWN, pnl 0 y el intento NO avanza.
Sin red: FakeClient + gist en memoria de tests/test_pi_executor.py.
"""
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
os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pe
import scheduler.geometry_scheduler as sched
from pi.liquidation_pure import classify_unknown_exit, liq_pnl
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent  # noqa: F401

MES = "CON.MES.Z26"


# ── pura ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cuenta_ausente_con_otras_cuentas_activas_es_liq():
    v = classify_unknown_exit(account_id=555, active_accounts=[{"id": 999, "canTrade": True}])
    assert v["result"] == "LIQ" and v["evidence"].startswith("E1")


def test_canTrade_false_es_liq():
    v = classify_unknown_exit(account_id=555, active_accounts=[{"id": 555, "canTrade": False, "balance": 49400}])
    assert v["result"] == "LIQ" and v["evidence"].startswith("E2")


def test_lista_vacia_es_ambigua_no_liq():
    v = classify_unknown_exit(account_id=555, active_accounts=[], all_accounts=[])
    assert v == {"result": "UNKNOWN", "evidence": None, "suspected": True}


def test_lista_vacia_pero_cuenta_inactiva_en_el_listado_completo_con_canTrade_false():
    v = classify_unknown_exit(account_id=555, active_accounts=[], all_accounts=[{"id": 555, "canTrade": False}])
    assert v["result"] == "LIQ"


def test_cuenta_operable_con_balance_cerca_del_piso_solo_es_sospecha():
    v = classify_unknown_exit(account_id=555, active_accounts=[{"id": 555, "canTrade": True, "balance": 49420.0}], floor_abs=49401.2)
    assert v["result"] == "UNKNOWN" and v["suspected"] is True


def test_cuenta_normal_sigue_unknown_sin_sospecha():
    v = classify_unknown_exit(account_id=555, active_accounts=[{"id": 555, "canTrade": True, "balance": 51000.0}], floor_abs=49401.2)
    assert v == {"result": "UNKNOWN", "evidence": None, "suspected": False}


def test_lectura_fallida_no_clasifica():
    assert classify_unknown_exit(account_id=555, active_accounts=None)["result"] == "UNKNOWN"


def test_liq_pnl_deja_el_intento_en_el_piso():
    assert liq_pnl(1401.2, -598.8) == -2000.0
    assert liq_pnl(0.0, -2000.0) == -2000.0
    assert liq_pnl(None, -2000.0) is None and liq_pnl(0.0, None) is None


# ── Pi: _finalize_cycle ─────────────────────────────────────────────────────────────────────────────────────────
def _state(**sig_over):
    sig = _signal(); sig.update({"attempt_pnl_before": 1401.2, "attempt_floor": -598.8}); sig.update(sig_over)
    return {"phase": "bracket_open", "signal": sig, "entry_price": 6000.0, "entry_order_id": 100,
            "tp_price": 6010.0, "sl_price": 5975.0, "tp_order_id": 101, "sl_order_id": 102,
            "contract_id": MES, "account_id": 555, "opened_at": "x"}


UNKNOWN = {"result": "UNKNOWN", "exit_price": None, "exit_price_estimated": True}


def test_unknown_con_cuenta_terminada_se_registra_como_liq_con_pnl_en_el_piso(fake_gist, monkeypatch):
    msgs = []
    monkeypatch.setattr(pe, "send", lambda m: msgs.append(m))
    c = FakeClient(); c.accounts = [{"id": 999, "canTrade": True}]           # la 555 ya no figura (cuenta liquidada)
    pe._finalize_cycle(c, 555, _state(), dict(UNKNOWN))
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["result"] == "LIQ" and e["pnl"] == -2000.0 and e["pnl_estimated"] is True and "needs_review" not in e
    assert any("LIQUIDACION" in m for m in msgs)


def test_la_liquidacion_hace_avanzar_el_intento_y_dispara_quiebre(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    c = FakeClient(); c.accounts = [{"id": 999}]
    log_ = [{"date": "2026-10-19", "result": "TP", "pnl": 1401.2, "intento": 2}]
    st = _state(); st["signal"]["date"] = "2026-10-20"; st["signal"]["intento"] = 2
    fake_gist["geometry_mes_log.json"] = list(log_)
    pe._finalize_cycle(c, 555, st, dict(UNKNOWN))
    lg = fake_gist["geometry_mes_log.json"]
    assert sched._attempt_pnl(lg, 2) == pytest.approx(-598.8)
    assert sched._check_attempt_reset(sched._attempt_pnl(lg, 2), sched.PROFIT_TARGET, sched._attempt_trailing_floor(lg, 2)) == "QUIEBRE"
    assert sched._current_intento(lg) == 3                     # el intento YA avanza solo, sin editar el Gist a mano


def test_unknown_con_cuenta_presente_no_cambia(fake_gist, monkeypatch):
    """Compatibilidad: con la cuenta aun activa y sin canTrade=false, sigue exactamente como antes."""
    monkeypatch.setattr(pe, "send", lambda m: None)
    pe._finalize_cycle(FakeClient(), 555, _state(), dict(UNKNOWN))     # FakeClient.accounts = [{"id": 555}]
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["result"] == "UNKNOWN" and e["needs_review"] is True and e["pnl"] == 0.0 and "liq_suspected" not in e


def test_unknown_con_lista_vacia_se_alerta_pero_no_se_clasifica(fake_gist, monkeypatch):
    msgs = []
    monkeypatch.setattr(pe, "send", lambda m: msgs.append(m))
    c = FakeClient(); c.accounts = []
    pe._finalize_cycle(c, 555, _state(), dict(UNKNOWN))
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["result"] == "UNKNOWN" and e["needs_review"] is True and "liq_suspected" in e
    assert any("SOSPECHA" in m for m in msgs)


def test_sin_estado_previo_en_la_senal_no_se_convierte_a_liq(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    c = FakeClient(); c.accounts = [{"id": 999}]
    st = _state(); del st["signal"]["attempt_pnl_before"]; del st["signal"]["attempt_floor"]
    pe._finalize_cycle(c, 555, st, dict(UNKNOWN))
    e = fake_gist["geometry_mes_log.json"][-1]
    assert e["result"] == "UNKNOWN" and e["needs_review"] is True and "liq_suspected" in e


def test_error_de_la_api_de_cuentas_no_rompe_el_cierre(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    c = FakeClient(); c.get_accounts = lambda only_active=True: (_ for _ in ()).throw(RuntimeError("API caida"))
    pe._finalize_cycle(c, 555, _state(), dict(UNKNOWN))
    assert fake_gist["geometry_mes_log.json"][-1]["result"] == "UNKNOWN"


def test_un_tp_normal_no_consulta_cuentas(fake_gist, monkeypatch):
    monkeypatch.setattr(pe, "send", lambda m: None)
    c = FakeClient(); calls = []
    c.get_accounts = lambda only_active=True: calls.append(1) or []
    pe._finalize_cycle(c, 555, _state(), {"result": "TP", "exit_price": 6010.0, "exit_price_estimated": False})
    assert calls == [] and fake_gist["geometry_mes_log.json"][-1]["result"] == "TP"


# ── scheduler ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_liq_no_cuenta_como_victoria_en_el_pass_rate():
    lg = [{"date": "2026-10-19", "result": "TP", "pnl": 1401.2, "intento": 2},
          {"date": "2026-10-20", "result": "LIQ", "pnl": -2000.0, "intento": 2}]
    prog = sched._paper_progress(lg, "2026-10-21")
    assert prog["n_cycles"] == 2 and prog["pass_rate_empirico"] == 0.5


def test_unknown_sigue_excluido_del_intento():
    lg = [{"date": "2026-10-20", "result": "UNKNOWN", "pnl": 0.0, "intento": 2, "needs_review": True}]
    assert sched._attempt_entries(lg, 2) == []
