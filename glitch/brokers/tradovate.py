"""
Glitch — Tradovate Broker Adapter
===================================
Conecta el motor de Glitch a la API de Tradovate.

ENDPOINTS:
  Demo:  https://demo.tradovateapi.com/v1
  Live:  https://live.tradovateapi.com/v1
  MD WS: wss://md.tradovateapi.com/v1/websocket
  Live WS: wss://live.tradovateapi.com/v1/websocket

AUTH FLOW:
  1. POST /auth/accessTokenRequest → accessToken + expirationTime
  2. Incluir Bearer token en cada request
  3. Renovar 5 min antes de expiración

CREDENCIALES NECESARIAS:
  - name:       tu email de Topstep/Tradovate
  - password:   tu password
  - appId:      "Sample App" (demo) o tu app registrada
  - appVersion: "1.0"
  - cid:        tu client ID (de Tradovate developer portal)
  - sec:        tu client secret

PARA TOPSTEP:
  Topstep usa Tradovate como broker backend.
  Las credenciales son las de tu cuenta Topstep.
  El accountId del Combine aparece en /account/list
"""

from __future__ import annotations
import os
import json
import time
import asyncio
import threading
import requests
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


# ── Config ─────────────────────────────────────────────────────────────────

DEMO_REST  = "https://demo.tradovateapi.com/v1"
LIVE_REST  = "https://live.tradovateapi.com/v1"
DEMO_WS    = "wss://demo.tradovateapi.com/v1/websocket"
LIVE_WS    = "wss://live.tradovateapi.com/v1/websocket"
MD_WS      = "wss://md.tradovateapi.com/v1/websocket"


class TradovateEnv(Enum):
    DEMO = "demo"
    LIVE = "live"


@dataclass
class TradovateCredentials:
    name:        str   # email
    password:    str
    app_id:      str   = "Sample App"
    app_version: str   = "1.0"
    cid:         int   = 8      # Tradovate Sample App (public demo)
    sec:         str   = "f03741b6-f634-48d6-9308-c8fb871150c2"  # Sample App secret
    device_id:   str   = "9818ba62-27d2-418f-837e-14af70314cad"  # this machine

    @classmethod
    def from_env(cls) -> "TradovateCredentials":
        """Load from environment variables."""
        return cls(
            name        = os.environ["TRADOVATE_NAME"],
            password    = os.environ["TRADOVATE_PASSWORD"],
            app_id      = os.environ.get("TRADOVATE_APP_ID", "Sample App"),
            app_version = os.environ.get("TRADOVATE_APP_VERSION", "1.0"),
            cid         = int(os.environ.get("TRADOVATE_CID", "0")),
            sec         = os.environ.get("TRADOVATE_SEC", ""),
        )

    @classmethod
    def from_file(cls, path: str = ".tradovate_creds.json") -> "TradovateCredentials":
        with open(path) as f:
            d = json.load(f)
        return cls(**d)


# ── Token management ────────────────────────────────────────────────────────

@dataclass
class AccessToken:
    token:           str
    expiration_time: datetime
    user_id:         int
    account_id:      Optional[int] = None

    @property
    def is_valid(self) -> bool:
        buffer = 5 * 60  # 5 min buffer
        return time.time() < self.expiration_time.timestamp() - buffer

    @property
    def seconds_until_expiry(self) -> float:
        return self.expiration_time.timestamp() - time.time()


# ── Order types ─────────────────────────────────────────────────────────────

