"""
Glitch — Verificación empírica de OrderSide contra una cuenta de PRÁCTICA de
ProjectX/TopstepX (22-sep-2026)
==============================================================================
Resuelve el TODO CRÍTICO documentado en pi/pi_executor.py y GLITCH_RESEARCH_LOG.md
(rama design/pi-execution, 11-sep-2026): la doc oficial de ProjectX dice
"side: 0 = Bid (buy), 1 = Ask (sell)"; el código huérfano brokers/projectx.py
dice lo CONTRARIO ("OrderSide.BID = 0  # Sell"). Una de las dos fuentes está
invertida. Este script coloca UNA orden de mercado minima con side=0 contra
una cuenta de PRACTICA (nunca fondeada -- ver el chequeo de seguridad abajo)
y lee la posicion resultante para determinar empiricamente cual es la
convencion real, sin confiar en ninguna de las dos fuentes.

NO PROBADO CONTRA LA API REAL TODAVIA -- este agente no tiene credenciales
de ProjectX. Los nombres de campo exactos (accountId/contractId/side/type,
el endpoint de resolucion de contrato, el campo de posicion neta) vienen de
la investigacion ya documentada (research log, 11-sep-2026) y del codigo
huerfano brokers/projectx.py -- si la API real responde con un error de
campo/endpoint no reconocido, el error completo queda logueado (ver abajo)
para poder ajustar el script sin adivinar de nuevo.

REQUISITOS (env vars, SOLO estas -- NO requiere Gist ni Telegram, es un
diagnostico standalone, mismo principio que scripts/verify_fix_intento_today.py):
    TOPSTEP_USERNAME   -- email de Topstep
    TOPSTEP_API_KEY    -- API key del addon de TopstepX ($29/mes, dashboard)
    TOPSTEP_ACCOUNT_ID -- accountId de la cuenta de PRACTICA (confirmar en el
                          UI cual accountId es la de practica antes de correr
                          esto -- ver Account/search si no se conoce)

SEGURIDAD: rechaza correr si TOPSTEP_ACCOUNT_ID no está seteado, y pide
confirmacion explicita ("si") antes de colocar la orden real -- incluso
siendo una cuenta de practica (sin dinero real en juego), mismo estandar de
"pedir confirmacion antes de escribir/actuar" ya usado en el resto del repo.
Verifica que la cuenta este FLAT (sin posicion abierta) antes de operar, y
SIEMPRE intenta flatten al final (exito o error), para no dejar una
posicion de practica abierta sin que el usuario se de cuenta.

NO EJECUTAR TODAVIA (22-sep-2026, instruccion explicita del usuario):
este script queda escrito y ESPERANDO -- no se corre contra ninguna
cuenta de Topstep (demo o real) hasta llegar a la Fase 3 del plan ya
confirmado (Combine pagado, Raspberry Pi validado en Telegram hasta el
15-oct-2026). Por eso exige la variable de entorno GLITCH_PI_PHASE3=si
ademas de las confirmaciones interactivas de abajo -- un gate adicional,
separado de las confirmaciones de seguridad de la orden en si, para que
no se corra por accidente/curiosidad antes de esa fecha.

Uso (SOLO en Fase 3):
    GLITCH_PI_PHASE3=si python scripts/verify_orderside_demo.py
"""
from __future__ import annotations
import os
import sys
import json
import time
import datetime as dt

import requests

BASE_URL = "https://api.topstepx.com"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        f"orderside_verification_{dt.datetime.now():%Y%m%d_%H%M%S}.log")

_log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg)
    _log_lines.append(msg)


def log_json(label: str, payload) -> None:
    log(f"{label}:\n{json.dumps(payload, indent=2, default=str)}")


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"FALTA {name} -- seteala antes de correr este script. Abortando, sin llamada a la API.")
        sys.exit(1)
    return v


def save_log() -> None:
    with open(LOG_PATH, "w") as f:
        f.write("\n".join(_log_lines))
    print(f"\nLog completo (para pegar en GLITCH_RESEARCH_LOG.md): {LOG_PATH}")


