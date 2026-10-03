"""
GLITCH -- Watchdog minimo del Pi Executor (03-oct-2026)
=========================================================
Corre desde cron cada 5 min EN EL PI. Revisa UNA cosa: que pi_executor.log haya
recibido una linea nueva en los ultimos N minutos. Si no, manda un Telegram.

Por que basta con eso: pi_executor escribe una linea en CADA ciclo (cada POLL_SECONDS=120 s,
"Sin señal pendiente -- nada que hacer." cuando esta ocioso) y, con una posicion abierta,
un heartbeat cada ~5 min (ver pi/pi_executor.py::poll_position_until_closed). Un log que
deja de crecer = proceso muerto, colgado, Pi sin red, o servicio detenido.

Diseño deliberado:
  * SOLO stdlib (urllib): sigue funcionando aunque el venv del executor este roto.
  * Una alerta por caida (no una cada 5 min); re-aviso cada REALERT_HOURS si sigue caido; un aviso
    de RECUPERADO al volver. Solo marca "avisado" si el Telegram SE ENVIO (si la red esta caida,
    reintenta en la proxima corrida).
  * Periodo de gracia tras un reinicio del Pi (uptime < GRACE_MIN): no alerta, el servicio todavia
    esta arrancando / esperando red.
  * Credenciales: lee TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID del MISMO archivo de entorno que usa
    systemd (~/.glitch_pi.env), sin imprimirlos jamas; la ultima linea del log que se reenvia por
    Telegram pasa por _sanitize() (un error de `requests` puede incluir la URL con el token del bot).

Uso (cron, instalado por install_watchdog.sh):
    python3 watchdog.py --log-file ~/glitch-logs/pi_executor.log --env-file ~/.glitch_pi.env
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from typing import Optional

PREFIX = "S10GLITCH - PI WATCHDOG"
DEFAULT_MAX_AGE_MIN = 10     # 5x el ciclo ocioso (120 s) -- holgura para jitter de cron/red, muy por debajo de "horas"
DEFAULT_GRACE_MIN = 5
DEFAULT_REALERT_HOURS = 6

_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


def _sanitize(line: str, max_len: int = 200) -> str:
    """Quita el token del bot de Telegram si aparece (p. ej. dentro de una URL de error de requests) y acota el largo."""
    return _TOKEN_RE.sub("bot***", line).strip()[:max_len]


def evaluate(now_ts: float, log_mtime: Optional[float], uptime_s: Optional[float], prev_state: dict,
             max_age_min: float = DEFAULT_MAX_AGE_MIN, grace_min: float = DEFAULT_GRACE_MIN,
             realert_hours: float = DEFAULT_REALERT_HOURS) -> tuple[str, str, dict]:
    """
    Funcion PURA (sin I/O) -- toda la decision del watchdog.

    Devuelve (status, action, new_state):
      status: "ok" | "stale" | "missing" | "grace"
      action: "none" | "alert" | "recovered"
      new_state: lo que se debe persistir SI Y SOLO SI la accion (alert/recovered) se envio con exito;
                 para "none" es igual a prev_state.
    """
    max_age_s = max_age_min * 60
    if uptime_s is not None and uptime_s < grace_min * 60:
        return "grace", "none", prev_state

    if log_mtime is None:
        status = "missing"
    else:
        status = "ok" if (now_ts - log_mtime) <= max_age_s else "stale"

    was_alerted = bool(prev_state.get("alerted"))

    if status == "ok":
        if was_alerted:
            return status, "recovered", {"alerted": False}
        return status, "none", prev_state

    # stale / missing
    if not was_alerted:
        return status, "alert", {"alerted": True, "last_alert_ts": now_ts}
    if (now_ts - float(prev_state.get("last_alert_ts", 0))) >= realert_hours * 3600:
        return status, "alert", {"alerted": True, "last_alert_ts": now_ts}
    return status, "none", prev_state


def parse_env_file(path: str) -> dict:
    """KEY=VALUE por linea (formato EnvironmentFile de systemd). Ignora comentarios y vacias; tolera 'export ' y comillas."""
    out: dict = {}
    try:
        with open(path) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                k, v = line.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                out[k.strip()] = v
    except OSError:
        pass
    return out


def read_uptime_s() -> Optional[float]:
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except Exception:
        return None


def last_log_line(path: str) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", "replace").strip().splitlines()
        return _sanitize(tail[-1]) if tail else "(log vacio)"
    except OSError:
        return "(log no existe)"


def service_state(service: Optional[str]) -> str:
    if not service:
        return "n/a"
    try:
        r = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=5)
        return (r.stdout.strip() or r.stderr.strip() or "desconocido")
    except Exception:
        return "desconocido"


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"watchdog: no se pudo enviar a Telegram: {_sanitize(str(e))}", file=sys.stderr)
        return False


def load_state(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(path: str, state: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Watchdog minimo de pi_executor.log")
    ap.add_argument("--log-file", default=os.path.expanduser("~/glitch-logs/pi_executor.log"))
    ap.add_argument("--env-file", default=os.path.expanduser("~/.glitch_pi.env"))
    ap.add_argument("--state-file", default=os.path.expanduser("~/.glitch_watchdog_state.json"))
    ap.add_argument("--service", default="glitch-pi-executor", help="nombre de la unidad systemd (solo informativo en el mensaje)")
    ap.add_argument("--max-age-min", type=float, default=DEFAULT_MAX_AGE_MIN)
    ap.add_argument("--grace-min", type=float, default=DEFAULT_GRACE_MIN)
    ap.add_argument("--realert-hours", type=float, default=DEFAULT_REALERT_HOURS)
    ap.add_argument("--dry-run", action="store_true", help="evalua e imprime, sin enviar Telegram ni guardar estado")
    args = ap.parse_args(argv)

    now = dt.datetime.now(dt.timezone.utc).timestamp()
    try:
        mtime: Optional[float] = os.path.getmtime(args.log_file)
    except OSError:
        mtime = None
    uptime = read_uptime_s()
    prev = load_state(args.state_file)

    status, action, new_state = evaluate(now, mtime, uptime, prev, args.max_age_min, args.grace_min, args.realert_hours)
    age_min = None if mtime is None else (now - mtime) / 60
    print(f"watchdog: status={status} action={action} log_age_min={'n/a' if age_min is None else f'{age_min:.1f}'} "
          f"uptime_min={'n/a' if uptime is None else f'{uptime/60:.0f}'}")
    if action == "none" or args.dry_run:
        return 0

    env = parse_env_file(args.env_file)
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("watchdog: faltan TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID en el archivo de entorno -- no se puede alertar", file=sys.stderr)
        return 2

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if action == "alert":
        what = ("pi_executor.log NO EXISTE" if status == "missing"
                else f"pi_executor.log sin lineas nuevas hace {age_min:.0f} min (umbral {args.max_age_min:.0f} min)")
        text = (f"{PREFIX}\nSTATUS: ALERTA\n{what}\n"
                f"Servicio {args.service}: {service_state(args.service)}  |  Uptime del Pi: "
                f"{'n/a' if uptime is None else f'{uptime/60:.0f} min'}\n"
                f"Ultima linea: {last_log_line(args.log_file)}\n{stamp}")
    else:  # recovered
        text = (f"{PREFIX}\nSTATUS: RECUPERADO\npi_executor.log vuelve a recibir lineas.\n"
                f"Servicio {args.service}: {service_state(args.service)}\n{stamp}")

    if send_telegram(token, chat, text):
        save_state(args.state_file, new_state)   # solo se marca "avisado" si el envio funciono
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
