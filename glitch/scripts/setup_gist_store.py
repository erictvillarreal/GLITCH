"""
Glitch — Crea el gist privado de persistencia (27-ago-2026)
==============================================================
Corrida UNICA, manual, para crear el gist que usaran combo2d_scheduler.py
y geometry_scheduler.py via execution/gist_store.py. No forma parte del
loop de ningun scheduler.

Requiere GITHUB_GIST_TOKEN en el entorno -- el token NUEVO Y SEPARADO
con scope UNICAMENTE "gist" (nunca "repo", nunca el token usado para
pushear el repo).

Uso:
    export GITHUB_GIST_TOKEN="ghp_..."
    python scripts/setup_gist_store.py

Imprime el GIST_ID resultante -- copiarlo a las variables de entorno de
AMBOS servicios de Railway (combo2d y geometry) como GIST_ID.
"""
from __future__ import annotations
import os
import sys

import requests

TOKEN = os.environ.get("GITHUB_GIST_TOKEN")
if not TOKEN:
    print("ERROR: falta GITHUB_GIST_TOKEN en el entorno.")
    sys.exit(1)

PAYLOAD = {
    "description": "GLITCH -- estado de paper trading (combo2d + geometry). Privado, no compartir la URL.",
    "public": False,
    "files": {
        "combo2d_log.json": {"content": "[]"},
        "geometry_mes_log.json": {"content": "[]"},
    },
}


def main():
    r = requests.post(
        "https://api.github.com/gists",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
        json=PAYLOAD,
        timeout=15,
    )
    r.raise_for_status()
    gist = r.json()
    print(f"Gist creado: {gist['html_url']}")
    print(f"GIST_ID={gist['id']}")
    print()
    print("Copiar GIST_ID a las variables de entorno de AMBOS servicios de Railway")
    print("(combo2d y geometry), junto con GITHUB_GIST_TOKEN.")


if __name__ == "__main__":
    main()
