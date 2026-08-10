"""
CoinGecko API v3 client — market data & coin metadata.

Free tier requires no API key (~30 req/min).
Pro tier accepts *api_key* for higher rate limits.

Example::

    from OrbisPaySDK.utils.coingecko import CoinGecko

    cg = CoinGecko()
    prices = await cg.get_prices()             # default native coins in USD
    sol    = await cg.get_price("sol", "eur")  # single coin price in EUR
    info   = await cg.get_coin_info("bitcoin") # full coin metadata
    res    = await cg.search("solana")         # search coins
"""

from __future__ import annotations

from typing import Dict, List, Optional
from OrbisPaySDK.utils.provider import _BaseProvider


class CoinGecko(_BaseProvider):
    """
    CoinGecko price provider.

    Free tier — no API key required (rate-limit ~30 req/min).
    Pro tier  — pass *api_key* for higher limits.
    """

    COIN_ID_MAP: Dict[str, str] = {
        "btc": "bitcoin", "tbtc": "bitcoin", "bitcoin": "bitcoin",
        "eth": "ethereum", "teth": "ethereum", "evm": "ethereum", "ethereum": "ethereum", "goreth": "ethereum", "sepeth": "ethereum",
        "bnb": "binancecoin", "tbnb": "binancecoin", "bsc": "binancecoin", "binancecoin": "binancecoin",
        "sol": "solana", "tsol": "solana", "solana": "solana",
        "trx": "tron", "ttrx": "tron", "tron": "tron",
        "ton": "the-open-network", "tton": "the-open-network", "the-open-network": "the-open-network",
    }
    DEFAULT_COINS = ["bitcoin", "ethereum", "binancecoin", "solana", "tron", "the-open-network"]
    SYMBOL_MAP: Dict[str, str] = {
        "bitcoin": "btc", "ethereum": "eth", "binancecoin": "bnb", "solana": "sol",
        "tron": "trx", "the-open-network": "ton",
    }

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            base = "https://pro-api.coingecko.com/api/v3"
            headers = {"x-cg-pro-api-key": api_key}
        else:
            base = "https://api.coingecko.com/api/v3"
            headers = {}
        super().__init__(base, headers)

    def _resolve_ids(self, coins: Optional[List[str]] = None) -> List[str]:
        if not coins:
            return list(self.DEFAULT_COINS)
        ids = []
        for c in coins:
            c_clean = c.lower()
            cg_id = self.COIN_ID_MAP.get(c_clean)
            if not cg_id and c_clean.startswith("t") and len(c_clean) > 1:
                cg_id = self.COIN_ID_MAP.get(c_clean[1:])
            if not cg_id:
                cg_id = c_clean
            ids.append(cg_id)
        return ids

    async def get_prices(
        self,
        coins: Optional[List[str]] = None,
        vs_currency: str = "usd",
    ) -> Dict[str, float]:
        """
        Fetch prices for native tokens.

        Args:
            coins: List of aliases (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).
                   ``None`` — default set.
            vs_currency: Fiat code (``usd``, ``eur``, ``rub``, …).

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, "bnb": 600.0, ...}``
        """
        cg_ids = self._resolve_ids(coins)
        vs = vs_currency.lower()
        data = await self._get(
            "/simple/price",
            params={"ids": ",".join(sorted(set(cg_ids))), "vs_currencies": vs},
        ) or {}
        result: Dict[str, float] = {}
        for cg_id in cg_ids:
            sym = self.SYMBOL_MAP.get(cg_id, cg_id)
            result[sym] = float((data.get(cg_id) or {}).get(vs, 0))
        return result

    async def get_price(self, coin: str, vs_currency: str = "usd") -> float:
        """Get the price of a single token. Returns ``0.0`` if unavailable."""
        prices = await self.get_prices(coins=[coin], vs_currency=vs_currency)
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        sym = self.SYMBOL_MAP.get(cg_id, cg_id)
        return prices.get(sym, 0.0)

    async def get_coin_info(self, coin: str) -> Optional[dict]:
        """
        Full coin metadata (description, links, market data, …).

        *coin* can be an alias (``btc``) or CoinGecko ID (``bitcoin``).
        """
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        return await self._get(f"/coins/{cg_id}")

    async def search(self, query: str) -> list:
        """Search coins, categories, exchanges by keyword."""
        data = await self._get("/search", params={"query": query}) or {}
        return data.get("coins", [])

    async def get_market_chart(
        self,
        coin: str,
        days: int = 7,
        vs_currency: str = "usd",
    ) -> Optional[dict]:
        """
        Price / market-cap / volume chart data.

        Args:
            coin: Alias or CoinGecko ID.
            days: Number of days (1, 7, 30, 90, 365, ``max``).
            vs_currency: Fiat code.

        Returns:
            ``{"prices": [[ts, price], ...], "market_caps": [...], "total_volumes": [...]}``
        """
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        return await self._get(
            f"/coins/{cg_id}/market_chart",
            params={"vs_currency": vs_currency.lower(), "days": str(days)},
        )
