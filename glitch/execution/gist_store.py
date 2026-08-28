"""
Glitch — Persistencia de estado via GitHub Gist (27-ago-2026)
================================================================
UNICA fuente de verdad para leer/escribir el log de paper trading de
CUALQUIER scheduler (combo2d, geometry, futuros que se agreguen) --
reemplaza los load_log()/save_log() basados en filesystem local.

POR QUE: confirmado en el dashboard de Railway que los servicios "Cron
Schedule" (combo2d y geometry, ambos) NO tienen seccion de Volumes
disponible -- el filesystem es efimero entre ejecuciones del cron.
Cualquier archivo JSON local (combo2d_log.json, geometry_*_log.json) se
reseteaba a cero en CADA corrida. Esto invalido el conteo de "dia X de
Y" y el "pass_rate acumulado" reportado por Telegram en AMBOS
schedulers desde que arrancaron -- ver GLITCH_RESEARCH_LOG.md, seccion
"Persistencia de estado (hallazgo critico, 27-ago-2026)".

DISEÑO: un Gist privado de GitHub como almacen minimo de estado -- un
archivo JSON por scheduler, todos dentro del mismo gist (un solo
GIST_ID que administrar, no uno por scheduler). Requiere un Personal
Access Token NUEVO Y SEPARADO con scope UNICAMENTE "gist" (nunca
"repo") -- nunca reusar el token de push al repo.

Variables de entorno requeridas (mismo patron fail-loud que
MASSIVE_API_KEY -- sin fallback silencioso si faltan):
    GITHUB_GIST_TOKEN  -- PAT con scope "gist" unicamente
    GIST_ID            -- id del gist privado ya creado

Filosofia de fallos, deliberadamente asimetrica:
  - Falta configuracion (env vars ausentes): RAISE inmediato. Un
    scheduler mal configurado no debe arrancar creyendo en silencio
    que esta en su primer dia de paper -- eso es exactamente el bug
    que este modulo existe para eliminar.
  - Fallo de RED/API en una corrida ya bien configurada (timeout, gist
    borrado, JSON corrupto): se loguea pero NO tumba el scheduler --
    para cuando save_log() se llama, el trade del dia YA se ejecuto y
    YA se notifico por Telegram; perder un dia de contador es mejor
    que perder la notificacion real por un problema de persistencia.
"""
from __future__ import annotations
import json
import logging
import os

import requests

log = logging.getLogger("gist_store")

GITHUB_GIST_TOKEN = os.environ.get("GITHUB_GIST_TOKEN")
GIST_ID = os.environ.get("GIST_ID")

_API = "https://api.github.com"


def _require_config():
    if not GITHUB_GIST_TOKEN or not GIST_ID:
        raise RuntimeError(
            "FATAL: falta GITHUB_GIST_TOKEN o GIST_ID en el entorno. Sin fallback -- "
            "generar un Personal Access Token NUEVO con scope UNICAMENTE 'gist' "
            "(nunca reusar el token de push al repo) y crear un gist privado antes "
            "de arrancar este scheduler."
        )


def _headers():
    return {
        "Authorization": f"Bearer {GITHUB_GIST_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def load_log(filename: str) -> list:
    """
    Lee el archivo `filename` dentro del gist GIST_ID. Devuelve [] si el
    gist/archivo no existe todavia o el contenido esta vacio -- mismo
    comportamiento que el load_log() de filesystem que reemplaza
    (primera corrida = lista vacia, nunca una excepcion por ESO).
    """
    _require_config()
    try:
        r = requests.get(f"{_API}/gists/{GIST_ID}", headers=_headers(), timeout=15)
        r.raise_for_status()
        gist = r.json()
        file_obj = gist.get("files", {}).get(filename)
        if not file_obj:
            return []
        content = file_obj.get("content", "")
        if not content.strip():
            return []
        return json.loads(content)
    except Exception as e:
        log.error(f"gist_store.load_log({filename}): fallo al leer -- {e}. "
                  f"Asumiendo lista vacia (mismo criterio que un archivo local ausente).")
        return []


def save_log(filename: str, data: list) -> None:
    """Escribe `data` (serializado a JSON) en el archivo `filename` dentro del gist GIST_ID."""
    _require_config()
    try:
        payload = {"files": {filename: {"content": json.dumps(data, indent=2, default=str)}}}
        r = requests.patch(f"{_API}/gists/{GIST_ID}", headers=_headers(), json=payload, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.error(f"gist_store.save_log({filename}): fallo al escribir -- {e}. "
                  f"El ciclo de hoy pudo no haber quedado registrado -- verificar manualmente.")
