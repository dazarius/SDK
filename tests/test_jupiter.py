"""
Tests for the Jupiter (Solana DEX) API client.

Unit tests mock HTTP calls.
Integration tests (marked @pytest.mark.integration) hit real APIs.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from OrbisPaySDK.utils.jupiter import Jupiter, KNOWN_MINTS


# ========================= Unit tests =========================

class TestJupiterUnit:

    def test_resolve_mint_alias(self):
        assert Jupiter._resolve_mint("sol") == KNOWN_MINTS["sol"]
        assert Jupiter._resolve_mint("usdc") == KNOWN_MINTS["usdc"]
        assert Jupiter._resolve_mint("usdt") == KNOWN_MINTS["usdt"]
        assert Jupiter._resolve_mint("jup") == KNOWN_MINTS["jup"]

    def test_resolve_mint_passthrough(self):
        addr = "So11111111111111111111111111111111111111112"
        assert Jupiter._resolve_mint(addr) == addr

    def test_known_mints_not_empty(self):
        assert len(KNOWN_MINTS) >= 5

    def test_init_no_key(self):
        jup = Jupiter()
        assert "jup.ag" in jup._base_url
        assert jup._headers == {}

    def test_init_with_key(self):
        jup = Jupiter(api_key="test-key")
        assert "Bearer test-key" in jup._headers.get("Authorization", "")

    @pytest.mark.asyncio
    async def test_get_quote_mock(self):
        jup = Jupiter()
        async def mock_get(path, params=None):
            return {
                "inputMint": KNOWN_MINTS["sol"],
                "outputMint": KNOWN_MINTS["usdc"],
                "inAmount": "1000000000",
                "outAmount": "80000000",
                "otherAmountThreshold": "79600000",
                "priceImpactPct": "0.01",
                "routePlan": [{"swapInfo": {"label": "Raydium"}}],
            }
        jup._get = mock_get

        quote = await jup.get_quote("sol", "usdc", 1_000_000_000)
        assert quote is not None
        assert quote["inAmount"] == "1000000000"
        assert quote["outAmount"] == "80000000"
        assert len(quote["routePlan"]) == 1

    @pytest.mark.asyncio
    async def test_get_quote_none_response(self):
        jup = Jupiter()
        async def mock_get(path, params=None):
            return None
        jup._get = mock_get

        quote = await jup.get_quote("sol", "usdc", 1_000_000_000)
        assert quote is None

    @pytest.mark.asyncio
    async def test_get_quote_with_options(self):
        jup = Jupiter()
        captured_params = {}
        async def mock_get(path, params=None):
            captured_params.update(params or {})
            return {"inAmount": "1000", "outAmount": "80"}
        jup._get = mock_get

        await jup.get_quote(
            "sol", "usdc", 1000,
            slippage_bps=100,
            swap_mode="ExactOut",
            only_direct_routes=True,
            max_accounts=20,
            platform_fee_bps=10,
        )
        assert captured_params["slippageBps"] == 100
        assert captured_params["swapMode"] == "ExactOut"
        assert captured_params["onlyDirectRoutes"] == "true"
        assert captured_params["maxAccounts"] == 20
        assert captured_params["platformFeeBps"] == 10

    @pytest.mark.asyncio
    async def test_get_swap_mock(self):
        jup = Jupiter()
        import httpx

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps({
                    "swapTransaction": "base64encodedtx==",
                    "lastValidBlockHeight": 123456789,
                }).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        # Patch httpx.AsyncClient to use mock transport
        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            swap = await jup.get_swap(
                quote_response={"inAmount": "1000", "outAmount": "80"},
                user_public_key="FakePublicKey111111111111111111111111111111111",
            )
            assert swap is not None
            assert swap["swapTransaction"] == "base64encodedtx=="
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_get_swap_instructions_mock(self):
        jup = Jupiter()
        import httpx

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps({
                    "setupInstructions": [],
                    "swapInstruction": {"programId": "JUP6…"},
                    "cleanupInstruction": None,
                    "addressLookupTableAddresses": [],
                }).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            result = await jup.get_swap_instructions(
                quote_response={"inAmount": "1000", "outAmount": "80"},
                user_public_key="FakePublicKey111111111111111111111111111111111",
            )
            assert result is not None
            assert "swapInstruction" in result
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_get_prices_mock(self):
        jup = Jupiter()
        import httpx

        sol_mint = KNOWN_MINTS["sol"]

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps({
                    "data": {
                        sol_mint: {"id": sol_mint, "price": "80.5"},
                    }
                }).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            prices = await jup.get_prices(["sol"])
            assert prices[sol_mint] == 80.5
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        jup = Jupiter()
        import httpx

        sol_mint = KNOWN_MINTS["sol"]

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps({
                    "data": {
                        sol_mint: {"id": sol_mint, "price": "80.5"},
                    }
                }).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            price = await jup.get_price("sol")
            assert price == 80.5
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_get_token_list_mock(self):
        jup = Jupiter()
        import httpx

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps([
                    {"address": KNOWN_MINTS["sol"], "symbol": "SOL", "name": "Solana", "decimals": 9},
                    {"address": KNOWN_MINTS["usdc"], "symbol": "USDC", "name": "USD Coin", "decimals": 6},
                ]).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            tokens = await jup.get_token_list()
            assert len(tokens) == 2
            assert tokens[0]["symbol"] == "SOL"
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_search_token_mock(self):
        jup = Jupiter()
        import httpx

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json
                body = json.dumps([
                    {"address": KNOWN_MINTS["sol"], "symbol": "SOL", "name": "Solana", "decimals": 9},
                    {"address": KNOWN_MINTS["usdc"], "symbol": "USDC", "name": "USD Coin", "decimals": 6},
                    {"address": "fake", "symbol": "BONK", "name": "Bonk", "decimals": 5},
                ]).encode()
                return httpx.Response(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    content=body,
                )

        original_init = httpx.AsyncClient.__init__
        def patched_init(self_client, **kwargs):
            kwargs["transport"] = MockTransport()
            original_init(self_client, **kwargs)
        httpx.AsyncClient.__init__ = patched_init

        try:
            results = await jup.search_token("sol")
            assert any(t["symbol"] == "SOL" for t in results)
        finally:
            httpx.AsyncClient.__init__ = original_init


# ========================= Integration tests =========================

@pytest.mark.integration
class TestJupiterIntegration:

    @pytest.mark.asyncio
    async def test_get_quote_real(self):
        jup = Jupiter()
        quote = await jup.get_quote(
            input_mint="sol",
            output_mint="usdc",
            amount=100_000_000,  # 0.1 SOL
        )
        assert quote is not None
        assert int(quote.get("outAmount", 0)) > 0

    @pytest.mark.asyncio
    async def test_get_price_real(self):
        jup = Jupiter()
        price = await jup.get_price("sol")
        assert price > 0
