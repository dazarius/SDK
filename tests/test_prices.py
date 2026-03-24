"""
Tests for price provider classes: CoinGecko, CoinMarketCap, DexScreener.

Unit tests mock HTTP calls.
Integration tests (marked @pytest.mark.integration) hit real APIs and may be slow.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import pytest
import httpx
import pytest_asyncio

from OrbisPaySDK.utils.utils import (
    CoinGecko,
    CoinMarketCap,
    DexScreener,
    get_native_prices,
    get_native_price,
)


# ========================= Mock transport =========================

class MockTransport(httpx.AsyncBaseTransport):
    """Returns pre-configured JSON responses for any request."""

    def __init__(self, response_data, status_code=200):
        self._data = response_data
        self._status = status_code

    async def handle_async_request(self, request):
        body = json.dumps(self._data).encode()
        return httpx.Response(
            status_code=self._status,
            headers={"content-type": "application/json"},
            content=body,
        )


# ========================= CoinGecko unit tests =========================

class TestCoinGeckoUnit:

    def test_resolve_ids_default(self):
        cg = CoinGecko()
        ids = cg._resolve_ids()
        assert "bitcoin" in ids
        assert "ethereum" in ids
        assert "solana" in ids
        assert "tron" in ids
        assert "binancecoin" in ids
        assert "the-open-network" in ids
        assert len(ids) == 6

    def test_resolve_ids_aliases(self):
        cg = CoinGecko()
        ids = cg._resolve_ids(["btc", "evm", "ton"])
        assert ids == ["bitcoin", "ethereum", "the-open-network"]

    def test_resolve_ids_unknown_raises(self):
        cg = CoinGecko()
        with pytest.raises(ValueError, match="Unknown coin"):
            cg._resolve_ids(["unknown_coin"])

    def test_symbol_map_completeness(self):
        cg = CoinGecko()
        for coin_id in cg.DEFAULT_COINS:
            assert coin_id in cg.SYMBOL_MAP

    def test_init_free_tier(self):
        cg = CoinGecko()
        assert "coingecko.com" in cg._base_url
        assert "pro" not in cg._base_url

    def test_init_pro_tier(self):
        cg = CoinGecko(api_key="test-key")
        assert "pro-api" in cg._base_url
        assert cg._headers.get("x-cg-pro-api-key") == "test-key"

    @pytest.mark.asyncio
    async def test_get_prices_mock(self):
        """Test get_prices with mocked HTTP response."""
        cg = CoinGecko()
        mock_data = {
            "bitcoin": {"usd": 67000.0},
            "ethereum": {"usd": 1900.0},
            "binancecoin": {"usd": 600.0},
            "solana": {"usd": 80.0},
            "tron": {"usd": 0.28},
            "the-open-network": {"usd": 1.3},
        }
        # Patch the _get method
        async def mock_get(path, params=None):
            return mock_data
        cg._get = mock_get

        prices = await cg.get_prices()
        assert prices["btc"] == 67000.0
        assert prices["eth"] == 1900.0
        assert prices["bnb"] == 600.0
        assert prices["sol"] == 80.0
        assert prices["trx"] == 0.28
        assert prices["ton"] == 1.3

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        cg = CoinGecko()
        async def mock_get(path, params=None):
            return {"bitcoin": {"usd": 99000.0}}
        cg._get = mock_get

        price = await cg.get_price("btc")
        assert price == 99000.0

    @pytest.mark.asyncio
    async def test_get_prices_empty_response(self):
        cg = CoinGecko()
        async def mock_get(path, params=None):
            return {}
        cg._get = mock_get

        prices = await cg.get_prices()
        for v in prices.values():
            assert v == 0.0

    @pytest.mark.asyncio
    async def test_search_mock(self):
        cg = CoinGecko()
        async def mock_get(path, params=None):
            return {"coins": [{"id": "solana", "name": "Solana", "symbol": "SOL"}]}
        cg._get = mock_get

        results = await cg.search("solana")
        assert len(results) == 1
        assert results[0]["name"] == "Solana"

    @pytest.mark.asyncio
    async def test_get_coin_info_mock(self):
        cg = CoinGecko()
        async def mock_get(path, params=None):
            return {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}
        cg._get = mock_get

        info = await cg.get_coin_info("btc")
        assert info["name"] == "Bitcoin"

    @pytest.mark.asyncio
    async def test_rate_limit_returns_none(self):
        """When _get returns None (rate limited), prices should be zeros."""
        cg = CoinGecko()
        async def mock_get(path, params=None):
            return None
        cg._get = mock_get

        prices = await cg.get_prices()
        assert all(v == 0.0 for v in prices.values())


# ========================= CoinMarketCap unit tests =========================

class TestCoinMarketCapUnit:

    def test_resolve_symbols_default(self):
        cmc = CoinMarketCap(api_key="fake")
        syms = cmc._resolve_symbols()
        assert syms == ["BTC", "ETH", "BNB", "SOL", "TRX", "TON"]

    def test_resolve_symbols_aliases(self):
        cmc = CoinMarketCap(api_key="fake")
        syms = cmc._resolve_symbols(["btc", "evm", "ton"])
        assert syms == ["BTC", "ETH", "TON"]

    def test_init_headers(self):
        cmc = CoinMarketCap(api_key="my-key")
        assert cmc._headers["X-CMC_PRO_API_KEY"] == "my-key"
        assert "coinmarketcap.com" in cmc._base_url

    @pytest.mark.asyncio
    async def test_get_prices_mock(self):
        cmc = CoinMarketCap(api_key="fake")
        mock_data = {
            "data": {
                "BTC": [{"quote": {"USD": {"price": 68000}}}],
                "ETH": [{"quote": {"USD": {"price": 2000}}}],
                "BNB": [{"quote": {"USD": {"price": 600}}}],
                "SOL": [{"quote": {"USD": {"price": 85}}}],
                "TRX": [{"quote": {"USD": {"price": 0.3}}}],
                "TON": [{"quote": {"USD": {"price": 1.5}}}],
            }
        }
        async def mock_get(path, params=None):
            return mock_data
        cmc._get = mock_get

        prices = await cmc.get_prices()
        assert prices["btc"] == 68000.0
        assert prices["eth"] == 2000.0
        assert prices["bnb"] == 600.0
        assert prices["sol"] == 85.0
        assert prices["trx"] == 0.3
        assert prices["ton"] == 1.5

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        cmc = CoinMarketCap(api_key="fake")
        async def mock_get(path, params=None):
            return {"data": {"SOL": [{"quote": {"USD": {"price": 90}}}]}}
        cmc._get = mock_get

        price = await cmc.get_price("sol")
        assert price == 90.0

    @pytest.mark.asyncio
    async def test_get_prices_none_response(self):
        cmc = CoinMarketCap(api_key="fake")
        async def mock_get(path, params=None):
            return None
        cmc._get = mock_get

        prices = await cmc.get_prices()
        assert all(v == 0.0 for v in prices.values())

    @pytest.mark.asyncio
    async def test_get_listings_mock(self):
        cmc = CoinMarketCap(api_key="fake")
        async def mock_get(path, params=None):
            return {
                "data": [
                    {
                        "symbol": "BTC", "name": "Bitcoin",
                        "quote": {"USD": {
                            "price": 68000, "market_cap": 1.3e12,
                            "volume_24h": 30e9,
                            "percent_change_24h": 1.5,
                            "percent_change_7d": -2.3,
                        }},
                    }
                ]
            }
        cmc._get = mock_get

        listings = await cmc.get_listings(limit=1)
        assert len(listings) == 1
        assert listings[0]["symbol"] == "BTC"
        assert listings[0]["price"] == 68000

    @pytest.mark.asyncio
    async def test_get_coin_info_mock(self):
        cmc = CoinMarketCap(api_key="fake")
        async def mock_get(path, params=None):
            return {"data": {"BTC": [{"name": "Bitcoin", "description": "..."}]}}
        cmc._get = mock_get

        info = await cmc.get_coin_info("btc")
        assert info["name"] == "Bitcoin"


# ========================= DexScreener unit tests =========================

class TestDexScreenerUnit:

    def test_chain_alias_resolution(self):
        ds = DexScreener()
        assert ds._chain("sol") == "solana"
        assert ds._chain("eth") == "ethereum"
        assert ds._chain("trx") == "tron"
        assert ds._chain("bsc") == "bsc"
        assert ds._chain("solana") == "solana"
        # Unknown chains pass through
        assert ds._chain("fantom") == "fantom"

    def test_init_no_key(self):
        ds = DexScreener()
        assert "dexscreener.com" in ds._base_url
        assert ds._headers == {}

    @pytest.mark.asyncio
    async def test_search_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return {
                "pairs": [
                    {
                        "chainId": "solana",
                        "dexId": "raydium",
                        "baseToken": {"symbol": "SOL"},
                        "quoteToken": {"symbol": "USDC"},
                        "priceUsd": "80.5",
                    }
                ]
            }
        ds._get = mock_get

        pairs = await ds.search("SOL/USDC")
        assert len(pairs) == 1
        assert pairs[0]["baseToken"]["symbol"] == "SOL"

    @pytest.mark.asyncio
    async def test_get_token_price_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return [
                {
                    "priceUsd": "80.5",
                    "liquidity": {"usd": 1_000_000},
                },
                {
                    "priceUsd": "80.3",
                    "liquidity": {"usd": 500_000},
                },
            ]
        ds._get = mock_get

        price = await ds.get_token_price("solana", "So111")
        assert price == 80.5  # picked the higher liquidity pair

    @pytest.mark.asyncio
    async def test_get_token_price_empty(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return []
        ds._get = mock_get

        price = await ds.get_token_price("solana", "nonexistent")
        assert price == 0.0

    @pytest.mark.asyncio
    async def test_get_pair_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return {"pairs": [{"pairAddress": "abc", "priceUsd": "1.5"}]}
        ds._get = mock_get

        pair = await ds.get_pair("solana", "abc")
        assert pair["pairAddress"] == "abc"

    @pytest.mark.asyncio
    async def test_get_pair_not_found(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return {"pairs": []}
        ds._get = mock_get

        pair = await ds.get_pair("solana", "abc")
        assert pair is None

    @pytest.mark.asyncio
    async def test_get_tokens_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return [{"pairAddress": "p1"}, {"pairAddress": "p2"}]
        ds._get = mock_get

        tokens = await ds.get_tokens("solana", "addr1")
        assert len(tokens) == 2

    @pytest.mark.asyncio
    async def test_get_token_pools_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return [{"pairAddress": "pool1"}, {"pairAddress": "pool2"}]
        ds._get = mock_get

        pools = await ds.get_token_pools("sol", "addr1")
        assert len(pools) == 2

    @pytest.mark.asyncio
    async def test_search_empty(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return None
        ds._get = mock_get

        pairs = await ds.search("nonexistent_xyz")
        assert pairs == []

    @pytest.mark.asyncio
    async def test_get_top_boosts_mock(self):
        ds = DexScreener()
        async def mock_get(path, params=None):
            return [{"tokenAddress": "a", "totalAmount": 10}]
        ds._get = mock_get

        boosts = await ds.get_top_boosts()
        assert len(boosts) == 1


# ========================= Backward compat module-level functions =========================

class TestBackwardCompat:

    @pytest.mark.asyncio
    async def test_get_native_prices_delegates(self):
        """The module-level function should return a dict with all 5 keys."""
        # Patch the default CoinGecko instance
        import OrbisPaySDK.utils.utils as mod
        orig = mod._default_cg._get

        async def mock_get(path, params=None):
            return {
                "bitcoin": {"usd": 100}, "ethereum": {"usd": 200},
                "binancecoin": {"usd": 250},
                "solana": {"usd": 300}, "tron": {"usd": 400},
                "the-open-network": {"usd": 500},
            }
        mod._default_cg._get = mock_get
        try:
            prices = await get_native_prices()
            assert len(prices) == 6
            assert prices["btc"] == 100.0
        finally:
            mod._default_cg._get = orig

    @pytest.mark.asyncio
    async def test_get_native_price_delegates(self):
        import OrbisPaySDK.utils.utils as mod
        orig = mod._default_cg._get

        async def mock_get(path, params=None):
            return {"bitcoin": {"usd": 77777}}
        mod._default_cg._get = mock_get
        try:
            price = await get_native_price("btc")
            assert price == 77777.0
        finally:
            mod._default_cg._get = orig


# ========================= Integration tests (real network) =========================

@pytest.mark.integration
class TestCoinGeckoIntegration:
    """These tests hit real CoinGecko API. Run with: pytest -m integration"""

    @pytest.mark.asyncio
    async def test_get_prices_real(self):
        cg = CoinGecko()
        prices = await cg.get_prices()
        assert "btc" in prices
        assert prices["btc"] > 0

    @pytest.mark.asyncio
    async def test_search_real(self):
        cg = CoinGecko()
        results = await cg.search("bitcoin")
        assert len(results) > 0


@pytest.mark.integration
class TestDexScreenerIntegration:
    """These tests hit real DexScreener API. Run with: pytest -m integration"""

    @pytest.mark.asyncio
    async def test_search_real(self):
        ds = DexScreener()
        pairs = await ds.search("SOL/USDC")
        assert len(pairs) > 0

    @pytest.mark.asyncio
    async def test_get_token_price_real(self):
        ds = DexScreener()
        price = await ds.get_token_price(
            "solana", "So11111111111111111111111111111111111111112"
        )
        assert price > 0
