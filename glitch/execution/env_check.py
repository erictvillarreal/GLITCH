"""
Glitch — Chequeo unificado de variables de entorno al arranque (01-sep-2026)
================================================================================
UNICA fuente de verdad de "que variables de entorno necesita ESTE
scheduler". Se llama en la PRIMERA linea util de combo2d_scheduler.py y
geometry_scheduler.py -- ANTES de cualquier otro import del proyecto.

POR QUE ESTE MODULO EXISTE, DELIBERADAMENTE SIN DEPENDENCIAS DE
execution/contracts.py, scheduler/telegram_bot.py, NI
execution/gist_store.py: 2.5 semanas (14-ago a 01-sep-2026) de fallos
en combo2d, descubiertos UNO A LA VEZ via crash-arreglo-siguiente-crash
-- cada variable faltante se validaba en un modulo DISTINTO, en un
punto DISTINTO de la cadena de imports (contracts.py al importarse,
telegram_bot.py al importarse, gist_store.py solo cuando load_log()/
save_log() se llamaban DENTRO de run(), ya bien entrada la ejecucion).
Si alguno de esos tres modulos se importara AQUI, dispararia su propio
chequeo individual (y su propio crash, reportando solo ESA variable)
antes de que este chequeo unificado alcance a correr siquiera --
exactamente el problema que este modulo existe para eliminar. Por eso
usa `requests` directo para el envio a Telegram (duplicacion minima y
deliberada de 5 lineas), no la funcion `send()` compartida.

Ver GLITCH_RESEARCH_LOG.md para la cronologia completa del problema que
motivo esto.
"""
from __future__ import annotations
import os
import sys
from typing import Union

import requests

# un nombre, o una tupla de nombres alternativos ("A o B") -- alias solo para
# el type hint de abajo, `from __future__ import annotations` lo deja como
# string sin evaluar, pero Union() en vez de `str | tuple` evita romper en
# Python 3.9 si algo llegara a evaluarlo en runtime (ej. typing.get_type_hints).
RequirementSpec = Union[str, tuple]


def require_env(required: list, scheduler_label: str) -> None:
    """
    Verifica TODAS las variables en `required` de un jalon (cada elemento
    puede ser un nombre simple, o una tupla de nombres alternativos donde
    basta con que UNO este presente, ej. MASSIVE_API_KEY o POLYGON_API_KEY).

    Si falta cualquiera: manda UN SOLO mensaje a Telegram listando TODAS
    las faltantes juntas (best-effort -- si el envio mismo falla porque
    TELEGRAM_BOT_TOKEN/CHAT_ID tambien faltan, se loguea a stderr en vez
    de sumar un traceback no manejado encima) y termina el proceso.

    Si todo esta presente: no hace nada, deja que el resto del arranque
    continue normal.
    """
    missing = []
    for spec in required:
        names = (spec,) if isinstance(spec, str) else spec
        if not any(os.environ.get(n) for n in names):
            missing.append(" o ".join(names))

    if not missing:
        return

    msg = (f"GLITCH - {scheduler_label} | STARTUP FAILED\n"
           f"Faltan {len(missing)} variable(s) de entorno -- TODAS de un jalon, no una por vez:\n"
           + "\n".join(f"  - {name}" for name in missing))
    print(f"FATAL:\n{msg}", file=sys.stderr)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=10,
            )
        except Exception as e:
            print(f"(ademas, no se pudo notificar por Telegram: {e})", file=sys.stderr)
    else:
        print("(no se pudo notificar por Telegram -- TELEGRAM_BOT_TOKEN/CHAT_ID tambien faltan)",
              file=sys.stderr)

    sys.exit(1)
