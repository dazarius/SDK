"""
CoinMarketCap API v2 client — price quotes & cryptocurrency listings.

Requires an API key (get one free at https://pro.coinmarketcap.com).

Example::

    from OrbisPaySDK.utils.coinmarketcap import CoinMarketCap

    cmc = CoinMarketCap(api_key="your-api-key")
    prices = await cmc.get_prices()           # prices for default native symbols
    sol    = await cmc.get_price("sol", "EUR") # single symbol price in EUR
    top    = await cmc.get_listings(limit=20) # top 20 by market cap
    info   = await cmc.get_coin_info("BTC")   # coin metadata
"""

from __future__ import annotations

from typing import Dict, List, Optional
from OrbisPaySDK.utils.provider import _BaseProvider


class CoinMarketCap(_BaseProvider):
    """
    CoinMarketCap price provider (requires API key).

    Get a key at https://pro.coinmarketcap.com
    """

    SYMBOL_MAP: Dict[str, str] = {
        "btc": "BTC", "bitcoin": "BTC",
        "eth": "ETH", "evm": "ETH", "ethereum": "ETH",
        "bnb": "BNB", "bsc": "BNB", "binancecoin": "BNB",
        "sol": "SOL", "solana": "SOL",
        "trx": "TRX", "tron": "TRX",
        "ton": "TON", "the-open-network": "TON",
    }
    DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "TRX", "TON"]

    def __init__(self, api_key: str):
        super().__init__(
            "https://pro-api.coinmarketcap.com",
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
        )

    def _resolve_symbols(self, coins: Optional[List[str]] = None) -> List[str]:
        if not coins:
            return list(self.DEFAULT_SYMBOLS)
        syms = []
        for c in coins:
            s = self.SYMBOL_MAP.get(c.lower(), c.upper())
            syms.append(s)
        return syms

    async def get_prices(
        self,
        coins: Optional[List[str]] = None,
        vs_currency: str = "USD",
    ) -> Dict[str, float]:
        """
        Fetch latest prices.

        Args:
            coins: List of aliases (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).
            vs_currency: Fiat code (``USD``, ``EUR``, …).

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, "bnb": 600.0, ...}``
        """
        symbols = self._resolve_symbols(coins)
        data = await self._get(
            "/v2/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(symbols), "convert": vs_currency.upper()},
        )
        if not data:
            return {s.lower(): 0.0 for s in symbols}

        result: Dict[str, float] = {}
        quotes = data.get("data", {})
        for sym in symbols:
            entries = quotes.get(sym, [])
            if isinstance(entries, list) and entries:
                entry = entries[0]
            elif isinstance(entries, dict):
                entry = entries
            else:
                result[sym.lower()] = 0.0
                continue
            price = (
                entry.get("quote", {})
                .get(vs_currency.upper(), {})
                .get("price", 0)
            )
            result[sym.lower()] = float(price) if price else 0.0
        return result

    async def get_price(self, coin: str, vs_currency: str = "USD") -> float:
        """Get the price of a single token."""
        prices = await self.get_prices(coins=[coin], vs_currency=vs_currency)
        sym = self.SYMBOL_MAP.get(coin.lower(), coin.upper()).lower()
        return prices.get(sym, 0.0)

    async def get_listings(
        self,
        limit: int = 100,
        vs_currency: str = "USD",
    ) -> list:
        """
        Top cryptocurrencies by market cap.

        Returns:
            List of dicts with ``name``, ``symbol``, ``price``, ``market_cap``, etc.
        """
        data = await self._get(
            "/v1/cryptocurrency/listings/latest",
            params={"limit": str(limit), "convert": vs_currency.upper()},
        )
        if not data:
            return []
        raw = data.get("data", [])
        result = []
        for item in raw:
            q = item.get("quote", {}).get(vs_currency.upper(), {})
            result.append({
                "symbol": item.get("symbol", ""),
                "name": item.get("name", ""),
                "price": q.get("price", 0),
                "market_cap": q.get("market_cap", 0),
                "volume_24h": q.get("volume_24h", 0),
                "percent_change_24h": q.get("percent_change_24h", 0),
                "percent_change_7d": q.get("percent_change_7d", 0),
            })
        return result

    async def get_coin_info(self, coin: str) -> Optional[dict]:
        """
        Coin metadata (logo, description, urls, …).

        *coin* can be an alias (``btc``) or raw symbol (``BTC``).
        """
        sym = self.SYMBOL_MAP.get(coin.lower(), coin.upper())
        data = await self._get(
            "/v2/cryptocurrency/info",
            params={"symbol": sym},
        )
        if not data:
            return None
        entries = data.get("data", {}).get(sym, [])
        if isinstance(entries, list) and entries:
            return entries[0]
        if isinstance(entries, dict):
            return entries
        return None