def main() -> None:
    if os.environ.get("GLITCH_PI_PHASE3", "").strip().lower() != "si":
        print("BLOQUEADO: este script no corre hasta la Fase 3 del plan (Combine pagado, "
              "Raspberry Pi validado en Telegram hasta el 15-oct-2026) -- instruccion explicita "
              "del usuario, 22-sep-2026. Setear GLITCH_PI_PHASE3=si SOLO cuando de verdad se "
              "haya llegado a esa fase. Abortando, sin llamada a la API.")
        sys.exit(1)

    username = require_env("TOPSTEP_USERNAME")
    api_key = require_env("TOPSTEP_API_KEY")
    account_id = require_env("TOPSTEP_ACCOUNT_ID")

    log(f"=== Verificacion de OrderSide -- {dt.datetime.now(dt.timezone.utc).isoformat()} UTC ===")
    log(f"accountId usado: {account_id} -- CONFIRMAR MANUALMENTE en el UI que esta es la cuenta de PRACTICA, no una fondeada, antes de continuar.")
    confirm = input("\n¿Confirmado que accountId de arriba es la cuenta de PRACTICA? Escribir 'si' para continuar: ").strip().lower()
    if confirm != "si":
        print("Cancelado -- no se hizo ninguna llamada a la API.")
        return

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json", "Accept": "text/plain"})

    # ---- 1. Auth ----
    log("\n--- 1. POST /api/Auth/loginKey ---")
    resp = requests.post(f"{BASE_URL}/api/Auth/loginKey",
                          json={"userName": username, "apiKey": api_key}, timeout=10)
    body = resp.json()
    log_json("Response (token omitido del log)", {**body, "token": "***REDACTED***" if body.get("token") else None})
    if not body.get("success"):
        log(f"AUTH FALLO: {body.get('errorMessage')} -- abortando, nada mas que hacer.")
        save_log()
        sys.exit(1)
    token = body["token"]
    session.headers["Authorization"] = f"Bearer {token}"
    log("Auth OK.")

    # ---- 2. Resolver contrato MES ----
    log("\n--- 2. POST /api/Contract/available (buscando MES) ---")
    resp = session.post(f"{BASE_URL}/api/Contract/available", json={"live": False}, timeout=10)
    try:
        contracts_body = resp.json()
    except Exception:
        log(f"Contract/available devolvio algo no-JSON (status {resp.status_code}): {resp.text[:500]}")
        log("Si esto falla, probar el endpoint alterno Contract/search (ver GLITCH_RESEARCH_LOG.md, 11-sep-2026 -- "
            "dos nombres distintos vistos en fuentes distintas, nunca resuelto cual es el correcto).")
        save_log()
        sys.exit(1)
    contracts = contracts_body if isinstance(contracts_body, list) else contracts_body.get("contracts", [])
    log_json("Contratos recibidos (primeros 5)", contracts[:5])
    mes = [c for c in contracts if "MES" in str(c.get("name", "")) or "MES" in str(c.get("symbol", ""))]
    if not mes:
        log("No se encontro ningun contrato MES en la respuesta -- revisar el JSON completo arriba para el nombre real del campo/simbolo.")
        save_log()
        sys.exit(1)
    mes.sort(key=lambda c: str(c.get("expirationDate", "")))
    contract = mes[0]
    contract_id = contract.get("id") or contract.get("contractId")
    log(f"Contrato MES resuelto: {contract.get('name')} contractId={contract_id}")

    # ---- 3. Confirmar que la cuenta esta FLAT antes de operar ----
    log("\n--- 3. POST /api/Position/searchOpen (chequeo pre-orden, debe estar flat) ---")
    resp = session.post(f"{BASE_URL}/api/Position/searchOpen", json={"accountId": int(account_id)}, timeout=10)
    pre_positions = resp.json()
    pre_list = pre_positions if isinstance(pre_positions, list) else pre_positions.get("positions", [])
    log_json("Posiciones abiertas ANTES de la orden", pre_list)
    if pre_list:
        log("La cuenta NO esta flat -- hay posiciones abiertas de antes. Abortando por seguridad, "
            "no se coloca ninguna orden nueva. Cerrar/verificar manualmente en el UI antes de reintentar.")
        save_log()
        sys.exit(1)
    log("Cuenta confirmada FLAT.")

    # ---- 4. Colocar la orden de prueba: side=0, tamaño minimo ----
    log("\n--- 4. POST /api/Order/place -- side=0, size=1, MARKET ---")
    log(f"A punto de colocar: accountId={account_id} contractId={contract_id} type=2 (MARKET) side=0 size=1")
    confirm2 = input("Escribir 'si' para colocar esta orden real (en la cuenta de PRACTICA confirmada arriba): ").strip().lower()
    if confirm2 != "si":
        print("Cancelado antes de colocar la orden -- no se movio nada.")
        save_log()
        return

    order_payload = {"accountId": int(account_id), "contractId": contract_id, "type": 2, "side": 0, "size": 1}
    resp = session.post(f"{BASE_URL}/api/Order/place", json=order_payload, timeout=10)
    order_body = resp.json()
    log_json("Order/place payload enviado", order_payload)
    log_json("Order/place respuesta", order_body)

    if not order_body.get("success"):
        log(f"LA ORDEN FALLO: {order_body.get('errorMessage')} -- revisar el error arriba. "
            f"Nada que flatten (la orden nunca se ejecuto).")
        save_log()
        sys.exit(1)

    # ---- 5. Leer la posicion resultante -- ESTA es la evidencia real ----
    log("\n--- 5. POST /api/Position/searchOpen (posicion resultante -- LA EVIDENCIA) ---")
    time.sleep(3)  # margen para que el fill se refleje
    resp = session.post(f"{BASE_URL}/api/Position/searchOpen", json={"accountId": int(account_id)}, timeout=10)
    post_positions = resp.json()
    post_list = post_positions if isinstance(post_positions, list) else post_positions.get("positions", [])
    log_json("Posiciones abiertas DESPUES de la orden (side=0)", post_list)

    veredicto = "NO SE PUDO DETERMINAR -- revisar el JSON completo arriba a mano."
    try:
        match = next(p for p in post_list if str(p.get("contractId")) == str(contract_id))
        net = match.get("netPos", match.get("size", match.get("quantity")))
        if net is not None:
            if net > 0:
                veredicto = f"netPos={net} (positivo) -> side=0 EJECUTO UNA COMPRA (LONG). Confirma la doc oficial, CONTRADICE brokers/projectx.py."
            elif net < 0:
                veredicto = f"netPos={net} (negativo) -> side=0 EJECUTO UNA VENTA (SHORT). Confirma brokers/projectx.py, CONTRADICE la doc oficial."
    except StopIteration:
        pass
    log(f"\n>>> VEREDICTO: {veredicto}")
    log(">>> CONFIRMAR TAMBIEN en el UI de la cuenta de practica (no solo en este log) antes de dar esto por definitivo.")

    # ---- 6. SIEMPRE flatten al final ----
    log("\n--- 6. Flatten de limpieza (POST /api/Position/closeContract) ---")
    close_payload = {"accountId": int(account_id), "contractId": contract_id}
    resp = session.post(f"{BASE_URL}/api/Position/closeContract", json=close_payload, timeout=10)
    try:
        close_body = resp.json()
    except Exception:
        close_body = {"raw_text": resp.text[:500], "status_code": resp.status_code}
    log_json("Position/closeContract respuesta", close_body)
    log("Verificar en el UI que la posicion quedo en 0 -- este script no reintenta el flatten si falla.")

    save_log()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"\nERROR NO MANEJADO: {e!r}")
        log("Si una orden ya se coloco antes de este error, VERIFICAR Y CERRAR MANUALMENTE en el UI de la cuenta de practica -- no asumir que quedo flat.")
        save_log()
        raise
