"""
GLITCH -- Verificacion empirica de OrderSide contra la cuenta PRACTICE de ProjectX (03-oct-2026)
===============================================================================================
Resuelve el bloqueante #1: la documentacion oficial de ProjectX dice `side: 0 = Bid (buy),
1 = Ask (sell)`; brokers/projectx.py::OrderSide dice lo CONTRARIO (BID=0 # Sell). Una de las
dos esta invertida. Este script coloca UNA orden de mercado de tamaño 1 con side=0, lee la
posicion que realmente resulta, y deduce el mapeo REAL -- sin confiar en ninguna de las dos
fuentes. Si todo sale limpio escribe pi/orderside_verified.json con EXACTAMENTE dos claves:

    {"BUY_SIDE_INT": <int>, "SELL_SIDE_INT": <int>}

que es el formato que pi/pi_executor.py::_load_verified_side_map() espera.

NO es automatizable sin supervision la primera vez -- por diseño:
  * Exige GLITCH_PI_PHASE3=si en el entorno (el gate del 22-sep, el mismo que abre pi_executor).
  * Exige --account-id explicito (nunca "la primera cuenta de la lista"), que debe existir y estar
    activa en la cuenta de TopstepX; imprime el registro completo de la cuenta y exige que ESCRIBAS
    ese id de vuelta, mas "si", ANTES de la orden. (No hay forma de saltarse la confirmacion.)
  * La cuenta debe estar PLANA (sin posiciones ni ordenes abiertas) antes de operar.
  * Una sola orden, tamaño 1, MES. Despues SIEMPRE cierra con closeContract (que NO depende del lado)
    y comprueba que la cuenta quedo plana; si no, te dice en voz alta que la cierres a mano en TopstepX.
  * No sobrescribe un orderside_verified.json existente sin --force.
  * --dry-run hace login + chequeos de cuenta/contrato y se detiene ANTES de la orden: sirve para la
    primera corrida (valida credenciales, accountId y contrato sin mover nada).

Credenciales: solo por variables de entorno (TOPSTEP_USERNAME, TOPSTEP_API_KEY) -- se leen en el Pi,
nunca se imprimen ni se escriben al log (el token JWT se redacta).

Uso (en el Pi, en la misma sesion donde exportaste las credenciales):
    GLITCH_PI_PHASE3=si python pi/verify_orderside_demo.py --account-id 28197753 --dry-run   # primero esto
    GLITCH_PI_PHASE3=si python pi/verify_orderside_demo.py --account-id 28197753             # luego la orden real

Todos los nombres de campo de la API (accountId/contractId/type/side/size, Position `type`/`size`/
`netPos`) vienen de la documentacion y del cliente existente -- NO se han probado contra la API real.
Por eso el log (pi/orderside_verification_<fecha>.log) guarda la respuesta CRUDA de cada llamada: si algun
campo no coincide, ahi se ve cual es el real. En particular registra la forma real de una Position, para
confirmar si `netPos` (que pi_executor::_has_untracked_position y brokers/projectx.py asumen) existe.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from typing import Optional

import requests

BASE_URL = "https://api.topstepx.com"
HERE = os.path.dirname(os.path.abspath(__file__))
VERIFIED_PATH = os.path.join(HERE, "orderside_verified.json")   # el MISMO path que pi_executor.ORDERSIDE_VERIFIED_PATH
MARKET = 2        # OrderType.MARKET (brokers/projectx.py::OrderType)
TEST_SIDE = 0     # el lado que se prueba: la doc oficial dice Bid=Buy, el codigo huerfano dice Sell
TEST_SIZE = 1
PRODUCT_CODE = "MES"

_log_lines: list = []


def log(msg: str) -> None:
    print(msg)
    _log_lines.append(msg)


def log_json(label: str, payload) -> None:
    log(f"{label}:\n{json.dumps(payload, indent=2, default=str)}")


# ── Logica pura (testeable sin red) ──────────────────────────────────────────────────────────
def position_direction(pos: dict) -> Optional[int]:
    """+1 si la posicion es LONG, -1 si es SHORT, None si no se puede determinar.

    Soporta las dos formas que se han visto/documentado, porque cual es la real NO esta verificado:
      * `netPos` (con signo) -- lo que asumen brokers/projectx.py y pi_executor.
      * `type` (1=Long, 2=Short) + `size` -- la forma que documenta la API de ProjectX (Position model).
    Si ambas faltan o son inconsistentes devuelve None -- nunca se adivina el lado.
    """
    net = pos.get("netPos")
    if isinstance(net, (int, float)) and not isinstance(net, bool) and net != 0:
        return 1 if net > 0 else -1
    ptype, size = pos.get("type"), pos.get("size", pos.get("quantity"))
    if ptype in (1, 2) and isinstance(size, (int, float)) and not isinstance(size, bool) and size > 0:
        return 1 if ptype == 1 else -1
    return None


def infer_side_map(test_side_int: int, resulting_direction: Optional[int]) -> Optional[dict]:
    """Dado que se envio `side=test_side_int` y la posicion resultante fue LONG (+1) o SHORT (-1),
    devuelve {"BUY_SIDE_INT", "SELL_SIDE_INT"}. None si la direccion no se pudo determinar.

    LONG tras enviar side=X  => X compra  => BUY=X,  SELL=1-X
    SHORT tras enviar side=X => X vende   => SELL=X, BUY=1-X
    (ProjectX solo tiene dos lados: 0 y 1.)"""
    if resulting_direction not in (1, -1) or test_side_int not in (0, 1):
        return None
    other = 1 - test_side_int
    if resulting_direction == 1:
        return {"BUY_SIDE_INT": test_side_int, "SELL_SIDE_INT": other}
    return {"BUY_SIDE_INT": other, "SELL_SIDE_INT": test_side_int}


def pick_front_month(contracts: list, product_code: str, now: Optional[dt.datetime] = None) -> Optional[dict]:
    """Contrato mas cercano a vencer cuyo nombre contiene `product_code`, DESCARTANDO los ya vencidos.
    (pi_executor.resolve_contract_id ordena igual pero sin descartar vencidos -- aqui un vencido solo
    haria fallar la prueba, asi que se filtra por robustez.)"""
    now = now or dt.datetime.now(dt.timezone.utc)
    matches = []
    for c in contracts:
        name = str(c.get("name", ""))
        if product_code not in name:
            continue
        exp = c.get("expirationDate")
        if exp:
            try:
                exp_dt = dt.datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=dt.timezone.utc)
                if exp_dt <= now:
                    continue
            except ValueError:
                pass
        matches.append(c)
    matches.sort(key=lambda c: str(c.get("expirationDate", "")))
    return matches[0] if matches else None


def as_list(body, key: str, endpoint: str) -> list:
    """Extrae la lista de una respuesta de ProjectX. Una respuesta malformada (no-JSON, success=false, sin la
    clave esperada) LANZA en vez de contarse como "lista vacia": un endpoint roto no puede hacer que la cuenta
    parezca plana. Con una respuesta valida y vacia ({"positions": [], "success": true}) devuelve []."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and "_non_json" not in body and body.get("success") is not False and key in body:
        value = body[key]
        return value if isinstance(value, list) else []
    raise RuntimeError(f"{endpoint}: respuesta inesperada, no se puede confiar en ella -> {json.dumps(body, default=str)[:300]}")


