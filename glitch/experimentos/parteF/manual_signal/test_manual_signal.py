"""Pruebas de pi/manual_signal.py (plan B del lunes). Sin red: API de Gists simulada en memoria."""
import datetime as dt
import json
import os
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from zoneinfo import ZoneInfo

import execution.gist_store as gs
from pi import manual_signal as ms

CT = ZoneInfo("America/Chicago")
HISTORY = [
    {"date": "2026-10-14", "result": "SL", "pnl": -2000.0, "intento": 1},
    {"date": "2026-10-19", "result": "TP", "pnl": 1551.2, "intento": 2},
    {"date": "2026-10-20", "result": "TP", "pnl": 1401.2, "intento": 2},
]


def at(y, m, d, h, mi): return dt.datetime(y, m, d, h, mi, tzinfo=CT)
MON_OK = at(2026, 10, 26, 9, 40)


class _Resp:
    def __init__(self, status=200, body=None): self.status_code, self._b = status, body or {}
    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")


class Gist:
    def __init__(self, files=None, mode="ok"):
        self.files = {k: json.dumps(v) for k, v in (files or {}).items()}; self.mode = mode; self.patches = []
    def get(self, *a, **k):
        return _Resp(401) if self.mode == "401" else _Resp(200, {"files": {k_: {"content": v} for k_, v in self.files.items()}})
    def patch(self, url, headers=None, json=None, timeout=None, **k):
        self.patches.append(json)
        if self.mode in ("401", "write401"): return _Resp(401)
        if self.mode != "write_lost":
            for n, o in json["files"].items(): self.files[n] = o["content"]
        return _Resp(200)