@dataclass
class OrderRequest:
    account_id:   int
    symbol:       str          # e.g. "MESM5" (MES June 2025)
    action:       str          # "Buy" or "Sell"
    order_qty:    int          # number of contracts
    order_type:   str          # "Market", "Limit", "Stop", "StopLimit"
    price:        Optional[float] = None   # for Limit orders
    stop_price:   Optional[float] = None   # for Stop orders
    time_in_force: str = "Day"             # "Day", "GTC", "IOC", "FOK"
    text:         str = "Glitch"           # order tag

    def to_dict(self) -> dict:
        d = {
            "accountSpec":    str(self.account_id),
            "accountId":      self.account_id,
            "action":         self.action,
            "symbol":         self.symbol,
            "orderQty":       self.order_qty,
            "orderType":      self.order_type,
            "timeInForce":    self.time_in_force,
            "text":           self.text,
            "isAutomated":    True,
        }
        if self.price is not None:
            d["price"] = self.price
        if self.stop_price is not None:
            d["stopPrice"] = self.stop_price
        return d


@dataclass
class BracketOrder:
    """Entry + TP + SL as a single bracket."""
    account_id:  int
    symbol:      str
    action:      str          # "Buy" or "Sell"
    qty:         int
    entry_price: Optional[float]  # None = Market
    tp_price:    float
    sl_price:    float
    time_in_force: str = "Day"

    def exit_action(self) -> str:
        return "Sell" if self.action == "Buy" else "Buy"


# ── Position & Account state ────────────────────────────────────────────────

@dataclass
class Position:
    account_id:   int
    contract_id:  int
    symbol:       str
    net_pos:      int        # positive = long, negative = short
    avg_price:    float
    realized_pnl: float
    open_pnl:     float

    @property
    def is_flat(self) -> bool:
        return self.net_pos == 0


@dataclass
class AccountSummary:
    account_id:    int
    name:          str
    balance:       float
    realized_pnl:  float
    open_pnl:      float
    total_equity:  float
    margin_used:   float

    @property
    def available_margin(self) -> float:
        return self.total_equity - self.margin_used


# ── Main broker client ──────────────────────────────────────────────────────