def write_verified_map_atomic(path: str, side_map: dict) -> None:
    """Escribe SOLO las dos claves que pi_executor espera (la evidencia va al log, no al JSON)."""
    payload = {"BUY_SIDE_INT": int(side_map["BUY_SIDE_INT"]), "SELL_SIDE_INT": int(side_map["SELL_SIDE_INT"])}
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


# ── I/O contra ProjectX ──────────────────────────────────────────────────────────────────────
class Api:
    def __init__(self, username: str, api_key: str):
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json", "Accept": "text/plain"})
        self._login(username, api_key)

    def _login(self, username: str, api_key: str) -> None:
        r = requests.post(f"{BASE_URL}/api/Auth/loginKey", json={"userName": username, "apiKey": api_key}, timeout=15)
        body = r.json()
        log_json("Auth/loginKey respuesta (token redactado)", {**body, "token": "***REDACTED***" if body.get("token") else None})
        if not body.get("success"):
            raise SystemExit(f"AUTH FALLO: {body.get('errorMessage')} -- nada mas que hacer.")
        self.s.headers["Authorization"] = f"Bearer {body['token']}"

    def post(self, path: str, payload: dict):
        r = self.s.post(f"{BASE_URL}{path}", json=payload, timeout=15)
        try:
            body = r.json()
        except Exception:
            body = {"_non_json": r.text[:500], "_status": r.status_code}
        return body

    def positions(self, account_id: int) -> list:
        return as_list(self.post("/api/Position/searchOpen", {"accountId": account_id}), "positions", "Position/searchOpen")

    def open_orders(self, account_id: int) -> list:
        return as_list(self.post("/api/Order/searchOpen", {"accountId": account_id}), "orders", "Order/searchOpen")


