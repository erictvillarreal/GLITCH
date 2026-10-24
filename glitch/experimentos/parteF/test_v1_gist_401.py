"""V1 — Fallo silencioso del scheduler (modo real) cuando el token del Gist esta revocado (401). Recorre run() REAL hasta el Telegram,
con send/ct_now/date/sleep/get_front_month parcheados y la API de Gists simulada en memoria (sin red real).
    cd glitch && python -m pytest -q experimentos/parteF/test_v1_gist_401.py"""
import datetime as dt
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
for k in ("MASSIVE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_GIST_TOKEN", "GIST_ID"):
    os.environ.setdefault(k, "test-not-real")

import pytest
from zoneinfo import ZoneInfo
from fake_gist import FakeGist

CT = ZoneInfo("America/Chicago")
MON = dt.date(2026, 10, 26)

# Historial como lo describe el encargo F: ciclos hasta el 20-oct, intento 2 con un TP de +$1,401.20 (20-oct).
HISTORY = [
    {"date": "2026-10-14", "result": "SL", "pnl": -2000.0, "intento": 1, "direction": "SHORT", "side": -1},
    {"date": "2026-10-19", "result": "TP", "pnl": 1551.2, "intento": 2, "direction": "SHORT", "side": -1},
    {"date": "2026-10-20", "result": "TP", "pnl": 1401.2, "intento": 2, "direction": "LONG", "side": 1},
]


class Env:
    pass


@pytest.fixture
def sched(monkeypatch):
    import execution.gist_store as gs
    monkeypatch.setattr(gs, "GITHUB_GIST_TOKEN", "fake-token"); monkeypatch.setattr(gs, "GIST_ID", "fake-id")
    monkeypatch.setenv("GLITCH_PRODUCT", "MES")
    import scheduler.geometry_scheduler as s
    s = importlib.reload(s)
    sent = []
    now = dt.datetime(2026, 10, 26, 9, 36, tzinfo=CT)

    class FakeDate(dt.date):
        @classmethod
        def today(cls): return MON

    monkeypatch.setattr(s, "DRY_RUN", False)
    monkeypatch.setattr(s, "send", lambda m: sent.append(m))
    monkeypatch.setattr(s, "ct_now", lambda: now)
    monkeypatch.setattr(s, "date", FakeDate)
    monkeypatch.setattr(s.time, "sleep", lambda *_: None)
    monkeypatch.setattr(s, "get_front_month", lambda *_a, **_k: "MESZ6")
    monkeypatch.setattr(s, "check_expiry_alerts", lambda *_a, **_k: None)
    e = Env(); e.s, e.sent, e.gs, e.mp = s, sent, gs, monkeypatch
    return e


def install(e, gist):
    e.mp.setattr(e.gs.requests, "get", gist.get); e.mp.setattr(e.gs.requests, "patch", gist.patch)


def test_hipotesis_con_token_revocado_el_scheduler_anuncia_senal_sin_escribir(sched):
    """401 en TODAS las llamadas al Gist. Hipotesis: INICIO 'Dia 1 / sin ciclo previo', 'Intento #1', y aun asi '[SEÑAL ENVIADA AL PI]'."""
    gist = FakeGist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": {}}, mode="401")
    install(sched, gist)
    sched.s.run()
    text = "\n".join(sched.sent)
    assert "Dia 1 de paper" in text and "(sin ciclo previo registrado)" in text and "Ciclos completados: 0" in text   # canario
    assert "Intento #1" in text                                                                                       # el correcto era #2
    assert "[SEÑAL ENVIADA AL PI]" in text                                                                            # se anuncia...
    assert gist.read("orden_pendiente_mes.json") == {}                                                                # ...pero NO hay orden en el Gist
    assert len(gist.patches) >= 1 and all(p for p in gist.patches)                                                    # el PATCH se intento y fallo en silencio
    assert not any("STATUS: ERROR" in m for m in sched.sent)                                                          # ningun aviso de error


def test_con_gist_sano_el_inicio_y_la_orden_son_correctos(sched):
    """Mismo recorrido con el Gist sano: texto esperado el lunes (V8.2) y orden escrita con intento 2."""
    gist = FakeGist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": {}})
    install(sched, gist)
    sched.s.run()
    inicio = sched.sent[0]
    assert "INICIO DE DIA" in inicio and "Dia 13 de paper" in inicio          # 2026-10-14 (primera entrada del ejemplo) -> 26-oct = dia 13 (dias CALENDARIO)
    assert "Ciclos completados: 3" in inicio and "Señal de hoy: LONG (day_index=1778" in inicio
    assert "Resultado de ayer: 2026-10-20: LONG → TP  PnL=$+1,401.20" in inicio
    orden = gist.read("orden_pendiente_mes.json")
    assert orden["intento"] == 2 and orden["side"] == 1 and orden["nc"] == 40 and orden["date"] == "2026-10-26"
    assert "Intento #2" in sched.sent[-1] and "[SEÑAL ENVIADA AL PI]" in sched.sent[-1]


def test_lectura_ok_pero_escritura_401_tambien_anuncia_senal(sched):
    """Variante: token con permiso de lectura pero sin escritura (o PATCH rechazado). El historial se lee bien (intento 2 correcto) y aun asi se anuncia."""
    gist = FakeGist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": {}}, mode="write401")
    install(sched, gist)
    sched.s.run()
    assert "Intento #2" in "\n".join(sched.sent) and "[SEÑAL ENVIADA AL PI]" in "\n".join(sched.sent)
    assert gist.read("orden_pendiente_mes.json") == {}


def test_orden_anterior_sin_consumir_si_bloquea_cuando_el_gist_se_lee(sched):
    """Con el Gist sano la orden vieja SI bloquea (comportamiento del MGC el miercoles 21). Con 401 la orden se lee como {} y NO bloquea."""
    viejo = {"date": "2026-10-19", "side": 1, "nc": 3}
    gist = FakeGist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": viejo})
    install(sched, gist); sched.s.run()
    assert any("STATUS: BLOCKED" in m for m in sched.sent) and gist.read("orden_pendiente_mes.json") == viejo
    sched.sent.clear()
    install(sched, FakeGist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": viejo}, mode="401")); sched.s.run()
    assert not any("BLOCKED" in m for m in sched.sent) and any("[SEÑAL ENVIADA AL PI]" in m for m in sched.sent)