class TradovateClient:
    """
    Tradovate REST + WebSocket client for Glitch.

    Usage:
        creds  = TradovateCredentials.from_env()
        client = TradovateClient(creds, env=TradovateEnv.DEMO)
        client.authenticate()

        # Get accounts
        accounts = client.get_accounts()

        # Place market order
        order = OrderRequest(
            account_id=accounts[0]['id'],
            symbol="MESM5",
            action="Buy",
            order_qty=3,
            order_type="Market",
        )
        result = client.place_order(order)

        # Place bracket (entry + TP + SL)
        client.place_bracket(BracketOrder(...))
    """

    def __init__(
        self,
        credentials: TradovateCredentials,
        env: TradovateEnv = TradovateEnv.DEMO,
        verbose: bool = True,
    ):
        self.creds   = credentials
        self.env     = env
        self.verbose = verbose
        self.base    = DEMO_REST if env == TradovateEnv.DEMO else LIVE_REST
        self._token: Optional[AccessToken] = None
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Auth ──────────────────────────────────────────────────────────────

    def authenticate(self) -> AccessToken:
        """
        POST /auth/accessTokenRequest
        Returns AccessToken and stores it for subsequent requests.
        """
        payload = {
            "name":       self.creds.name,
            "password":   self.creds.password,
            "appId":      self.creds.app_id,
            "appVersion": self.creds.app_version,
            "deviceId":   self.creds.device_id,
            "cid":        self.creds.cid,
            "sec":        self.creds.sec,
        }

        resp = self._post("/auth/accessTokenRequest", payload, auth=False)

        exp = datetime.fromisoformat(
            resp["expirationTime"].replace("Z", "+00:00")
        )
        self._token = AccessToken(
            token           = resp["accessToken"],
            expiration_time = exp,
            user_id         = resp.get("userId", 0),
        )
        self._session.headers["Authorization"] = f"Bearer {self._token.token}"

        if self.verbose:
            print(f"[Tradovate] Authenticated as {resp.get('name', '?')} "
                  f"(expires in {self._token.seconds_until_expiry/60:.0f} min)")
        return self._token

    def ensure_auth(self):
        """Re-authenticate if token is missing or expired."""
        if self._token is None or not self._token.is_valid:
            self.authenticate()

    # ── Account ───────────────────────────────────────────────────────────

    def get_accounts(self) -> list[dict]:
        """GET /account/list — returns all accounts."""
        self.ensure_auth()
        return self._get("/account/list")

    def get_account_summary(self, account_id: int) -> AccountSummary:
        """GET /cashBalance/getcashbalancesnapshot — P&L snapshot."""
        self.ensure_auth()
        resp = self._get(f"/cashBalance/getcashbalancesnapshot?accountId={account_id}")
        return AccountSummary(
            account_id   = account_id,
            name         = str(account_id),
            balance      = resp.get("totalCashValue", 0),
            realized_pnl = resp.get("realizedPnL", 0),
            open_pnl     = resp.get("openPnL", 0),
            total_equity = resp.get("totalCashValue", 0),
            margin_used  = resp.get("initialMargin", 0),
        )

    def get_positions(self, account_id: int) -> list[Position]:
        """GET /position/list — open positions."""
        self.ensure_auth()
        raw = self._get(f"/position/ldeps?masterids={account_id}")
        positions = []
        for p in raw:
            if p.get("netPos", 0) != 0:
                positions.append(Position(
                    account_id   = account_id,
                    contract_id  = p.get("contractId", 0),
                    symbol       = "",   # resolve via contract lookup
                    net_pos      = p["netPos"],
                    avg_price    = p.get("avgPrice", 0),
                    realized_pnl = p.get("realizedPnL", 0),
                    open_pnl     = p.get("openPnL", 0),
                ))
        return positions

    # ── Contracts ─────────────────────────────────────────────────────────

    def find_contract(self, symbol: str) -> dict:
        """
        GET /contract/find — find contract by symbol.
        For MES continuous front month: symbol = "MESM5" (June 2025)
        Check https://www.cmegroup.com for current front month code.
        """
        self.ensure_auth()
        return self._get(f"/contract/find?name={symbol}")

    def get_contract_id(self, symbol: str) -> int:
        """Returns the contractId for a symbol."""
        contract = self.find_contract(symbol)
        return contract["id"]

    # ── Orders ────────────────────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> dict:
        """
        POST /order/placeorder
        Returns order confirmation with orderId.
        """
        self.ensure_auth()
        resp = self._post("/order/placeorder", order.to_dict())
        if self.verbose:
            print(f"[Tradovate] Order placed: {order.action} {order.order_qty} "
                  f"{order.symbol} @ {order.order_type} → orderId={resp.get('orderId')}")
        return resp

    def place_market_order(
        self, account_id: int, symbol: str,
        action: str, qty: int
    ) -> dict:
        """Convenience: place a market order."""
        return self.place_order(OrderRequest(
            account_id=account_id, symbol=symbol,
            action=action, order_qty=qty, order_type="Market"
        ))

    def place_bracket(self, bracket: BracketOrder) -> dict:
        """
        Place entry + TP + SL as OSO (Order Sends Order) bracket.
        Tradovate supports OSO via /order/placeoso endpoint.
        Entry fills → automatically places TP and SL.
        """
        self.ensure_auth()
        entry_type = "Market" if bracket.entry_price is None else "Limit"
        payload = {
            "accountSpec":  str(bracket.account_id),
            "accountId":    bracket.account_id,
            "action":       bracket.action,
            "symbol":       bracket.symbol,
            "orderQty":     bracket.qty,
            "orderType":    entry_type,
            "timeInForce":  bracket.time_in_force,
            "isAutomated":  True,
            "text":         "Glitch-Entry",
            "bracket1": {   # Take profit
                "action":    bracket.exit_action(),
                "orderType": "Limit",
                "price":     bracket.tp_price,
                "text":      "Glitch-TP",
            },
            "bracket2": {   # Stop loss
                "action":    bracket.exit_action(),
                "orderType": "Stop",
                "stopPrice": bracket.sl_price,
                "text":      "Glitch-SL",
            },
        }
        if bracket.entry_price:
            payload["price"] = bracket.entry_price

        resp = self._post("/order/placeoso", payload)
        if self.verbose:
            print(f"[Tradovate] Bracket placed: {bracket.action} {bracket.qty} "
                  f"{bracket.symbol} | TP={bracket.tp_price} SL={bracket.sl_price}")
        return resp

    def cancel_order(self, order_id: int) -> dict:
        """POST /order/cancelorder"""
        self.ensure_auth()
        return self._post("/order/cancelorder", {"orderId": order_id})

    def cancel_all_orders(self, account_id: int) -> dict:
        """POST /order/cancelallorders"""
        self.ensure_auth()
        return self._post("/order/cancelallorders", {"accountId": account_id})

    def flatten_position(self, account_id: int, symbol: str) -> dict:
        """
        Close all open positions for a symbol.
        Uses /order/liquidateposition endpoint.
        """
        self.ensure_auth()
        return self._post("/order/liquidateposition", {
            "accountId": account_id,
            "contractId": self.get_contract_id(symbol),
            "admin": False,
        })

    # ── Orders status ─────────────────────────────────────────────────────

    def get_orders(self, account_id: int) -> list[dict]:
        """GET /order/list — all orders for account."""
        self.ensure_auth()
        return self._get(f"/order/ldeps?masterids={account_id}")

    def get_fills(self, account_id: int) -> list[dict]:
        """GET /fill/list — executed fills."""
        self.ensure_auth()
        return self._get(f"/fill/ldeps?masterids={account_id}")

    # ── Risk / Account state check ────────────────────────────────────────

    def check_combine_status(self, account_id: int) -> dict:
        """
        Returns current P&L vs Topstep limits.
        Use before every trade to ensure we're within constraints.
        """
        self.ensure_auth()
        summary = self.get_account_summary(account_id)
        return {
            "balance":       summary.balance,
            "open_pnl":      summary.open_pnl,
            "total_equity":  summary.total_equity,
            "realized_pnl":  summary.realized_pnl,
        }

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _get(self, path: str) -> Any:
        url  = self.base + path
        resp = self._session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict, auth: bool = True) -> Any:
        url     = self.base + path
        headers = {}
        if not auth:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, json=body, headers=headers, timeout=10)
        else:
            resp = self._session.post(url, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()


# ── MES symbol helper ───────────────────────────────────────────────────────

def current_mes_symbol() -> str:
    """
    Returns the current front-month MES contract symbol.
    MES rolls quarterly: March (H), June (M), September (U), December (Z)
    Format: MES + month_code + year_last_2_digits
    e.g. MESM5 = MES June 2025, MESU5 = MES September 2025
    """
    now = datetime.now(timezone.utc)
    y   = now.year % 100
    m   = now.month

    # Front month rolls ~2 weeks before expiration (3rd Friday of month)
    # Conservative: roll on 1st of expiration month
    if m <= 2:   return f"MESH{y}"   # March
    elif m <= 5: return f"MESM{y}"   # June
    elif m <= 8: return f"MESU{y}"   # September
    elif m <= 11:return f"MESZ{y}"   # December
    else:        return f"MESH{y+1}" # March next year


# ── Glitch execution engine ─────────────────────────────────────────────────

class GlitchExecutor:
    """
    Connects the ORB strategy signals to Tradovate execution.

    Full pipeline:
      1. Check regime filter (prev day range)
      2. Wait for ORB signal (9:35 AM CT)
      3. Check account status vs Topstep limits
      4. Place bracket order (entry + TP + SL)
      5. Monitor until exit or 2:30 PM CT
      6. Flatten any remaining position at 3:00 PM CT
      7. Log results

    Usage:
        creds    = TradovateCredentials.from_env()
        executor = GlitchExecutor(creds, account_id=12345, env=TradovateEnv.DEMO)
        executor.run_trading_day()
    """

    def __init__(
        self,
        credentials:  TradovateCredentials,
        account_id:   int,
        n_contracts:  int  = 3,
        tp_pts:       float = 6.0,
        sl_pts:       float = 3.0,
        env:          TradovateEnv = TradovateEnv.DEMO,
        verbose:      bool = True,
    ):
        self.client      = TradovateClient(credentials, env, verbose)
        self.account_id  = account_id
        self.n_contracts = n_contracts
        self.tp_pts      = tp_pts
        self.sl_pts      = sl_pts
        self.symbol      = current_mes_symbol()
        self.verbose     = verbose

        # MES tick = 0.25 pts
        self.tick_size   = 0.25

    def round_to_tick(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, 2)

    def check_pre_trade_conditions(self) -> tuple[bool, str]:
        """
        Verify all Topstep conditions before placing any trade.
        Returns (ok, reason).
        """
        try:
            status = self.client.check_combine_status(self.account_id)
            equity = status["total_equity"]

            # Hard limits from TOPSTEP_50K spec
            ACCOUNT_SIZE  = 50_000
            MLL_DISTANCE  = 2_000
            DLL_LIMIT     = 1_000
            FLOOR         = ACCOUNT_SIZE - MLL_DISTANCE   # $48,000 min

            if equity <= FLOOR:
                return False, f"BLOWN: equity ${equity:.0f} <= floor ${FLOOR:.0f}"

            daily_pnl = status["realized_pnl"] + status["open_pnl"]
            if daily_pnl <= -DLL_LIMIT:
                return False, f"DLL hit: daily PnL ${daily_pnl:.0f}"

            # Remaining buffer check: don't trade if < $300 buffer
            buffer = equity - FLOOR
            if buffer < 300:
                return False, f"Buffer too thin: ${buffer:.0f} remaining"

            return True, "OK"
        except Exception as e:
            return False, f"API error: {e}"

    def execute_orb_signal(
        self,
        direction:   int,    # +1 long, -1 short
        entry_price: float,
    ) -> dict:
        """
        Execute one ORB trade as a bracket order.
        direction: +1 = long, -1 = short
        """
        action     = "Buy"  if direction == 1 else "Sell"
        tp_price   = self.round_to_tick(entry_price + direction * self.tp_pts)
        sl_price   = self.round_to_tick(entry_price - direction * self.sl_pts)

        ok, reason = self.check_pre_trade_conditions()
        if not ok:
            if self.verbose:
                print(f"[Glitch] Trade blocked: {reason}")
            return {"status": "blocked", "reason": reason}

        bracket = BracketOrder(
            account_id  = self.account_id,
            symbol      = self.symbol,
            action      = action,
            qty         = self.n_contracts,
            entry_price = None,   # Market entry
            tp_price    = tp_price,
            sl_price    = sl_price,
        )

        if self.verbose:
            print(f"[Glitch] Executing {action} {self.n_contracts}x {self.symbol} "
                  f"| TP={tp_price} SL={sl_price}")

        return self.client.place_bracket(bracket)

    def flatten_all(self) -> dict:
        """Emergency flatten — close all positions. Call at 3:00 PM CT."""
        if self.verbose:
            print(f"[Glitch] Flattening all positions in {self.symbol}")
        positions = self.client.get_positions(self.account_id)
        results   = []
        for pos in positions:
            if not pos.is_flat:
                r = self.client.flatten_position(self.account_id, self.symbol)
                results.append(r)
        return {"flattened": len(results), "results": results}

    def daily_summary(self) -> dict:
        """Print and return end-of-day summary."""
        status = self.client.check_combine_status(self.account_id)
        fills  = self.client.get_fills(self.account_id)

        if self.verbose:
            print(f"\n[Glitch] EOD Summary:")
            print(f"  Balance:     ${status['balance']:,.2f}")
            print(f"  Realized PnL: ${status['realized_pnl']:+,.2f}")
            print(f"  Open PnL:    ${status['open_pnl']:+,.2f}")
            print(f"  Fills today: {len(fills)}")

        return {**status, "fills_today": len(fills)}