def _save_log(stamp: str) -> str:
    path = os.path.join(HERE, f"orderside_verification_{stamp}.log")
    with open(path, "w") as f:
        f.write("\n".join(_log_lines))
    print(f"\nLog completo (pegalo en GLITCH_RESEARCH_LOG.md): {path}")
    return path


def _final_flat_check(api: Api, account_id: int) -> bool:
    time.sleep(3)
    pos = api.positions(account_id)
    log_json("Posiciones abiertas DESPUES del cierre", pos)
    return len([p for p in pos if position_direction(p) is not None]) == 0


def run(args) -> int:
    if os.environ.get("GLITCH_PI_PHASE3", "").strip().lower() != "si":
        print("BLOQUEADO: exporta GLITCH_PI_PHASE3=si (el mismo gate del 22-sep que abre pi_executor) para correr "
              "esto. Sin llamadas a la API.")
        return 1
    username, api_key = os.environ.get("TOPSTEP_USERNAME"), os.environ.get("TOPSTEP_API_KEY")
    if not username or not api_key:
        print("FALTAN TOPSTEP_USERNAME y/o TOPSTEP_API_KEY en el entorno. Sin llamadas a la API.")
        return 1
    if os.path.exists(VERIFIED_PATH) and not (args.force or args.dry_run):
        print(f"Ya existe {VERIFIED_PATH}. Si de verdad quieres re-verificar, usa --force. No se hizo nada.")
        return 1

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    account_id = int(args.account_id)
    log(f"=== Verificacion de OrderSide -- {dt.datetime.now(dt.timezone.utc).isoformat()} UTC | accountId={account_id} | "
        f"{'DRY-RUN' if args.dry_run else 'ORDEN REAL (Practice)'} ===")
    try:
        api = Api(username, api_key)

        # 1. La cuenta existe y esta activa -- se imprime el registro COMPLETO para que lo veas tu
        accounts = api.post("/api/Account/search", {"onlyActiveAccounts": True})
        acc_list = accounts if isinstance(accounts, list) else accounts.get("accounts", [])
        acct = next((a for a in acc_list if str(a.get("id")) == str(account_id)), None)
        log_json("Cuentas activas visibles (ids)", [{"id": a.get("id"), "name": a.get("name")} for a in acc_list])
        if acct is None:
            log(f"La cuenta {account_id} NO aparece entre las cuentas activas -- abortando sin operar.")
            return 1
        log_json("Registro de la cuenta elegida", acct)

        # 2. Contrato
        contracts = api.post("/api/Contract/available", {"live": False})
        c_list = contracts if isinstance(contracts, list) else contracts.get("contracts", [])
        contract = pick_front_month(c_list, PRODUCT_CODE)
        if contract is None:
            log_json("Contratos recibidos (primeros 5)", c_list[:5])
            log(f"No se encontro un contrato {PRODUCT_CODE} vigente -- revisar el JSON de arriba. Abortando sin operar.")
            return 1
        contract_id = contract.get("id") or contract.get("contractId")
        log(f"Contrato: {contract.get('name')}  contractId={contract_id}  vence={contract.get('expirationDate')}")

        # 3. La cuenta debe estar PLANA
        pre_pos, pre_orders = api.positions(account_id), api.open_orders(account_id)
        log_json("Posiciones abiertas ANTES (la forma real de una Position, si hay alguna, queda aqui)", pre_pos)
        log_json("Ordenes abiertas ANTES", pre_orders)
        if pre_pos or pre_orders:
            log("La cuenta NO esta plana (posiciones u ordenes abiertas) -- abortando por seguridad. Limpiar en TopstepX y reintentar.")
            return 1
        log("Cuenta PLANA confirmada.")

        if args.dry_run:
            log("\nDRY-RUN completo: credenciales, cuenta y contrato OK. NO se coloco ninguna orden. "
                "Para la orden real, repetir sin --dry-run.")
            return 0

        # 4. Doble confirmacion humana ANTES de mover nada
        print(f"\nA punto de colocar UNA orden de mercado REAL en la cuenta {account_id} "
              f"(nombre: {acct.get('name')!r}): contrato {contract.get('name')}, side={TEST_SIDE}, size={TEST_SIZE}.")
        typed = input(f"Escribe el accountId ({account_id}) para confirmar que ES la cuenta PRACTICE: ").strip()
        if typed != str(account_id):
            print("El id no coincide -- cancelado, no se movio nada.")
            return 1
        if input("Escribe 'si' para enviar la orden: ").strip().lower() != "si":
            print("Cancelado -- no se movio nada.")
            return 1

        payload = {"accountId": account_id, "contractId": contract_id, "type": MARKET, "side": TEST_SIDE, "size": TEST_SIZE}
        log_json("Order/place payload", payload)
        placed = api.post("/api/Order/place", payload)
        log_json("Order/place respuesta", placed)
        if not (isinstance(placed, dict) and placed.get("success")):
            log("La orden fallo -- no hay nada que cerrar. Revisar el error de arriba.")
            return 1

        # 5. La evidencia: la posicion REAL que resulto (reintenta unos segundos hasta que aparezca el fill)
        post_pos: list = []
        for _ in range(5):
            time.sleep(2)
            post_pos = api.positions(account_id)
            if post_pos:
                break
        log_json("Posiciones abiertas DESPUES de la orden (LA EVIDENCIA)", post_pos)
        mine = [p for p in post_pos if str(p.get("contractId")) == str(contract_id)]
        direction = position_direction(mine[0]) if mine else None
        side_map = infer_side_map(TEST_SIDE, direction)

        # 6. SIEMPRE cerrar -- closeContract no depende del lado, asi que funciona aunque la inferencia haya fallado
        log("\nCierre de limpieza: POST /api/Position/closeContract")
        closed = api.post("/api/Position/closeContract", {"accountId": account_id, "contractId": contract_id})
        log_json("closeContract respuesta", closed)
        flat = _final_flat_check(api, account_id)
        if not flat:
            log("\n!!! LA CUENTA NO QUEDO PLANA. CIERRA LA POSICION MANUALMENTE EN TOPSTEPX AHORA. !!!")

        if side_map is None:
            log("\nNO SE PUDO DETERMINAR el lado (la posicion no aparecio o no trae netPos ni type/size reconocibles). "
                "NO se escribio orderside_verified.json. Revisar la respuesta cruda de arriba.")
            return 1
        if not flat:
            log("\nSe dedujo un mapeo, pero la cuenta no quedo plana: NO se escribe orderside_verified.json hasta confirmar "
                "el cierre a mano y volver a correr.")
            return 1

        log(f"\n>>> side={TEST_SIDE} produjo una posicion {'LONG (compra)' if direction == 1 else 'SHORT (venta)'}.")
        log(f">>> Mapeo verificado: {side_map}")
        log(">>> Contrastar tambien en el historial de TopstepX (una orden de compra/venta de 1 MES en la cuenta Practice).")
        write_verified_map_atomic(VERIFIED_PATH, side_map)
        log(f">>> Escrito {VERIFIED_PATH}")
        return 0
    except SystemExit as e:
        log(str(e))
        return 1
    except Exception as e:  # noqa: BLE001
        log(f"\nERROR NO MANEJADO: {e!r}\nSi una orden ya se coloco antes del error, VERIFICA Y CIERRA A MANO en TopstepX -- "
            f"no asumas que quedo plana.")
        return 1
    finally:
        _save_log(stamp)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica empiricamente OrderSide contra la cuenta Practice (una orden, tamaño 1).")
    ap.add_argument("--account-id", required=True, help="accountId de la cuenta PRACTICE (explicito, nunca se adivina)")
    ap.add_argument("--dry-run", action="store_true", help="login + chequeos y se detiene ANTES de la orden")
    ap.add_argument("--force", action="store_true", help="permite sobrescribir un orderside_verified.json existente")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
