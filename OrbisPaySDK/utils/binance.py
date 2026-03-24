"""
Binance API v3 client — market data + authenticated spot trading.

Public endpoints require no credentials.
Authenticated endpoints need *api_key* + *api_secret*.

Example::

    from OrbisPaySDK.utils.binance import Binance

    bn = Binance()                                         # public only
    price  = await bn.get_price("BTCUSDT")
    klines = await bn.get_klines("ETHUSDT", "1h")

    bn = Binance(api_key="…", api_secret="…")              # authenticated
    bal   = await bn.get_account()
    order = await bn.place_order("BTCUSDT", "BUY", "LIMIT",
                                  quantity="0.001", price="60000",
                                  time_in_force="GTC")
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from OrbisPaySDK.utils.utils import _BaseProvider


class Binance(_BaseProvider):
    """Binance Spot API v3 wrapper."""

    SYMBOL_MAP: Dict[str, str] = {
        "btc": "BTCUSDT", "bitcoin": "BTCUSDT",
        "eth": "ETHUSDT", "ethereum": "ETHUSDT",
        "bnb": "BNBUSDT", "binancecoin": "BNBUSDT",
        "sol": "SOLUSDT", "solana": "SOLUSDT",
        "trx": "TRXUSDT", "tron": "TRXUSDT",
        "ton": "TONUSDT", "the-open-network": "TONUSDT",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
    ):
        base = (
            "https://testnet.binance.vision"
            if testnet
            else "https://api.binance.com"
        )
        headers: dict = {}
        if api_key:
            headers["X-MBX-APIKEY"] = api_key
        super().__init__(base, headers)
        self._api_key = api_key
        self._api_secret = api_secret

    # ------------------------------------------------------------------ auth
    def _sign_params(self, params: dict) -> dict:
        """Add ``timestamp`` + HMAC-SHA256 ``signature`` to *params*."""
        if not self._api_key or not self._api_secret:
            raise RuntimeError("Binance API key/secret required for this endpoint")
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        qs = urlencode(sorted(params.items()))
        sig = hmac.new(
            self._api_secret.encode(), qs.encode(), hashlib.sha256,
        ).hexdigest()
        params["signature"] = sig
        return params

    async def _auth_get(self, path: str, params: Optional[dict] = None) -> Any:
        signed = self._sign_params(params or {})
        return await self._get(path, params=signed)

    async def _auth_post(self, path: str, params: Optional[dict] = None) -> Any:
        signed = self._sign_params(params or {})
        import httpx, asyncio as _aio

        url = f"{self._base_url}{path}"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, params=signed, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
        return None

    async def _auth_delete(self, path: str, params: Optional[dict] = None) -> Any:
        signed = self._sign_params(params or {})
        import httpx, asyncio as _aio

        url = f"{self._base_url}{path}"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.delete(url, params=signed, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
        return None

    def _sym(self, symbol: str) -> str:
        return self.SYMBOL_MAP.get(symbol.lower(), symbol.upper())

    # ============================== PUBLIC: MARKET DATA ==============================

    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """
        Get 24h ticker statistics.

        Args:
            symbol: Trading pair (``BTCUSDT``) or alias (``btc``).

        Returns:
            Dict with ``lastPrice``, ``highPrice``, ``lowPrice``,
            ``volume``, ``priceChangePercent``, etc.
        """
        sym = self._sym(symbol)
        return await self._get("/api/v3/ticker/24hr", params={"symbol": sym})

    async def get_price(self, symbol: str) -> float:
        """Get latest price for a symbol as float."""
        sym = self._sym(symbol)
        data = await self._get("/api/v3/ticker/price", params={"symbol": sym})
        if data and data.get("price"):
            return float(data["price"])
        return 0.0

    async def get_prices(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Get prices for multiple symbols.

        Args:
            symbols: List of aliases / pairs.  ``None`` → default set
                     (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, ...}``
        """
        if symbols is None:
            symbols = ["btc", "eth", "bnb", "sol", "trx", "ton"]

        # Fetch all tickers in one call
        all_tickers = await self._get("/api/v3/ticker/price")
        if not all_tickers:
            return {s.lower(): 0.0 for s in symbols}

        ticker_map = {t["symbol"]: float(t["price"]) for t in all_tickers}
        result: Dict[str, float] = {}
        for s in symbols:
            sym = self._sym(s)
            result[s.lower()] = ticker_map.get(sym, 0.0)
        return result

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[list]:
        """
        Get kline / candlestick bars.

        Args:
            symbol: Trading pair or alias.
            interval: ``1s`` ``1m`` ``3m`` ``5m`` ``15m`` ``30m``
                      ``1h`` ``2h`` ``4h`` ``6h`` ``8h`` ``12h``
                      ``1d`` ``3d`` ``1w`` ``1M``.
            limit: 1–1000 (default 500).
            start_time: Start time in ms.
            end_time: End time in ms.

        Returns:
            List of ``[openTime, open, high, low, close, volume, closeTime,
            quoteAssetVolume, numberOfTrades, …]``.
        """
        sym = self._sym(symbol)
        params: dict = {"symbol": sym, "interval": interval, "limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._get("/api/v3/klines", params=params)
        return data if isinstance(data, list) else []

    async def get_orderbook(
        self,
        symbol: str,
        limit: int = 100,
    ) -> Optional[dict]:
        """
        Get order book depth.

        Args:
            symbol: Trading pair or alias.
            limit: 5 | 10 | 20 | 50 | 100 | 500 | 1000 | 5000 (default 100).

        Returns:
            Dict with ``bids`` and ``asks`` lists of ``[price, qty]``.
        """
        sym = self._sym(symbol)
        return await self._get(
            "/api/v3/depth",
            params={"symbol": sym, "limit": limit},
        )

    async def get_recent_trades(
        self,
        symbol: str,
        limit: int = 500,
    ) -> List[dict]:
        """
        Get recent trades.

        Args:
            symbol: Trading pair or alias.
            limit: 1–1000 (default 500).
        """
        sym = self._sym(symbol)
        data = await self._get(
            "/api/v3/trades",
            params={"symbol": sym, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def get_avg_price(self, symbol: str) -> float:
        """Get current average price for a symbol."""
        sym = self._sym(symbol)
        data = await self._get("/api/v3/avgPrice", params={"symbol": sym})
        if data and data.get("price"):
            return float(data["price"])
        return 0.0

    async def get_exchange_info(
        self,
        symbol: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get exchange trading rules and symbol information.

        Args:
            symbol: Optional specific symbol.
        """
        params: dict = {}
        if symbol:
            params["symbol"] = self._sym(symbol)
        return await self._get("/api/v3/exchangeInfo", params=params)

    async def get_server_time(self) -> Optional[int]:
        """Get Binance server time in milliseconds."""
        data = await self._get("/api/v3/time")
        if data:
            return data.get("serverTime")
        return None

    # ============================== PRIVATE: ACCOUNT ==============================

    async def get_account(self) -> Optional[dict]:
        """
        Get current account information (requires auth).

        Returns:
            Account dict with ``balances``, ``permissions``, etc.
        """
        return await self._auth_get("/api/v3/account")

    async def get_balance(self, asset: str) -> float:
        """Convenience: get free balance for a single asset."""
        account = await self.get_account()
        if not account:
            return 0.0
        for b in account.get("balances", []):
            if b.get("asset", "").upper() == asset.upper():
                return float(b.get("free", 0))
        return 0.0

    # ============================== PRIVATE: TRADING ==============================

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[str] = None,
        quote_order_qty: Optional[str] = None,
        price: Optional[str] = None,
        time_in_force: Optional[str] = None,
        **kwargs,
    ) -> Optional[dict]:
        """
        Place a new order (requires auth).

        Args:
            symbol: Trading pair or alias.
            side: ``BUY`` | ``SELL``.
            order_type: ``LIMIT`` | ``MARKET`` | ``STOP_LOSS`` |
                        ``STOP_LOSS_LIMIT`` | ``TAKE_PROFIT`` |
                        ``TAKE_PROFIT_LIMIT`` | ``LIMIT_MAKER``.
            quantity: Order quantity (required for most types).
            quote_order_qty: Spend amount in quote asset (``MARKET`` only).
            price: Limit price (required for ``LIMIT``).
            time_in_force: ``GTC`` | ``IOC`` | ``FOK`` (required for ``LIMIT``).

        Returns:
            Order result dict with ``orderId``, ``status``, ``fills``, etc.
        """
        params: dict = {
            "symbol": self._sym(symbol),
            "side": side.upper(),
            "type": order_type.upper(),
            **kwargs,
        }
        if quantity:
            params["quantity"] = quantity
        if quote_order_qty:
            params["quoteOrderQty"] = quote_order_qty
        if price:
            params["price"] = price
        if time_in_force:
            params["timeInForce"] = time_in_force

        return await self._auth_post("/api/v3/order", params=params)

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Cancel an active order (requires auth).

        Provide either *order_id* or *orig_client_order_id*.
        """
        params: dict = {"symbol": self._sym(symbol)}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        return await self._auth_delete("/api/v3/order", params=params)

    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
    ) -> List[dict]:
        """Get all open orders (requires auth)."""
        params: dict = {}
        if symbol:
            params["symbol"] = self._sym(symbol)
        data = await self._auth_get("/api/v3/openOrders", params=params)
        return data if isinstance(data, list) else []

    async def get_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Query a specific order's status (requires auth).

        Provide either *order_id* or *orig_client_order_id*.
        """
        params: dict = {"symbol": self._sym(symbol)}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        return await self._auth_get("/api/v3/order", params=params)

    async def get_all_orders(
        self,
        symbol: str,
        limit: int = 500,
    ) -> List[dict]:
        """Get all orders — active, cancelled, filled (requires auth)."""
        params: dict = {"symbol": self._sym(symbol), "limit": limit}
        data = await self._auth_get("/api/v3/allOrders", params=params)
        return data if isinstance(data, list) else []

    async def get_my_trades(
        self,
        symbol: str,
        limit: int = 500,
    ) -> List[dict]:
        """Get account trade list for a symbol (requires auth)."""
        params: dict = {"symbol": self._sym(symbol), "limit": limit}
        data = await self._auth_get("/api/v3/myTrades", params=params)
        return data if isinstance(data, list) else []
