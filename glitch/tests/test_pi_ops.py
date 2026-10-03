"""
GLITCH -- Tests de las piezas operativas del Pi (03-oct-2026):
  pi/ops/watchdog.py            -- decision pura del watchdog + parseo del env file + saneo de tokens
  pi/verify_orderside_demo.py   -- inferencia pura del mapeo compra/venta, contrato, formato del JSON
  pi/ops/*.sh + .template       -- chequeos estaticos (la unidad systemd y los scripts no se ejecutan aqui:
                                   necesitan systemd/sudo del Pi real)

Sin red en ningun test. El contrato clave que se prueba de punta a punta: lo que escribe
verify_orderside_demo.py es EXACTAMENTE lo que pi_executor._load_verified_side_map() acepta.
"""
import json
import os
import re
import sys

os.environ.setdefault("TOPSTEP_USERNAME", "test-user-not-real")
os.environ.setdefault("TOPSTEP_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
os.environ.setdefault("GLITCH_PRODUCT", "MES")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pi", "ops"))

import datetime as dt

import pytest

import pi.pi_executor as pi_executor
import pi.verify_orderside_demo as verify
import watchdog

NOW = 1_800_000_000.0   # un instante cualquiera (epoch)


class TestWatchdogEvaluate:
    def test_fresh_log_is_ok_and_silent(self):
        status, action, _ = watchdog.evaluate(NOW, NOW - 60, 7200, {})
        assert (status, action) == ("ok", "none")

    def test_stale_log_alerts_once(self):
        status, action, state = watchdog.evaluate(NOW, NOW - 25 * 60, 7200, {})
        assert (status, action) == ("stale", "alert")
        assert state["alerted"] is True

    def test_log_exactly_at_threshold_is_still_ok(self):
        status, action, _ = watchdog.evaluate(NOW, NOW - 10 * 60, 7200, {}, max_age_min=10)
        assert (status, action) == ("ok", "none")

    def test_no_repeat_alert_while_still_down(self):
        _, _, state = watchdog.evaluate(NOW, NOW - 25 * 60, 7200, {})
        status, action, _ = watchdog.evaluate(NOW + 300, NOW - 25 * 60, 7200, state)
        assert (status, action) == ("stale", "none")

    def test_realerts_after_realert_window_if_still_down(self):
        _, _, state = watchdog.evaluate(NOW, NOW - 25 * 60, 7200, {})
        status, action, _ = watchdog.evaluate(NOW + 6 * 3600 + 1, NOW - 99999, 7200, state, realert_hours=6)
        assert (status, action) == ("stale", "alert")

    def test_recovery_message_once_then_quiet(self):
        _, _, state = watchdog.evaluate(NOW, NOW - 25 * 60, 7200, {})
        status, action, new_state = watchdog.evaluate(NOW + 600, NOW + 590, 7200, state)
        assert (status, action) == ("ok", "recovered")
        assert new_state == {"alerted": False}
        status2, action2, _ = watchdog.evaluate(NOW + 700, NOW + 690, 7200, new_state)
        assert (status2, action2) == ("ok", "none")

    def test_missing_log_alerts(self):
        status, action, _ = watchdog.evaluate(NOW, None, 7200, {})
        assert (status, action) == ("missing", "alert")

    def test_grace_period_after_reboot_suppresses_alert(self):
        """Pi recien reiniciado (uptime 2 min < gracia de 5): el servicio todavia esta arrancando/esperando red."""
        status, action, _ = watchdog.evaluate(NOW, NOW - 3 * 3600, 120, {})
        assert (status, action) == ("grace", "none")

    def test_unknown_uptime_does_not_trigger_grace(self):
        status, action, _ = watchdog.evaluate(NOW, NOW - 3 * 3600, None, {})
        assert (status, action) == ("stale", "alert")

    def test_default_threshold_is_well_above_the_idle_cycle(self):
        """pi_executor loguea cada POLL_SECONDS (120 s) ocioso: el umbral debe dejar holgura de sobra."""
        assert watchdog.DEFAULT_MAX_AGE_MIN * 60 >= 4 * pi_executor.POLL_SECONDS

    def test_default_threshold_covers_the_open_bracket_heartbeat(self):
        """Con un bracket abierto el log solo crece por el heartbeat (cada HEARTBEAT_EVERY_POLLS x 30 s)."""
        heartbeat_s = pi_executor.HEARTBEAT_EVERY_POLLS * pi_executor.POSITION_POLL_INTERVAL
        assert watchdog.DEFAULT_MAX_AGE_MIN * 60 > heartbeat_s


class TestWatchdogHelpers:
    def test_sanitize_masks_telegram_bot_token(self):
        line = "ConnectionError: https://api.telegram.org/bot123456789:AAE-secret_Token_xyz/sendMessage failed"
        out = watchdog._sanitize(line)
        assert "AAE-secret_Token_xyz" not in out
        assert "bot***" in out

    def test_sanitize_truncates(self):
        assert len(watchdog._sanitize("x" * 1000)) == 200

    def test_parse_env_file(self, tmp_path):
        f = tmp_path / "e.env"
        f.write_text("# comentario\n\nTELEGRAM_BOT_TOKEN=abc123\nexport TELEGRAM_CHAT_ID='999'\nVACIA=\nGIST_ID=\"g\"\n")
        env = watchdog.parse_env_file(str(f))
        assert env["TELEGRAM_BOT_TOKEN"] == "abc123"
        assert env["TELEGRAM_CHAT_ID"] == "999"
        assert env["GIST_ID"] == "g"
        assert env["VACIA"] == ""

    def test_parse_env_file_missing_returns_empty(self):
        assert watchdog.parse_env_file("/no/existe.env") == {}

    def test_state_only_saved_when_telegram_send_succeeds(self, tmp_path, monkeypatch):
        """Si el envio falla (red caida) NO se marca 'avisado': la proxima corrida reintenta."""
        import time
        log = tmp_path / "pi_executor.log"
        log.write_text("linea vieja\n")
        old_ts = time.time() - 3600           # reloj real: el log tiene 1 h de antiguedad
        os.utime(log, (old_ts, old_ts))
        env = tmp_path / "e.env"
        env.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
        state = tmp_path / "state.json"
        monkeypatch.setattr(watchdog, "read_uptime_s", lambda: 9999.0)
        monkeypatch.setattr(watchdog, "service_state", lambda s: "inactive")
        argv = ["--log-file", str(log), "--env-file", str(env), "--state-file", str(state)]

        monkeypatch.setattr(watchdog, "send_telegram", lambda *a: False)
        assert watchdog.main(argv) == 1
        assert not state.exists()

        monkeypatch.setattr(watchdog, "send_telegram", lambda *a: True)
        assert watchdog.main(argv) == 0
        assert json.loads(state.read_text())["alerted"] is True


class TestVerifierInference:
    def test_side0_long_means_zero_is_buy(self):
        """La documentacion oficial: 0=Bid=Buy."""
        assert verify.infer_side_map(0, +1) == {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1}

    def test_side0_short_means_zero_is_sell(self):
        """El comentario de brokers/projectx.py::OrderSide (BID=0 # Sell)."""
        assert verify.infer_side_map(0, -1) == {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0}

    def test_undetermined_direction_yields_no_map(self):
        assert verify.infer_side_map(0, None) is None
        assert verify.infer_side_map(0, 0) is None

    def test_invalid_test_side_yields_no_map(self):
        assert verify.infer_side_map(2, +1) is None

    def test_buy_and_sell_are_always_the_two_distinct_sides(self):
        for d in (+1, -1):
            m = verify.infer_side_map(0, d)
            assert {m["BUY_SIDE_INT"], m["SELL_SIDE_INT"]} == {0, 1}


class TestPositionDirection:
    def test_netpos_positive_is_long(self):
        assert verify.position_direction({"netPos": 1}) == 1

    def test_netpos_negative_is_short(self):
        assert verify.position_direction({"netPos": -2}) == -1

    def test_type_and_size_form_documented_by_projectx(self):
        assert verify.position_direction({"type": 1, "size": 1}) == 1
        assert verify.position_direction({"type": 2, "size": 3}) == -1

    def test_netpos_takes_precedence(self):
        assert verify.position_direction({"netPos": -1, "type": 1, "size": 1}) == -1

    def test_unknown_shape_is_none_never_guessed(self):
        assert verify.position_direction({}) is None
        assert verify.position_direction({"netPos": 0}) is None
        assert verify.position_direction({"type": 3, "size": 1}) is None
        assert verify.position_direction({"type": 1, "size": 0}) is None
        assert verify.position_direction({"netPos": True}) is None


class TestPickFrontMonth:
    NOW = dt.datetime(2026, 10, 3, tzinfo=dt.timezone.utc)

    def test_picks_nearest_unexpired(self):
        cs = [{"name": "MESZ6", "id": "z", "expirationDate": "2026-12-18T00:00:00Z"},
              {"name": "MESU6", "id": "u", "expirationDate": "2026-09-18T00:00:00Z"},   # vencido
              {"name": "MESH7", "id": "h", "expirationDate": "2027-03-19T00:00:00Z"},
              {"name": "MNQZ6", "id": "n", "expirationDate": "2026-10-20T00:00:00Z"}]   # otro producto
        assert verify.pick_front_month(cs, "MES", now=self.NOW)["id"] == "z"

    def test_none_when_nothing_matches(self):
        assert verify.pick_front_month([{"name": "MNQZ6"}], "MES", now=self.NOW) is None


class TestAsList:
    def test_valid_empty_is_empty_list(self):
        assert verify.as_list({"positions": [], "success": True}, "positions", "x") == []

    def test_valid_list_passthrough(self):
        assert verify.as_list({"positions": [{"a": 1}], "success": True}, "positions", "x") == [{"a": 1}]
        assert verify.as_list([{"a": 1}], "positions", "x") == [{"a": 1}]

    def test_malformed_responses_raise_instead_of_looking_flat(self):
        """Un endpoint roto NO puede hacer que la cuenta parezca plana."""
        for bad in ({"_non_json": "<html>", "_status": 404}, {"success": False, "errorMessage": "x"}, {"otra": []}):
            with pytest.raises(RuntimeError):
                verify.as_list(bad, "positions", "Position/searchOpen")


class TestVerifiedFileContract:
    def test_written_file_has_exactly_the_two_keys(self, tmp_path):
        p = tmp_path / "orderside_verified.json"
        verify.write_verified_map_atomic(str(p), {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1, "extra": "no debe pasar"})
        assert json.loads(p.read_text()) == {"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1}
        assert not (tmp_path / "orderside_verified.json.tmp").exists()

    def test_written_file_is_accepted_by_pi_executor_loader(self, tmp_path, monkeypatch):
        """El contrato de punta a punta: el verificador escribe lo que pi_executor lee."""
        p = tmp_path / "orderside_verified.json"
        verify.write_verified_map_atomic(str(p), {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0})
        monkeypatch.setattr(pi_executor, "ORDERSIDE_VERIFIED_PATH", str(p))
        loaded = pi_executor._load_verified_side_map()
        assert loaded == {"BUY_SIDE_INT": 1, "SELL_SIDE_INT": 0}
        assert pi_executor._resolve_side(+1, loaded) == 1
        assert pi_executor._resolve_side(-1, loaded) == 0

    def test_verifier_and_executor_agree_on_the_path(self):
        assert os.path.abspath(verify.VERIFIED_PATH) == os.path.abspath(pi_executor.ORDERSIDE_VERIFIED_PATH)


class TestVerifierGates:
    """El script se niega a tocar la red sin el gate y sin credenciales -- sin llamadas a la API."""

    def _boom(self, *a, **k):
        raise AssertionError("no debia tocar la red")

    def test_blocked_without_phase3(self, monkeypatch, capsys):
        monkeypatch.delenv("GLITCH_PI_PHASE3", raising=False)
        monkeypatch.setattr(verify, "Api", self._boom)
        assert verify.main(["--account-id", "28197753", "--dry-run"]) == 1
        assert "GLITCH_PI_PHASE3" in capsys.readouterr().out

    def test_blocked_without_credentials(self, monkeypatch, capsys):
        monkeypatch.setenv("GLITCH_PI_PHASE3", "si")
        monkeypatch.delenv("TOPSTEP_USERNAME", raising=False)
        monkeypatch.setattr(verify, "Api", self._boom)
        assert verify.main(["--account-id", "28197753", "--dry-run"]) == 1

    def test_refuses_to_overwrite_existing_verified_file_without_force(self, monkeypatch, tmp_path, capsys):
        existing = tmp_path / "orderside_verified.json"
        existing.write_text("{}")
        monkeypatch.setattr(verify, "VERIFIED_PATH", str(existing))
        monkeypatch.setenv("GLITCH_PI_PHASE3", "si")
        monkeypatch.setenv("TOPSTEP_USERNAME", "u")
        monkeypatch.setenv("TOPSTEP_API_KEY", "k")
        monkeypatch.setattr(verify, "Api", self._boom)
        assert verify.main(["--account-id", "28197753"]) == 1
        assert "--force" in capsys.readouterr().out

    def test_account_id_is_required(self):
        with pytest.raises(SystemExit):
            verify.main([])


class TestOpsFilesStatic:
    """La unidad systemd y los scripts no corren aqui (necesitan el Pi), pero sus invariantes de seguridad si se pueden fijar."""

    def _read(self, rel):
        with open(os.path.join(ROOT, "pi", "ops", rel)) as f:
            return f.read()

    def test_unit_template_restarts_always_but_caps_crash_loops(self):
        t = self._read("glitch-pi-executor.service.template")
        assert re.search(r"^Restart=always$", t, re.M)
        assert re.search(r"^StartLimitBurst=\d+$", t, re.M)      # require_env manda 1 Telegram por arranque fallido
        assert int(re.search(r"^RestartSec=(\d+)$", t, re.M).group(1)) >= 30

    def test_unit_template_keeps_secrets_out_of_the_unit(self):
        t = self._read("glitch-pi-executor.service.template")
        assert "EnvironmentFile=@ENV_FILE@" in t
        assert not re.search(r"^Environment=.*(TOKEN|KEY|PASSWORD|SECRET)", t, re.M | re.I)

    def test_unit_template_has_every_placeholder_the_installer_fills(self):
        t = self._read("glitch-pi-executor.service.template")
        inst = self._read("install_service.sh")
        for ph in set(re.findall(r"@[A-Z_]+@", t)):
            assert f"s|{ph}|" in inst, f"install_service.sh no reemplaza {ph}"

    def test_installer_never_opens_the_phase3_gate_and_never_kills_processes(self):
        inst = self._read("install_service.sh")
        for line in inst.splitlines():
            code = line.strip()
            if code.startswith("#") or code.startswith('echo "#'):
                continue   # comentarios y la linea que escribe el comentario de la plantilla de entorno
            assert "GLITCH_PI_PHASE3=si" not in code, f"el instalador no debe abrir el gate de Fase 3: {line}"
        assert not re.search(r"\b(pkill|killall)\b|^\s*kill\s", inst, re.M)

    def test_env_template_comments_out_the_phase3_gate(self):
        inst = self._read("install_service.sh")
        assert 'echo "# GLITCH_PI_PHASE3=si"' in inst

    def test_diagnose_script_is_read_only(self):
        d = self._read("diagnose_reboot.sh")
        for forbidden in (r"\bsystemctl\s+(restart|stop|disable|enable|mask)\b", r"\bapt(-get)?\s+(install|remove|purge|upgrade)\b",
                          r"\brm\s+-rf?\s+/(?!tmp)", r"\breboot\b\s*$", r"\bsed\s+-i\b"):
            for line in d.splitlines():
                if line.lstrip().startswith("#") or "echo" in line:
                    continue
                assert not re.search(forbidden, line), f"diagnose_reboot.sh no deberia ejecutar: {line}"
