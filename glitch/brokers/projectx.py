"""
Glitch — ProjectX / TopstepX Broker Adapter
=============================================
API oficial de Topstep via ProjectX Gateway.

Docs: https://gateway.docs.projectx.com
Base: https://api.topstepx.com
User Hub: https://rtc.topstepx.com/hubs/user
Market Hub: https://rtc.topstepx.com/hubs/market

AUTH:
  POST /api/Auth/loginKey
  { "userName": "email", "apiKey": "your-api-key" }
  → { "token": "jwt", "success": true }

COSTO: $29/mes addon en TopstepX dashboard
CONTACTO: dashboardapi@topstep.com
"""

from __future__ import annotations
import os, json, time, requests
from dataclasses import dataclass
from typing import Optional, Any
from enum import IntEnum


BASE_URL   = "https://api.topstepx.com"
USER_HUB   = "https://rtc.topstepx.com/hubs/user"
MARKET_HUB = "https://rtc.topstepx.com/hubs/market"


# ── Order enums (from ProjectX docs) ────────────────────────────────────────

class OrderType(IntEnum):
    LIMIT  = 1
    MARKET = 2
    STOP   = 4
    STOP_LIMIT = 3

class OrderSide(IntEnum):
    # !!! VERIFICADO EN VIVO el 4-oct-2026 (pi/verify_orderside_demo.py, cuenta Practice): side=0 abrio una
    # !!! posicion LONG, es decir 0 = COMPRA y 1 = VENTA -- lo CONTRARIO de los comentarios de abajo.
    # !!! Los NOMBRES y comentarios de este enum estan invertidos. No se corrige aqui para no cambiar en silencio
    # !!! a los llamadores legados (run_glitch_xfa.py, core/safety.py, flatten_position); pi_executor.py NO usa
    # !!! este enum: lee el mapeo verificado de pi/orderside_verified.json.
    BID = 0   # Sell  (en la practica: BUY -- ver arriba)
    ASK = 1   # Buy   (en la practica: SELL -- ver arriba)


# ── Credentials ──────────────────────────────────────────────────────────────

@dataclass
class ProjectXCredentials:
    user_name: str    # Topstep email
    api_key:   str    # From TopstepX API addon dashboard

    @classmethod
    def from_env(cls) -> "ProjectXCredentials":
        return cls(
            user_name = os.environ["TOPSTEP_USERNAME"],
            api_key   = os.environ["TOPSTEP_API_KEY"],
        )

    @classmethod
    def from_file(cls, path: str = ".projectx_creds.json") -> "ProjectXCredentials":
        d = json.load(open(path))
        return cls(**d)


# ── Client ────────────────────────────────────────────────────────────────────

def position_net(p: dict) -> int:
    """Tamano CON SIGNO de una posicion de ProjectX: +n LONG, -n SHORT, 0 si no se puede determinar o es plana.

    La forma REAL (verificada 4-oct-2026) es `type` (1=Long, 2=Short) + `size`. `netPos` (con signo) se acepta
    solo por compatibilidad: no existe en la API de ProjectX/TopstepX."""
    net = p.get("netPos")
    if isinstance(net, (int, float)) and not isinstance(net, bool) and net != 0:
        return int(net)
    ptype, size = p.get("type"), p.get("size")
    if ptype in (1, 2) and isinstance(size, (int, float)) and not isinstance(size, bool) and size > 0:
        return int(size) if ptype == 1 else -int(size)
    return 0


def position_is_open(p: dict) -> bool:
    """True si el registro (de un listado de posiciones ABIERTAS) representa una posicion abierta.

    Conservador: un registro con tamano reconocible y cero es plano; un registro cuya forma no se reconoce
    (ni netPos ni size) se trata como ABIERTO -- el endpoint solo lista posiciones abiertas, y ante la duda
    es mejor abstenerse de operar que apilar una orden encima de una posicion que no entendemos."""
    if position_net(p) != 0:
        return True
    return not ("netPos" in p or "size" in p)


