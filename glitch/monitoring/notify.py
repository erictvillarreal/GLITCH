"""Envio a Telegram con stdlib (mismo patron que pi/ops/watchdog.py: sigue funcionando sin el venv, nunca imprime el token)."""
from __future__ import annotations
import json
import re
import sys
import urllib.request

_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")
PREFIX = "S10GLITCH - MONITOR"


def sanitize(text: str, max_len: int = 3500) -> str:
    return _TOKEN_RE.sub("bot***", text)[:max_len]


def parse_env_file(path: str) -> dict:
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


def send(token: str, chat_id: str, text: str, timeout: int = 15) -> bool:
    """True solo si Telegram respondio 2xx. Texto plano (sin parse_mode: evita errores de formato con '_' o '<')."""
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps({"chat_id": chat_id, "text": sanitize(text)}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"monitor: no se pudo enviar a Telegram: {sanitize(str(e), 200)}", file=sys.stderr)
        return False
