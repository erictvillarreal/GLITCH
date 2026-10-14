"""T4 (12-oct-2026) -- Pi: seleccion del contrato activo, geometria MGC unica, contrato de la señal de Cerebro 2 y segunda instancia del servicio. Sin red."""
import os
import stat
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for k, v in (("TOPSTEP_USERNAME", "u"), ("TOPSTEP_API_KEY", "k"), ("TOPSTEP_ACCOUNT_ID", "555"), ("TELEGRAM_BOT_TOKEN", "t"), ("TELEGRAM_CHAT_ID", "c"),
             ("GITHUB_GIST_TOKEN", "g"), ("GIST_ID", "i"), ("GLITCH_PRODUCT", "MES")):
    os.environ.setdefault(k, v)
sys.path.insert(0, ROOT)

import strategies.geometry_pure as geo          # noqa: E402
import pi.pi_executor as pe                      # noqa: E402


class TestGeometry:
    def test_mgc_is_the_50k_xfa_geometry_and_never_above_cap(self):
        c = geo.CANDIDATES["MGC"]
        assert (c.sl_ticks, c.tp_ticks, c.nc) == (364, 364, 3)
        for k in ("MGC", "MGC_XFA_100K", "MGC_XFA_150K"):
            assert geo.CANDIDATES[k].nc <= geo.CANDIDATES[k].spec.nc_cap == 30
        assert geo.CANDIDATES["MGC_XFA_150K"].nc == 6 and geo.CANDIDATES["MGC_XFA_100K"].nc == 4

    def test_mes_untouched(self):
        c = geo.CANDIDATES["MES"]
        assert (c.sl_ticks, c.tp_ticks, c.nc) == (100, 40, 40)


class FakeClient:
    def __init__(self, contracts): self._c = contracts
    def get_contracts(self, live=False): return list(self._c)


GOLD = [{"id": "CON.F.US.MGC.V26", "name": "MGCV6", "expirationDate": "2026-10-28", "activeContract": False, "tickSize": 0.1, "tickValue": 1.0},
        {"id": "CON.F.US.MGC.Z26", "name": "MGCZ6", "expirationDate": "2026-12-29", "activeContract": True, "tickSize": 0.1, "tickValue": 1.0},
        {"id": "CON.F.US.MGC.G27", "name": "MGCG7", "expirationDate": "2027-02-24", "activeContract": False, "tickSize": 0.1, "tickValue": 1.0}]


@pytest.fixture
def mgc_cfg(monkeypatch):
    sent = []
    monkeypatch.setattr(pe, "CFG", geo.CANDIDATES["MGC"])
    monkeypatch.setattr(pe, "send", lambda m: sent.append(m))
    pe._SPEC_WARNED.clear()
    return sent


class TestResolveContract:
    def test_prefers_active_over_nearest_expiry(self, mgc_cfg):
        assert pe.resolve_contract_id(FakeClient(GOLD), "MGC")["name"] == "MGCZ6"

    def test_falls_back_to_nearest_with_warning_when_no_flag(self, mgc_cfg, caplog):
        flagless = [{k: v for k, v in c.items() if k != "activeContract"} for c in GOLD]
        with caplog.at_level("WARNING"):
            assert pe.resolve_contract_id(FakeClient(flagless), "MGC")["name"] == "MGCV6"
        assert any("activeContract" in r.message for r in caplog.records)

    def test_nearest_among_several_active(self, mgc_cfg):
        two = [dict(c, activeContract=True) if c["name"] in ("MGCG7", "MGCZ6") else c for c in GOLD]
        assert pe.resolve_contract_id(FakeClient(two), "MGC")["name"] == "MGCZ6"

    def test_no_match_raises(self, mgc_cfg):
        with pytest.raises(RuntimeError):
            pe.resolve_contract_id(FakeClient(GOLD), "MCL")

    def test_mes_behaviour_unchanged(self, monkeypatch):
        sent = []
        monkeypatch.setattr(pe, "CFG", geo.CANDIDATES["MES"]); monkeypatch.setattr(pe, "send", lambda m: sent.append(m)); pe._SPEC_WARNED.clear()
        mes = [{"id": "A", "name": "MESZ6", "expirationDate": "2026-12-18", "activeContract": True, "tickSize": 0.25, "tickValue": 1.25},
               {"id": "B", "name": "MESH7", "expirationDate": "2027-03-19", "activeContract": False, "tickSize": 0.25, "tickValue": 1.25}]
        assert pe.resolve_contract_id(FakeClient(mes), "MES")["name"] == "MESZ6" and sent == []

    def test_spec_mismatch_alerts_once_and_never_raises(self, mgc_cfg):
        bad = [dict(c, tickSize=0.01) for c in GOLD]
        pe.resolve_contract_id(FakeClient(bad), "MGC"); pe.resolve_contract_id(FakeClient(bad), "MGC")
        assert len(mgc_cfg) == 1 and "tickSize" in mgc_cfg[0]
        weird = [dict(c, tickSize="no-numero") for c in GOLD]
        pe._SPEC_WARNED.clear()
        assert pe.resolve_contract_id(FakeClient(weird), "MGC")["name"] == "MGCZ6"      # un valor raro no rompe el ciclo

    def test_matching_spec_is_silent(self, mgc_cfg):
        pe.resolve_contract_id(FakeClient(GOLD), "MGC")
        assert mgc_cfg == []