class ProjectXClient:
    """
    ProjectX / TopstepX REST client.

    Usage:
        creds  = ProjectXCredentials.from_file()
        client = ProjectXClient(creds)
        client.authenticate()

        accounts = client.get_accounts()
        account_id = accounts[0]["id"]

        contracts = client.get_contracts()
        mes = next(c for c in contracts if "MES" in c["name"])

        order_id = client.place_market_order(
            account_id  = account_id,
            contract_id = mes["id"],
            side        = OrderSide.ASK,   # Buy
            size        = 3,
        )
    """

    def __init__(self, creds: ProjectXCredentials, verbose: bool = True):
        self.creds   = creds
        self.verbose = verbose
        self._token: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "text/plain",
        })

    # ── Auth ──────────────────────────────────────────────────────────────

    def authenticate(self) -> str:
        """POST /api/Auth/loginKey → JWT token."""
        resp = self._post("/api/Auth/loginKey", {
            "userName": self.creds.user_name,
            "apiKey":   self.creds.api_key,
        }, auth=False)

        if not resp.get("success"):
            raise RuntimeError(f"Auth failed: {resp.get('errorMessage')}")

        self._token = resp["token"]
        self._session.headers["Authorization"] = f"Bearer {self._token}"

        if self.verbose:
            print(f"[ProjectX] Authenticated ✓")
        return self._token

    def validate_session(self) -> bool:
        """POST /api/Auth/validate — check if token still valid."""
        try:
            resp = self._post("/api/Auth/validate", {})
            return resp.get("success", False)
        except:
            return False

    def ensure_auth(self):
        if not self._token or not self.validate_session():
            self.authenticate()

    # ── Accounts ──────────────────────────────────────────────────────────

    def get_accounts(self, only_active: bool = True) -> list[dict]:
        """POST /api/Account/search"""
        self.ensure_auth()
        resp = self._post("/api/Account/search", {
            "onlyActiveAccounts": only_active
        })
        accounts = resp if isinstance(resp, list) else resp.get("accounts", [])
        if self.verbose:
            for a in accounts:
                print(f"[ProjectX] Account: {a.get('name')} "
                      f"ID={a.get('id')} "
                      f"Balance=${a.get('balance', 0):,.0f}")
        return accounts

    def get_account_balance(self, account_id: int) -> dict:
        """GET account balance and P&L."""
        self.ensure_auth()
        return self._post("/api/Account/balance", {"accountId": account_id})

    # ── Contracts ─────────────────────────────────────────────────────────

    def get_contracts(self, live: bool = False) -> list[dict]:
        """POST /api/Contract/available"""
        self.ensure_auth()
        resp = self._post("/api/Contract/available", {"live": live})
        return resp if isinstance(resp, list) else resp.get("contracts", [])

    def find_mes_contract(self, live: bool = False) -> dict:
        """Find the front-month MES contract."""
        contracts = self.get_contracts(live)
        mes = [c for c in contracts if "MES" in c.get("name", "")]
        if not mes:
            raise ValueError("MES contract not found")
        # Sort by expiry, take front month
        mes.sort(key=lambda c: c.get("expirationDate", ""))
        if self.verbose:
            print(f"[ProjectX] MES contract: {mes[0].get('name')} "
                  f"ID={mes[0].get('id')}")
        return mes[0]

    # ── Orders ────────────────────────────────────────────────────────────

    def place_order(
        self,
        account_id:  int,
        contract_id: str,
        order_type:  OrderType,
        side:        OrderSide,
        size:        int,
        price:       Optional[float] = None,
        stop_price:  Optional[float] = None,
    ) -> int:
        """
        POST /api/Order/place
        Returns orderId.
        """
        self.ensure_auth()
        payload = {
            "accountId":  account_id,
            "contractId": contract_id,
            "type":       int(order_type),
            "side":       int(side),
            "size":       size,
        }
        if price is not None:
            payload["price"] = price
        if stop_price is not None:
            payload["stopPrice"] = stop_price

        resp = self._post("/api/Order/place", payload)

        if not resp.get("success"):
            raise RuntimeError(f"Order failed: {resp.get('errorMessage')}")

        order_id = resp["orderId"]
        if self.verbose:
            action = "BUY" if side == OrderSide.ASK else "SELL"
            print(f"[ProjectX] Order placed: {action} {size}x "
                  f"@ {order_type.name} → orderId={order_id}")
        return order_id

    def place_market_order(
        self, account_id: int, contract_id: str,
        side: OrderSide, size: int
    ) -> int:
        return self.place_order(
            account_id, contract_id,
            OrderType.MARKET, side, size
        )

    def place_limit_order(
        self, account_id: int, contract_id: str,
        side: OrderSide, size: int, price: float
    ) -> int:
        return self.place_order(
            account_id, contract_id,
            OrderType.LIMIT, side, size, price=price
        )

    def place_stop_order(
        self, account_id: int, contract_id: str,
        side: OrderSide, size: int, stop_price: float
    ) -> int:
        return self.place_order(
            account_id, contract_id,
            OrderType.STOP, side, size, stop_price=stop_price
        )

    def cancel_order(self, order_id: int) -> bool:
        """POST /api/Order/cancel"""
        self.ensure_auth()
        resp = self._post("/api/Order/cancel", {"orderId": order_id})
        return resp.get("success", False)

    def cancel_all_orders(self, account_id: int) -> dict:
        """POST /api/Order/cancelallorders -- usado por core/safety.py FlattenFailsafe."""
        self.ensure_auth()
        return self._post("/api/Order/cancelallorders", {"accountId": account_id})

    def get_open_orders(self, account_id: int) -> list[dict]:
        """POST /api/Order/searchOpen -- ordenes abiertas. Endpoint y clave "orders" VERIFICADOS en vivo el
        4-oct-2026 (respuesta {"orders": [], "success": true} con la cuenta plana). Antes: /api/Order/search +
        onlyOpen, nunca verificado."""
        self.ensure_auth()
        resp = self._post("/api/Order/searchOpen", {
            "accountId": account_id,
        })
        return resp if isinstance(resp, list) else resp.get("orders", [])

    def get_orders(self, account_id: int, only_open: bool = False) -> list[dict]:
        """
        POST /api/Order/search -- generaliza get_open_orders() (que fuerza
        onlyOpen=True) para poder consultar TAMBIEN ordenes ya resueltas
        (fill price, timestamp de cierre). Anadido 29-sep-2026 para que
        pi/pi_executor.py pueda leer el precio de fill REAL de una orden
        despues de que se llena, en vez de asumir el precio objetivo
        (tp_price/sl_price) como si fuera el fill exacto. No toca la
        logica de OrderSide -- ver bloqueante #1 en la clase OrderSide
        arriba, sigue sin resolver.
        """
        self.ensure_auth()
        resp = self._post("/api/Order/search", {
            "accountId": account_id,
            "onlyOpen":  only_open,
        })
        return resp if isinstance(resp, list) else resp.get("orders", [])

    # ── Positions ─────────────────────────────────────────────────────────

    def get_positions(self, account_id: int) -> list[dict]:
        """POST /api/Position/searchOpen -- posiciones ABIERTAS.

        Endpoint y forma VERIFICADOS en vivo el 4-oct-2026: {"positions": [{"id", "accountId", "contractId",
        "contractDisplayName", "creationTimestamp", "type", "size", "averagePrice"}], "success": true}.
        (Antes se llamaba /api/Position/search, que nunca se verifico, y se leia `netPos`, que NO existe.)"""
        self.ensure_auth()
        resp = self._post("/api/Position/searchOpen", {
            "accountId": account_id
        })
        return resp if isinstance(resp, list) else resp.get("positions", [])

    def is_flat(self, account_id: int) -> bool:
        return not any(position_is_open(p) for p in self.get_positions(account_id))

    # ── Market data ───────────────────────────────────────────────────────

    def get_bars(
        self,
        contract_id: str,
        bar_type:    int = 1,      # 1 = minute
        bar_size:    int = 1,
        count:       int = 50,
        live:        bool = False,
    ) -> list[dict]:
        """
        POST /api/History/retrieveBars
        Rate limit: 50 req / 30 sec
        """
        self.ensure_auth()
        resp = self._post("/api/History/retrieveBars", {
            "contractId": contract_id,
            "live":       live,
            "barType":    bar_type,
            "barTypeSize": bar_size,
            "unit":       count,
        })
        return resp if isinstance(resp, list) else resp.get("bars", [])

    # ── Glitch-specific helpers ───────────────────────────────────────────

    def execute_orb_bracket(
        self,
        account_id:  int,
        contract_id: str,
        direction:   int,    # +1 long, -1 short
        size:        int,
        tp_price:    float,
        sl_price:    float,
    ) -> dict:
        """
        Execute ORB trade as separate orders:
        1. Market entry
        2. Limit TP
        3. Stop SL

        Note: ProjectX API doesn't have native OSO brackets.
        We place entry + TP + SL as separate orders.
        The monitor loop cancels the other when one fills.
        """
        entry_side = OrderSide.ASK if direction == 1 else OrderSide.BID
        exit_side  = OrderSide.BID if direction == 1 else OrderSide.ASK

        # 1. Entry
        entry_id = self.place_market_order(
            account_id, contract_id, entry_side, size
        )

        # 2. TP (limit)
        tp_id = self.place_limit_order(
            account_id, contract_id, exit_side, size, tp_price
        )

        # 3. SL (stop)
        sl_id = self.place_stop_order(
            account_id, contract_id, exit_side, size, sl_price
        )

        return {
            "entry_order_id": entry_id,
            "tp_order_id":    tp_id,
            "sl_order_id":    sl_id,
        }

    def cancel_exit_orders(self, tp_id: int, sl_id: int):
        """Cancel TP and SL after one of them fills."""
        for oid in [tp_id, sl_id]:
            try:
                self.cancel_order(oid)
            except:
                pass

    def check_combine_limits(
        self,
        account_id:   int,
        account_size: float = 50_000,
        mll_distance: float = 2_000,
        dll_limit:    float = 1_000,
    ) -> tuple[bool, str]:
        """
        Verify account is within Topstep constraints before trading.
        Returns (ok, message).
        """
        try:
            balance_info = self.get_account_balance(account_id)
            equity = balance_info.get("totalEquity",
                     balance_info.get("balance", account_size))
            daily_pnl = balance_info.get("dailyPnL",
                        balance_info.get("realizedPnL", 0))

            floor  = account_size - mll_distance
            buffer = equity - floor

            if equity <= floor:
                return False, f"BLOWN: equity ${equity:.0f} ≤ floor ${floor:.0f}"
            if daily_pnl <= -dll_limit:
                return False, f"DLL: daily PnL ${daily_pnl:.0f}"
            if buffer < 300:
                return False, f"Thin buffer: ${buffer:.0f}"

            return True, f"OK equity=${equity:.0f} buffer=${buffer:.0f}"
        except Exception as e:
            return False, f"API error: {e}"

    def flatten_position(self, account_id: int, symbol: str) -> dict:
        """
        BUGFIX (11-ago-2026): este metodo no existia pero run_glitch.py,
        run_glitch_xfa.py y core/safety.py (FlattenFailsafe) lo llaman --
        el flatten de fin de dia habria tronado con AttributeError.
        No hay endpoint nativo documentado de 'liquidate' en ProjectX;
        se implementa como orden de mercado en direccion contraria a la
        posicion neta actual. Ajustar si ProjectX expone un endpoint dedicado.
        """
        self.ensure_auth()
        positions = self.get_positions(account_id)
        results = []
        for p in positions:
            net = p.get("netPos", 0)
            if net == 0:
                continue
            side = OrderSide.BID if net > 0 else OrderSide.ASK
            oid = self.place_market_order(account_id, p.get("contractId", symbol), side, abs(net))
            results.append(oid)
        return {"flattened_orders": results}

    def close_contract(self, account_id: int, contract_id) -> dict:
        """
        POST /api/Position/closeContract {accountId, contractId} -- cierra la posicion de ESE
        contrato en el broker (03-oct-2026). A diferencia de flatten_position(), NO decide un lado
        de compra/venta: no usa OrderSide (enum sin verificar, bloqueante #1) ni lee `netPos`.
        Lanza RuntimeError si la respuesta no trae success=True -- fallar ruidosamente es
        preferible a creer que se cerro una posicion que sigue abierta. El endpoint viene de la
        documentacion oficial de ProjectX (gateway.docs.projectx.com) y todavia no se ha
        confirmado contra una cuenta real: pi/verify_orderside_demo.py lo ejercita en la
        cuenta Practice y deja la respuesta cruda en su log.
        """
        self.ensure_auth()
        resp = self._post("/api/Position/closeContract", {"accountId": account_id, "contractId": contract_id})
        if not (isinstance(resp, dict) and resp.get("success", False)):
            err = resp.get("errorMessage") if isinstance(resp, dict) else resp
            raise RuntimeError(f"closeContract fallo: {err}")
        return resp

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _post(self, path: str, body: dict, auth: bool = True) -> Any:
        url = BASE_URL + path
        if not auth:
            resp = requests.post(
                url, json=body,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        else:
            resp = self._session.post(url, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> Any:
        url  = BASE_URL + path
        resp = self._session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
