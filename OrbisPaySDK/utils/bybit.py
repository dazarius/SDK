"""
Bybit API v5 client — market data + authenticated trading.

Public endpoints require no credentials.
Authenticated endpoints (account, trading) need *api_key* + *api_secret*.

Example::

    from OrbisPaySDK.utils.bybit import Bybit

    bb = Bybit()                                       # public only
    ticker = await bb.get_ticker("BTCUSDT")
    klines = await bb.get_klines("ETHUSDT", "1h")

    bb = Bybit(api_key="…", api_secret="…")            # authenticated
    bal   = await bb.get_wallet_balance()
    order = await bb.place_order("BTCUSDT", "Buy", "Limit", qty="0.001", price="60000")
"""

from __future__ import annotations

import hashlib
import hmac
import time
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from OrbisPaySDK.utils.utils import _BaseProvider


class Bybit(_BaseProvider):
    """Bybit API v5 wrapper (spot / linear / inverse)."""

    # -- helpers for symbol normalization --
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
            "https://api-testnet.bybit.com"
            if testnet
            else "https://api.bybit.com"
        )
        super().__init__(base)
        self._api_key = api_key
        self._api_secret = api_secret

    # ------------------------------------------------------------------ auth

    async def _auth_request(self,method: str,path: str,params: Optional[dict] = None, body: Optional[dict] = None,) -> Any:
        if not self._api_key or not self._api_secret:
            raise RuntimeError("Bybit API key/secret required for this endpoint")

        from urllib.parse import urlencode
        import httpx, asyncio as _aio

        ts = str(int(time.time() * 1000))
        recv_window = "5000"

        # Build the payload string that goes into the HMAC signature.
        # For GET — the exact query string; for POST — the raw JSON body.
        if method == "GET" and params:
            payload_str = urlencode(params)          # keep dict insertion order
        elif body:
            payload_str = json.dumps(body, separators=(",", ":"))
        else:
            payload_str = ""

        raw = f"{ts}{self._api_key}{recv_window}{payload_str}"
        sign = hmac.new(
            self._api_secret.encode(), raw.encode(), hashlib.sha256,
        ).hexdigest()

        headers = {
            **self._headers,
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-SIGN": sign,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }

        url = f"{self._base_url}{path}"
        # For GET: append query string to URL manually so the signature
        # matches the exact bytes that Bybit sees.
        if method == "GET" and payload_str:
            url = f"{url}?{payload_str}"

        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                else:
                    resp = await client.post(
                        url, content=payload_str or "{}", headers=headers,
                    )

                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                data = resp.json()

                # Bybit returns HTTP 200 even on auth errors —
                # check retCode for the real status.
                ret_code = data.get("retCode", 0)
                if ret_code != 0:
                    ret_msg = data.get("retMsg", "unknown error")
                    raise RuntimeError(
                        f"Bybit API error (retCode={ret_code}): {ret_msg}"
                    )
                return data
        return None

    def _sym(self, symbol: str) -> str:
        """Resolve alias → Bybit symbol."""
        return self.SYMBOL_MAP.get(symbol.lower(), symbol.upper())

    # ============================== PUBLIC: MARKET DATA ==============================

    async def get_ticker(self, symbol: str, category: str = "spot") -> Optional[dict]:
        """
        Get latest price ticker for a symbol.

        Args:
            symbol: Trading pair (``BTCUSDT``) or alias (``btc``).
            category: ``spot`` | ``linear`` | ``inverse``.

        Returns:
            Ticker dict with ``lastPrice``, ``highPrice24h``, ``lowPrice24h``,
            ``turnover24h``, ``volume24h``, etc.
        """
        sym = self._sym(symbol)
        data = await self._get(
            "/v5/market/tickers",
            params={"category": category, "symbol": sym},
        )
        if not data:
            return None
        items = (data.get("result") or {}).get("list", [])
        return items[0] if items else None

    async def get_tickers(self, category: str = "spot") -> List[dict]:
        """Get all tickers for a category."""
        data = await self._get(
            "/v5/market/tickers",
            params={"category": category},
        )
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    async def get_price(self, symbol: str, category: str = "spot") -> float:
        """Convenience: get last price as float."""
        t = await self.get_ticker(symbol, category)
        if t and t.get("lastPrice"):
            return float(t["lastPrice"])
        return 0.0

    async def get_prices(self,symbols: Optional[List[str]] = None,category: str = "spot") -> Dict[str, float]:
        """
        Get prices for multiple symbols at once.

        Args:
            symbols: List of aliases / pairs.  ``None`` → default set
                     (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).
            category: ``spot`` | ``linear`` | ``inverse``.

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, ...}``
        """
        if symbols is None:
            symbols = ["btc", "eth", "bnb", "sol", "trx", "ton"]

        # Fetch all tickers in one call and filter
        all_tickers = await self.get_tickers(category)
        ticker_map = {t["symbol"]: t for t in all_tickers}

        result: Dict[str, float] = {}
        for s in symbols:
            sym = self._sym(s)
            key = s.lower()
            t = ticker_map.get(sym)
            if t and t.get("lastPrice"):
                result[key] = float(t["lastPrice"])
            else:
                result[key] = 0.0
        return result

    async def get_klines(
        self,
        symbol: str,
        interval: str = "60",
        limit: int = 200,
        category: str = "spot",
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> List[list]:
        """
        Get kline / candlestick data.

        Args:
            symbol: Trading pair or alias.
            interval: ``1`` ``3`` ``5`` ``15`` ``30`` ``60`` ``120`` ``240``
                      ``360`` ``720`` ``D`` ``W`` ``M``.
            limit: Max candles (1–1000, default 200).
            category: ``spot`` | ``linear`` | ``inverse``.
            start: Start time in ms.
            end: End time in ms.

        Returns:
            List of ``[startTime, open, high, low, close, volume, turnover]``.
        """
        sym = self._sym(symbol)
        params: dict = {
            "category": category,
            "symbol": sym,
            "interval": interval,
            "limit": limit,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        data = await self._get("/v5/market/kline", params=params)
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    async def get_orderbook(
        self,
        symbol: str,
        limit: int = 25,
        category: str = "spot",
    ) -> Optional[dict]:
        """
        Get order book depth.

        Args:
            symbol: Trading pair or alias.
            limit: Depth (1–200, default 25).
            category: ``spot`` | ``linear`` | ``inverse``.

        Returns:
            Dict with ``b`` (bids) and ``a`` (asks) lists of ``[price, qty]``.
        """
        sym = self._sym(symbol)
        data = await self._get(
            "/v5/market/orderbook",
            params={"category": category, "symbol": sym, "limit": limit},
        )
        if not data:
            return None
        return data.get("result")

    async def get_recent_trades(
        self,
        symbol: str,
        limit: int = 60,
        category: str = "spot",
    ) -> List[dict]:
        """
        Get recent public trades.

        Args:
            symbol: Trading pair or alias.
            limit: 1–60 (default 60).
            category: ``spot`` | ``linear`` | ``inverse``.

        Returns:
            List of trade dicts with ``price``, ``size``, ``side``, ``time``.
        """
        sym = self._sym(symbol)
        data = await self._get(
            "/v5/market/recent-trade",
            params={"category": category, "symbol": sym, "limit": limit},
        )
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    async def get_instruments(
        self,
        symbol: Optional[str] = None,
        category: str = "spot",
    ) -> List[dict]:
        """
        Get instrument / trading pair information.

        Args:
            symbol: Optional specific symbol.
            category: ``spot`` | ``linear`` | ``inverse`` | ``option``.
        """
        params: dict = {"category": category}
        if symbol:
            params["symbol"] = self._sym(symbol)

        data = await self._get("/v5/market/instruments-info", params=params)
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    async def get_server_time(self) -> Optional[int]:
        """Get Bybit server time in milliseconds."""
        data = await self._get("/v5/market/time")
        if not data:
            return None
        return int((data.get("result") or {}).get("timeSecond", 0)) * 1000

    # ============================== PRIVATE: ACCOUNT ==============================

    async def get_wallet_balance(
        self,
        account_type: str = "UNIFIED",
        coin: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get wallet balance (requires auth).

        Args:
            account_type: ``UNIFIED`` | ``SPOT`` | ``CONTRACT`` | ``FUND``.
            coin: Optional coin filter (e.g. ``BTC``).
        """
        params: dict = {"accountType": account_type}
        if coin:
            params["coin"] = coin.upper()
        data = await self._auth_request("GET", "/v5/account/wallet-balance", params=params)
        if not data:
            return None
        items = (data.get("result") or {}).get("list", [])
        return items[0] if items else None

    async def get_coin_balance(self, coin: str, account_type: str = "UNIFIED") -> float:
        """Convenience: get available balance for a single coin."""
        wallet = await self.get_wallet_balance(account_type, coin)
        if not wallet:
            return 0.0
        for c in wallet.get("coin", []):
            if c.get("coin", "").upper() == coin.upper():
                return float(c.get("availableToWithdraw", 0))
        return 0.0

    # ============================== PRIVATE: TRADING ==============================

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: str,
        price: Optional[str] = None,
        category: str = "spot",
        time_in_force: str = "GTC",
        **kwargs,
    ) -> Optional[dict]:
        """
        Place a spot / linear / inverse order (requires auth).

        Args:
            symbol: Trading pair or alias.
            side: ``Buy`` | ``Sell``.
            order_type: ``Market`` | ``Limit``.
            qty: Order quantity as string.
            price: Limit price (required for ``Limit``).
            category: ``spot`` | ``linear`` | ``inverse``.
            time_in_force: ``GTC`` | ``IOC`` | ``FOK``.

        Returns:
            Order result dict with ``orderId``, ``orderLinkId``.
        """
        body: dict = {
            "category": category,
            "symbol": self._sym(symbol),
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": time_in_force,
            **kwargs,
        }
        if price is not None:
            body["price"] = price

        data = await self._auth_request("POST", "/v5/order/create", body=body)
        if not data:
            return None
        return data.get("result")

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        category: str = "spot",
    ) -> Optional[dict]:
        """
        Cancel an active order (requires auth).

        Provide either *order_id* or *order_link_id*.
        """
        body: dict = {
            "category": category,
            "symbol": self._sym(symbol),
        }
        if order_id:
            body["orderId"] = order_id
        if order_link_id:
            body["orderLinkId"] = order_link_id

        data = await self._auth_request("POST", "/v5/order/cancel", body=body)
        if not data:
            return None
        return data.get("result")

    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
        category: str = "spot",
        limit: int = 50,
    ) -> List[dict]:
        """
        Get open / unfilled orders (requires auth).

        Args:
            symbol: Optional filter by symbol.
            category: ``spot`` | ``linear`` | ``inverse``.
            limit: Max orders (1–50).
        """
        params: dict = {"category": category, "limit": limit}
        if symbol:
            params["symbol"] = self._sym(symbol)

        data = await self._auth_request("GET", "/v5/order/realtime", params=params)
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        category: str = "spot",
        limit: int = 50,
    ) -> List[dict]:
        """
        Get closed / filled order history (requires auth).

        Args:
            symbol: Optional filter by symbol.
            category: ``spot`` | ``linear`` | ``inverse``.
            limit: Max orders (1–50).
        """
        params: dict = {"category": category, "limit": limit}
        if symbol:
            params["symbol"] = self._sym(symbol)

        data = await self._auth_request("GET", "/v5/order/history", params=params)
        if not data:
            return []
        return (data.get("result") or {}).get("list", [])

    # ============================== PRIVATE: WITHDRAWALS ==============================

    async def get_withdrawal_addresses(
        self,
        coin: Optional[str] = None,
        chain: Optional[str] = None,
        address_type: Optional[int] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Get withdrawal addresses from address book (requires auth).

        Args:
            coin: Coin filter (e.g. ``USDT``). ``baseCoin`` → universal addresses.
            chain: Chain filter (e.g. ``ETH``, ``SOL``).
            address_type: ``0`` — on-chain, ``1`` — internal transfer,
                          ``2`` — both.
            limit: Page size (1–50, default 50).

        Returns:
            List of address dicts with ``coin``, ``chain``, ``address``,
            ``tag``, ``remark``, ``status``, ``verified``, etc.
        """
        params: dict = {"limit": limit}
        if coin:
            params["coin"] = coin.upper()
        if chain:
            params["chain"] = chain.upper()
        if address_type is not None:
            params["addressType"] = address_type

        all_rows: List[dict] = []
        cursor: Optional[str] = None

        while True:
            p = dict(params)
            if cursor:
                p["cursor"] = cursor
            data = await self._auth_request(
                "GET", "/v5/asset/withdraw/query-address", params=p,
            )
            if not data:
                break
            result = data.get("result") or {}
            rows = result.get("rows") or []
            all_rows.extend(rows)
            cursor = result.get("nextPageCursor")
            if not cursor or len(rows) < limit:
                break

        return all_rows

    async def get_withdrawal_records(
        self,
        coin: Optional[str] = None,
        withdraw_type: int = 2,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        withdraw_id: Optional[str] = None,
        tx_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Get withdrawal records — **auto-paginates** through all pages.

        Args:
            coin: Coin filter (e.g. ``USDT``).
            withdraw_type: ``0`` — on-chain, ``1`` — off-chain, ``2`` — all (default).
            start_time: Start timestamp in ms.
            end_time: End timestamp in ms.
            withdraw_id: Specific withdraw ID.
            tx_id: Specific transaction hash.
            limit: Page size per request (1–50, default 50).

        Note:
            The Bybit API limits each query to a 30-day window.  If you need
            a longer range, call this method in 30-day chunks or use
            :meth:`get_all_withdrawal_records` which handles it automatically.

        Returns:
            List of raw withdrawal record dicts (newest first).
        """
        params: dict = {"withdrawType": withdraw_type, "limit": limit}
        if coin:
            params["coin"] = coin.upper()
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if withdraw_id:
            params["withdrawID"] = withdraw_id
        if tx_id:
            params["txID"] = tx_id

        all_rows: List[dict] = []
        cursor: Optional[str] = None

        while True:
            p = dict(params)
            if cursor:
                p["cursor"] = cursor
            data = await self._auth_request(
                "GET", "/v5/asset/withdraw/query-record", params=p,
            )
            if not data:
                break
            result = data.get("result") or {}
            rows = result.get("rows") or []
            all_rows.extend(rows)
            cursor = result.get("nextPageCursor")
            if not cursor or len(rows) < limit:
                break

        return all_rows

    async def get_all_withdrawal_records(
        self,
        coin: Optional[str] = None,
        withdraw_type: int = 2,
        months: int = 1,
    ) -> List[dict]:
        """
        Load **full** withdrawal history by walking back in 30-day windows.

        Args:
            coin: Coin filter (optional).
            withdraw_type: ``0`` on-chain / ``1`` off-chain / ``2`` all.
            months: How many months back to look (default 12).

        Returns:
            All withdrawal records (newest first), auto-paginated.
        """
        import asyncio as _aio

        now_ms = int(time.time() * 1000)
        _30_DAYS_MS = 30 * 24 * 60 * 60 * 1000
        all_rows: List[dict] = []

        end = now_ms
        for _ in range(months):
            start = end - _30_DAYS_MS
            rows = await self.get_withdrawal_records(
                coin=coin,
                withdraw_type=withdraw_type,
                start_time=start,
                end_time=end,
            )
            all_rows.extend(rows)
            end = start
            if not rows:
                # No records in this window; keep going in case there are older ones
                continue

        # Deduplicate by withdrawId (windows may overlap at edges)
        seen: set = set()
        unique: List[dict] = []
        for r in all_rows:
            wid = r.get("withdrawId", "")
            if wid and wid in seen:
                continue
            seen.add(wid)
            unique.append(r)

        return unique

    # ============================== WITHDRAWAL SUMMARY ==============================

    @staticmethod
    def summarize_withdrawals(
        records: List[dict],
        status_filter: Optional[str] = "success",
    ) -> Dict[str, "WithdrawalSummary"]:
        """
        Group withdrawal records by coin and compute totals.

        Args:
            records: Raw withdrawal records from :meth:`get_withdrawal_records`
                     or :meth:`get_all_withdrawal_records`.
            status_filter: Only include records with this status.
                           ``None`` — include all statuses.
                           Default: ``"success"`` (only successful withdrawals).

        Returns:
            ``{"USDT": WithdrawalSummary(…), "ETH": WithdrawalSummary(…), …}``

        Each :class:`WithdrawalSummary` contains:

        - ``coin`` — coin name
        - ``total_amount`` — sum of withdrawn amounts
        - ``total_fee`` — sum of withdrawal fees
        - ``count`` — number of withdrawals
        - ``by_chain`` — breakdown per chain
        - ``records`` — raw records for this coin
        """
        summary: Dict[str, WithdrawalSummary] = {}

        for r in records:
            if status_filter and r.get("status") != status_filter:
                continue

            coin = r.get("coin", "UNKNOWN")
            chain = r.get("chain", "UNKNOWN")
            amount = float(r.get("amount", 0))
            fee = float(r.get("withdrawFee") or r.get("fee") or 0)

            if coin not in summary:
                summary[coin] = WithdrawalSummary(coin=coin)

            s = summary[coin]
            s.total_amount += amount
            s.total_fee += fee
            s.count += 1
            s.records.append(r)

            if chain not in s.by_chain:
                s.by_chain[chain] = {"amount": 0.0, "fee": 0.0, "count": 0}
            s.by_chain[chain]["amount"] += amount
            s.by_chain[chain]["fee"] += fee
            s.by_chain[chain]["count"] += 1

        return summary

    async def get_withdrawal_summary(
        self,
        months: int = 12,
        coin: Optional[str] = None,
        withdraw_type: int = 2,
        status_filter: Optional[str] = "success",
    ) -> Dict[str, "WithdrawalSummary"]:
        """
        All-in-one: load full withdrawal history and return a per-token summary.

        Args:
            months: How many months back (default 12).
            coin: Optional coin filter.
            withdraw_type: ``0`` on-chain / ``1`` off-chain / ``2`` all.
            status_filter: Only count records with this status (``"success"``
                           by default). ``None`` → all statuses.

        Returns:
            ``{"USDT": WithdrawalSummary(…), "BTC": WithdrawalSummary(…)}``

        Example::

            bb = Bybit(api_key="…", api_secret="…")
            summary = await bb.get_withdrawal_summary(months=6)
            for coin, s in summary.items():
                print(f"{coin}: {s.total_amount} withdrawn ({s.count} txns, "
                      f"fee: {s.total_fee})")
                for chain, info in s.by_chain.items():
                    print(f"  {chain}: {info['amount']} ({info['count']} txns)")
        """
        records = await self.get_all_withdrawal_records(
            coin=coin,
            withdraw_type=withdraw_type,
            months=months,
        )
        return self.summarize_withdrawals(records, status_filter=status_filter)


@dataclass
class WithdrawalSummary:
    """Per-coin withdrawal summary."""
    coin: str
    total_amount: float = 0.0
    total_fee: float = 0.0
    count: int = 0
    by_chain: Dict[str, dict] = field(default_factory=dict)
    records: List[dict] = field(default_factory=list)

    def __repr__(self) -> str:
        chains = ", ".join(
            f"{c}: {d['amount']}" for c, d in self.by_chain.items()
        )
        return (
            f"WithdrawalSummary(coin={self.coin!r}, "
            f"total={self.total_amount}, fee={self.total_fee}, "
            f"count={self.count}, chains=[{chains}])"
        )