def _run_pi_product(product: str, code: str) -> str:
    env = dict(os.environ, GLITCH_PRODUCT=product, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout.strip().splitlines()[-1]


class TestMgcSignalContract:
    """El Pi arrancado con GLITCH_PRODUCT=MGC (proceso aparte: las constantes de producto se fijan al importar)."""

    def test_file_names_and_prefix_match_the_mgc_scheduler(self):
        out = _run_pi_product("MGC", "import pi.pi_executor as p; print(p.ORDER_FILE, p.LOG_FILE, p.PI_STATE_FILE, p.PREFIX)")
        assert out == "orden_pendiente_mgc.json geometry_mgc_log.json pi_position_mgc.json S10GLITCH - PI EXECUTOR - MGC"

    def test_valid_signal_from_the_scheduler_is_accepted(self):
        out = _run_pi_product("MGC", """
            import pi.pi_executor as p
            sig = {"date": "2026-10-30", "side": 1, "direction": "LONG", "ticker": None, "product_code": "MGC", "nc": 3, "sl_ticks": 364, "tp_ticks": 364,
                   "product": "MGC", "intento": 1, "dry_run": False}
            print(p._validate_signal(sig), p._is_test_signal(sig))""")
        assert out == "None False"

    def test_product_mismatch_downgrades_to_test_signal_and_caps_contracts(self):
        """Si el scheduler escribiera product='MGC_XFA_150K' el Pi la trataria como ENSAYO (<= 2 contratos, sin marcador): el contrato EXIGE product == GLITCH_PRODUCT."""
        out = _run_pi_product("MGC", """
            import pi.pi_executor as p
            sig = {"date": "2026-10-30", "side": 1, "direction": "LONG", "product_code": "MGC", "nc": 3, "sl_ticks": 364, "tp_ticks": 364, "product": "MGC_XFA_150K"}
            print(p._is_test_signal(sig), 'nc invalido' in (p._validate_signal(sig) or ''))""")
        assert out == "True True"

    def test_oversized_or_wrong_signals_rejected(self):
        out = _run_pi_product("MGC", """
            import pi.pi_executor as p
            base = {"side": 1, "direction": "LONG", "product_code": "MGC", "nc": 3, "sl_ticks": 364, "tp_ticks": 364, "product": "MGC"}
            r = [p._validate_signal(dict(base, nc=4)) is not None, p._validate_signal(dict(base, tp_ticks=364 * 4 + 1)) is not None,
                 p._validate_signal(dict(base, product_code="MES")) is not None, p._validate_signal(dict(base, tp_ticks=728, sl_ticks=728)) is None]
            print(r)""")
        assert out == "[True, True, True, True]"      # el bracket de 728 (propuesta) cabe dentro de 4x lo configurado


# ── segunda instancia del servicio ───────────────────────────────────────────────────────────
OPS = os.path.join(ROOT, "pi", "ops")


def _read(name): return open(os.path.join(OPS, name)).read()


class TestSecondInstance:
    def test_scripts_parse(self):
        for f in ("install_service.sh", "install_watchdog.sh", "install_monitoring.sh") if os.path.exists(os.path.join(OPS, "install_monitoring.sh")) else ("install_service.sh", "install_watchdog.sh"):
            assert subprocess.run(["bash", "-n", os.path.join(OPS, f)]).returncode == 0

    def test_template_has_state_dir_placeholder_and_installer_fills_it(self):
        assert "GLITCH_PI_STATE_DIR=@STATE_DIR@" in _read("glitch-pi-executor.service.template")
        assert "s|@STATE_DIR@|" in _read("install_service.sh")

    def test_watchdog_marks_do_not_collide(self):
        s = _read("install_watchdog.sh")
        default_mark = "# glitch-pi-watchdog"
        inst_mark = "# glitch-pi-instance-watchdog-"
        assert default_mark not in inst_mark and inst_mark in s

    def _fake_env(self, tmp_path):
        home = tmp_path / "home"; home.mkdir()
        venv = tmp_path / "venv" / "bin"; venv.mkdir(parents=True)
        (venv / "python").write_text("#!/bin/sh\nexit 0\n"); (venv / "python").chmod(0o755)
        bin_ = tmp_path / "bin"; bin_.mkdir()
        out = tmp_path / "installed"; out.mkdir()
        (bin_ / "sudo").write_text(f'#!/bin/sh\nif [ "$1" = "install" ]; then cp "$4" "{out}/$(basename "$5")"; fi\nexit 0\n')
        (bin_ / "systemctl").write_text('#!/bin/sh\necho 0\nexit 0\n')
        for f in ("sudo", "systemctl"): (bin_ / f).chmod(0o755)
        def envfile(path, product, acct):
            path.write_text("\n".join(f"{k}={v}" for k, v in (("TOPSTEP_USERNAME", "u"), ("TOPSTEP_API_KEY", "k"), ("TOPSTEP_ACCOUNT_ID", acct), ("TELEGRAM_BOT_TOKEN", "t"),
                                                                  ("TELEGRAM_CHAT_ID", "c"), ("GITHUB_GIST_TOKEN", "g"), ("GIST_ID", "i"), ("GLITCH_PRODUCT", product))) + "\n")
        return home, venv.parent, bin_, out, envfile

    def _run(self, home, venv, bin_, args):
        env = dict(os.environ, HOME=str(home), PI_VENV=str(venv), PATH=f"{bin_}:{os.environ['PATH']}")
        return subprocess.run(["bash", os.path.join(OPS, "install_service.sh")] + args, env=env, capture_output=True, text=True, timeout=60)

    def test_default_and_second_instance_render_separate_units(self, tmp_path):
        home, venv, bin_, out, envfile = self._fake_env(tmp_path)
        envfile(home / ".glitch_pi.env", "MES", "28197705"); envfile(home / ".glitch_pi_mgc.env", "MGC", "28514663")
        r1 = self._run(home, venv, bin_, []); assert r1.returncode == 0, r1.stderr
        r2 = self._run(home, venv, bin_, ["--instance", "mgc"]); assert r2.returncode == 0, r2.stderr
        u1 = (out / "glitch-pi-executor.service").read_text(); u2 = (out / "glitch-pi-executor-mgc.service").read_text()
        assert f"GLITCH_PI_STATE_DIR={home}\n" in u1 and f"EnvironmentFile={home}/.glitch_pi.env" in u1 and "pi_executor.log" in u1
        assert f"GLITCH_PI_STATE_DIR={home}/.glitch_pi_state_mgc" in u2 and f"EnvironmentFile={home}/.glitch_pi_mgc.env" in u2 and "pi_executor_mgc.log" in u2
        assert (home / ".glitch_pi_state_mgc").is_dir()
        assert "@" not in "".join(l for l in u2.splitlines() if not l.startswith("#"))

    def test_refuses_two_instances_with_the_same_product(self, tmp_path):
        home, venv, bin_, out, envfile = self._fake_env(tmp_path)
        envfile(home / ".glitch_pi.env", "MES", "28197705"); envfile(home / ".glitch_pi_dup.env", "MES", "28514663")
        r = self._run(home, venv, bin_, ["--instance", "dup"])
        assert r.returncode != 0 and "mismo producto" in r.stderr
        assert not (out / "glitch-pi-executor-dup.service").exists()

    def test_rejects_bad_instance_names(self, tmp_path):
        home, venv, bin_, out, envfile = self._fake_env(tmp_path)
        assert self._run(home, venv, bin_, ["--instance", "MG C"]).returncode != 0


# ── pi/ops/check_contracts.py (solo lectura) ──────────────────────────────────────────────────
def _load_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_contracts", os.path.join(OPS, "check_contracts.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class TestCheckContracts:
    def test_flags_active_not_nearest(self):
        m = _load_check(); r = m.analyze(GOLD, "MGC", geo.SPECS["MGC"])
        assert r["chosen"] == "MGCZ6" and r["nearest"] == "MGCV6" and any("NO es el de vencimiento mas cercano" in i for i in r["issues"])

    def test_flags_missing_field_and_spec_mismatch(self):
        m = _load_check()
        r = m.analyze([{k: v for k, v in c.items() if k != "activeContract"} for c in GOLD], "MGC", geo.SPECS["MGC"])
        assert any("NO trae el campo activeContract" in i for i in r["issues"])
        r = m.analyze([dict(c, tickSize=0.5) for c in GOLD], "MGC", geo.SPECS["MGC"])
        assert any("tickSize" in i for i in r["issues"])

    def test_main_is_read_only_and_exit_code(self, capsys):
        m = _load_check()
        class C(FakeClient):
            def __getattr__(self, name): raise AssertionError(f"el verificador no debe llamar {name}")
        assert m.main(["--products", "MGC", "--env-file", "/no/existe"], client=C(GOLD)) == 1      # hallazgo: activo != mas cercano
        out = capsys.readouterr().out
        assert "MGCZ6" in out and "activo=True" in out
        ok = [dict(c, activeContract=(c["name"] == "MGCV6")) for c in GOLD]
        assert m.main(["--products", "MGC", "--env-file", "/no/existe"], client=C(ok)) == 0