@pytest.fixture
def gist(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_GIST_TOKEN", "fake"); monkeypatch.setattr(gs, "GIST_ID", "fake")
    monkeypatch.delenv("GLITCH_PI_NC_MAX", raising=False); monkeypatch.delenv("GLITCH_PI_ENTRY_DEADLINE_CT", raising=False)
    def make(files=None, mode="ok"):
        g = Gist({"geometry_mes_log.json": HISTORY, "orden_pendiente_mes.json": {}, "pi_position_mes.json": {}, **(files or {})}, mode)
        monkeypatch.setattr(gs.requests, "get", g.get); monkeypatch.setattr(gs.requests, "patch", g.patch)
        return g
    return make


def run(argv, now=MON_OK, typed="", notes=None):
    notes = [] if notes is None else notes
    rc = ms.main(argv, now=now, input_fn=lambda _p: typed, notify_fn=lambda t: notes.append(t) or True)
    return rc, notes


def test_dry_run_por_defecto_no_escribe(gist, capsys):
    g = gist(); rc, notes = run([])
    out = capsys.readouterr().out
    assert rc == 0 and g.patches == [] and notes == [] and '"intento": 2' in out and '"direction": "LONG"' in out and "LUNES-LONG-40" in out


def test_feliz_con_confirmacion_escribe_verifica_y_avisa(gist):
    g = gist(); rc, notes = run(["--write", "--confirm", "LUNES-LONG-40"])
    assert rc == 0 and json.loads(g.files["orden_pendiente_mes.json"]) == {
        "date": "2026-10-26", "side": 1, "direction": "LONG", "ticker": "MES=F", "product_code": "MES", "nc": 40,
        "sl_ticks": 100, "tp_ticks": 32, "product": "MES", "intento": 2, "dry_run": False}
    assert len(notes) == 1 and "[SEÑAL MANUAL ENVIADA AL PI]" in notes[0]


def test_confirmacion_tecleada_correcta_e_incorrecta(gist):
    g = gist(); assert run(["--write"], typed="LUNES-LONG-40")[0] == 0
    g = gist(); rc, _ = run(["--write"], typed="lunes long")
    assert rc == 3 and g.patches == []


def test_payload_identico_al_del_scheduler(gist):
    import scheduler.geometry_scheduler as sch
    cfg = sch.CFG
    exp = {"date": "2026-10-26", "side": 1, "direction": "LONG", "ticker": cfg.spec.yf_ticker, "product_code": cfg.spec.product_code,
           "nc": cfg.nc, "sl_ticks": cfg.sl_ticks, "tp_ticks": cfg.tp_ticks, "product": sch.PRODUCT_KEY, "intento": 2, "dry_run": False}
    assert ms.build_payload("MES", dt.date(2026, 10, 26), 1, 40, 2) == exp


@pytest.mark.parametrize("now,frag", [
    (at(2026, 10, 25, 9, 40), "no es dia habil"),                  # domingo
    (at(2026, 11, 26, 9, 40), "no es dia habil"),                  # Thanksgiving
    (at(2026, 10, 26, 9, 30), "antes de la compuerta"),
    (at(2026, 10, 26, 10, 0), "hora limite de entrada"),
    (at(2026, 10, 26, 14, 30), "flatten"),
])
def test_rechazos_por_dia_u_hora(gist, now, frag, capsys):
    g = gist(); rc, notes = run(["--write", "--confirm", "X"], now=now)
    assert rc == 2 and frag in capsys.readouterr().out and g.patches == []


def test_rechazo_lado_y_fecha_y_nc(gist, capsys):
    g = gist()
    assert run(["--side", "SHORT"])[0] == 2 and "no es el de la estrategia hoy" in capsys.readouterr().out
    assert run(["--date", "2026-10-27"])[0] == 2 and "no es hoy en CT" in capsys.readouterr().out
    assert run(["--nc", "41"])[0] == 2 and "fuera de 1..40" in capsys.readouterr().out
    assert run(["--nc", "0"])[0] == 2
    assert run(["--nc", "6", "--nc-max", "5"])[0] == 2
    assert run(["--nc", "6", "--nc-max", "6", "--side", "LONG", "--date", "2026-10-26"])[0] == 0
    assert g.patches == []


def test_tope_por_variable_de_entorno(gist, monkeypatch, capsys):
    gist(); monkeypatch.setenv("GLITCH_PI_NC_MAX", "6")
    assert run([])[0] == 2 and "fuera de 1..6" in capsys.readouterr().out


def test_rechazo_orden_pendiente_posicion_abierta_y_ciclo_de_hoy(gist, capsys):
    g = gist({"orden_pendiente_mes.json": {"date": "2026-10-19"}}); assert run(["--write", "--confirm", "LUNES-LONG-40"])[0] == 2 and g.patches == []
    assert "orden pendiente" in capsys.readouterr().out
    g = gist({"pi_position_mes.json": {"phase": "bracket_open"}}); assert run([])[0] == 2 and "posicion registrada" in capsys.readouterr().out
    g = gist({"geometry_mes_log.json": HISTORY + [{"date": "2026-10-26", "result": "TP", "pnl": 1, "intento": 2}]}); assert run([])[0] == 2
    assert "ya tiene un ciclo" in capsys.readouterr().out


def test_gist_con_401_aborta_sin_asumir_intento_1(gist, capsys):
    g = gist(mode="401"); rc, notes = run(["--write", "--confirm", "LUNES-LONG-40"])
    out = capsys.readouterr().out
    assert rc == 2 and "ABORTADO" in out and '"intento": 1' not in out and g.patches == []


def test_escritura_rechazada_o_perdida_da_error_y_avisa(gist):
    g = gist(mode="write401"); rc, notes = run(["--write", "--confirm", "LUNES-LONG-40"])
    assert rc == 4 and "STATUS: ERROR" in notes[0]
    g = gist(mode="write_lost"); rc, notes = run(["--write", "--confirm", "LUNES-LONG-40"])
    assert rc == 4 and "NO quedo escrita" in notes[0]


def test_paridad_con_el_scheduler():
    import scheduler.geometry_scheduler as sch
    logs = [[], HISTORY, HISTORY[:1], [{"date": "x", "result": "SL", "pnl": -2000, "intento": 1}],
            [{"date": "a", "result": "TP", "pnl": 3000.5, "intento": 3}],
            [{"date": "a", "result": "TP", "pnl": 1500, "intento": 1}, {"date": "b", "result": "SL", "pnl": -3600, "intento": 1}]]
    for lg in logs:
        assert ms.current_intento(lg) == sch._current_intento(lg)
    for d in (dt.date(2026, 11, 26), dt.date(2026, 12, 25), dt.date(2026, 10, 26), dt.date(2026, 10, 24)):
        class FD(dt.datetime):
            @classmethod
            def now(cls, tz=None): return dt.datetime(d.year, d.month, d.day, 10, tzinfo=tz)
        sch_now, sch.ct_now = sch.ct_now, (lambda d=d: dt.datetime(d.year, d.month, d.day, 10, tzinfo=CT))
        try:
            assert ms.is_trading_day(d) == sch.is_trading_day()
        finally:
            sch.ct_now = sch_now
    assert ms.ENTRY_GATE_MINUTES == sch.ENTRY_GATE_MINUTES and ms.SESSION_FLATTEN_MINUTES == sch.SESSION_FLATTEN_MINUTES
    assert ms.PROFIT_TARGET == sch.PROFIT_TARGET and ms.MLL_THRESHOLD == sch.MLL_THRESHOLD


def test_no_importa_scheduler_ni_telegram_bot_y_se_importa_sin_variables_de_entorno():
    import ast, subprocess
    tree = ast.parse(open(ms.__file__).read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and (m.startswith("scheduler") or "telegram_bot" in m) for m in mods)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, "-c", "import pi.manual_signal as m; print('importado')"], cwd=root, capture_output=True, text=True,
                       env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": root})
    assert r.returncode == 0 and "importado" in r.stdout, r.stderr
