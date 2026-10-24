"""V4.4 — Reinicio del Pi a mitad del dia con posicion abierta: la reconciliacion recupera el bracket (pi_position_mes.json) y NO duplica la orden.
Reutiliza los dobles de tests/test_pi_executor.py (FakeClient sin red, Gist en memoria).   cd glitch && python -m pytest -q experimentos/parteF/test_v4_restart.py"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, ROOT)
for _k, _v in (("TOPSTEP_USERNAME", "u"), ("TOPSTEP_API_KEY", "k"), ("TOPSTEP_ACCOUNT_ID", "555"), ("TELEGRAM_BOT_TOKEN", "t"), ("TELEGRAM_CHAT_ID", "c"),
                ("GITHUB_GIST_TOKEN", "g"), ("GIST_ID", "i"), ("GLITCH_PRODUCT", "MES"), ("MASSIVE_API_KEY", "m")):
    os.environ.setdefault(_k, _v + "-test-not-real")
os.environ["TOPSTEP_ACCOUNT_ID"] = "555"; os.environ["GLITCH_PRODUCT"] = "MES"
import pi.pi_executor as pi_executor
from tests.test_pi_executor import FakeClient, _signal, fake_gist, sent, _entry_deadline_off, _fixed_clock   # noqa: F401  (fixtures)


def _state(**kw):
    s = {"phase": "bracket_open", "signal": _signal(), "entry_price": 6000.0, "entry_order_id": 200, "tp_price": 6008.0, "sl_price": 5975.0,
         "tp_order_id": 201, "sl_order_id": 202, "contract_id": "CON.MES.Z26", "account_id": 555, "opened_at": "2026-09-29 09:36 UTC"}
    s.update(kw); return s


def _clock(monkeypatch, start_h, start_m):
    t = {"now": dt.datetime(2026, 9, 29, start_h, start_m, tzinfo=pi_executor.CT)}
    monkeypatch.setattr(pi_executor, "ct_now", lambda: t["now"])
    def sleep(_):
        t["now"] += dt.timedelta(minutes=30)
    monkeypatch.setattr(pi_executor.time, "sleep", sleep)
    return t


def test_reinicio_con_ambas_patas_abiertas_retoma_hasta_el_flatten_sin_ordenes_nuevas(fake_gist, sent, monkeypatch):
    client = FakeClient()
    client.open_order_ids = {201, 202}                                   # el bracket sigue en el libro
    client.positions = [{"id": 200, "accountId": 555, "contractId": "CON.MES.Z26", "type": 1, "size": 40, "averagePrice": 6000.0}]
    fake_gist[pi_executor.PI_STATE_FILE] = _state()
    fake_gist[pi_executor.ORDER_FILE] = _signal()                         # la señal NO se alcanzo a limpiar antes del reinicio
    monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
    _clock(monkeypatch, 10, 30)
    pi_executor.run_once()                                                # = lo que hace main() al arrancar
    assert client.placed_orders == []                                     # NO se coloco ninguna orden nueva
    assert client.closed_contracts == [(555, "CON.MES.Z26")]              # se aplano UNA vez, a las 14:30
    log = fake_gist["geometry_mes_log.json"]
    assert len(log) == 1 and log[0]["result"] == "FLATTEN" and log[0]["intento"] == 1
    assert fake_gist[pi_executor.PI_STATE_FILE] == {} and fake_gist[pi_executor.ORDER_FILE] == {}   # estado y señal limpiados


def test_reinicio_tras_tp_lleno_finaliza_una_sola_vez_y_cancela_el_sl(fake_gist, sent, monkeypatch):
    client = FakeClient()
    client.open_order_ids = {202}                                        # TP ya no esta: se lleno durante la caida
    client.order_records = {201: {"id": 201, "avgFillPrice": 6008.0}}
    fake_gist[pi_executor.PI_STATE_FILE] = _state()
    fake_gist[pi_executor.ORDER_FILE] = _signal()
    monkeypatch.setattr(pi_executor, "authenticate", lambda: client)
    _clock(monkeypatch, 11, 0)
    pi_executor.run_once(); pi_executor.run_once()                       # un segundo ciclo (120 s despues) no debe repetir nada
    assert client.placed_orders == [] and 202 in client.cancelled
    log = fake_gist["geometry_mes_log.json"]
    assert len(log) == 1 and log[0]["result"] == "TP" and log[0]["exit"] == 6008.0
    assert fake_gist[pi_executor.ORDER_FILE] == {} and fake_gist[pi_executor.PI_STATE_FILE] == {}
