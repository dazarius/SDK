"""
Tests for the 0x Swap API v2 client.

Unit tests mock HTTP calls.
Integration tests (marked @pytest.mark.integration) require a 0x API key.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from OrbisPaySDK.utils.zerox import ZeroX, SUPPORTED_CHAINS, KNOWN_TOKENS


# ========================= Unit tests =========================

class TestZeroXUnit:

    def test_resolve_chain_id_int(self):
        assert ZeroX._resolve_chain_id(1) == 1
        assert ZeroX._resolve_chain_id(137) == 137
        assert ZeroX._resolve_chain_id(42161) == 42161

    def test_resolve_chain_id_alias(self):
        assert ZeroX._resolve_chain_id("ethereum") == 1
        assert ZeroX._resolve_chain_id("eth") == 1
        assert ZeroX._resolve_chain_id("polygon") == 137
        assert ZeroX._resolve_chain_id("matic") == 137
        assert ZeroX._resolve_chain_id("arbitrum") == 42161
        assert ZeroX._resolve_chain_id("arb") == 42161
        assert ZeroX._resolve_chain_id("bsc") == 56
        assert ZeroX._resolve_chain_id("base") == 8453
        assert ZeroX._resolve_chain_id("optimism") == 10
        assert ZeroX._resolve_chain_id("avalanche") == 43114

    def test_resolve_chain_id_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown chain"):
            ZeroX._resolve_chain_id("fantom_unknown")

    def test_resolve_token_known(self):
        assert ZeroX._resolve_token("weth", 1) == KNOWN_TOKENS[1]["weth"]
        assert ZeroX._resolve_token("usdc", 1) == KNOWN_TOKENS[1]["usdc"]
        assert ZeroX._resolve_token("usdc", 137) == KNOWN_TOKENS[137]["usdc"]
        assert ZeroX._resolve_token("bnb", 56) == KNOWN_TOKENS[56]["bnb"]

    def test_resolve_token_passthrough(self):
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        assert ZeroX._resolve_token(addr, 1) == addr

    def test_init_headers(self):
        zx = ZeroX(api_key="my-key")
        assert zx._headers["0x-api-key"] == "my-key"
        assert zx._headers["0x-version"] == "2"
        assert "0x.org" in zx._base_url

    def test_supported_chains(self):
        chains = ZeroX.supported_chains()
        assert chains["ethereum"] == 1
        assert chains["polygon"] == 137
        assert chains["bsc"] == 56

    def test_known_tokens_existing_chain(self):
        tokens = ZeroX.known_tokens(1)
        assert "weth" in tokens
        assert "usdc" in tokens

    def test_known_tokens_unknown_chain(self):
        tokens = ZeroX.known_tokens(99999)
        assert tokens == {}

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        zx = ZeroX(api_key="fake")
        async def mock_get(path, params=None):
            return {
                "sellToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "buyToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "sellAmount": "1000000000000000000",
                "buyAmount": "2600000000",
                "price": "2600.0",
                "estimatedGas": "200000",
            }
        zx._get = mock_get

        result = await zx.get_price(
            chain_id="ethereum",
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
        )
        assert result is not None
        assert result["buyAmount"] == "2600000000"
        assert result["price"] == "2600.0"

    @pytest.mark.asyncio
    async def test_get_price_none(self):
        zx = ZeroX(api_key="fake")
        async def mock_get(path, params=None):
            return None
        zx._get = mock_get

        result = await zx.get_price(
            chain_id=1,
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_quote_mock(self):
        zx = ZeroX(api_key="fake")
        async def mock_get(path, params=None):
            return {
                "sellToken": KNOWN_TOKENS[1]["weth"],
                "buyToken": KNOWN_TOKENS[1]["usdc"],
                "sellAmount": "1000000000000000000",
                "buyAmount": "2600000000",
                "transaction": {
                    "to": "0xdef1…",
                    "data": "0xabcdef…",
                    "value": "0",
                    "gas": "200000",
                },
                "permit2": {"eip712": {}},
                "route": {"fills": []},
            }
        zx._get = mock_get

        result = await zx.get_quote(
            chain_id="ethereum",
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
            taker="0x0000000000000000000000000000000000000001",
        )
        assert result is not None
        assert "transaction" in result
        assert "permit2" in result

    @pytest.mark.asyncio
    async def test_get_price_with_slippage(self):
        zx = ZeroX(api_key="fake")
        captured_params = {}
        async def mock_get(path, params=None):
            captured_params.update(params or {})
            return {"price": "2600.0"}
        zx._get = mock_get

        await zx.get_price(
            chain_id=1,
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
            slippage_bps=100,
        )
        assert captured_params.get("slippageBps") == 100

    @pytest.mark.asyncio
    async def test_get_price_buy_amount(self):
        zx = ZeroX(api_key="fake")
        captured_params = {}
        async def mock_get(path, params=None):
            captured_params.update(params or {})
            return {"price": "0.000384"}
        zx._get = mock_get

        await zx.get_price(
            chain_id=1,
            sell_token="weth",
            buy_token="usdc",
            buy_amount="2600000000",
        )
        assert "buyAmount" in captured_params
        assert "sellAmount" not in captured_params

    @pytest.mark.asyncio
    async def test_get_price_allowance_mock(self):
        zx = ZeroX(api_key="fake")
        captured_path = {}
        async def mock_get(path, params=None):
            captured_path["path"] = path
            return {"price": "2600.0"}
        zx._get = mock_get

        await zx.get_price_allowance(
            chain_id=1,
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
        )
        assert "allowance-holder" in captured_path["path"]

    @pytest.mark.asyncio
    async def test_get_quote_allowance_mock(self):
        zx = ZeroX(api_key="fake")
        captured_path = {}
        async def mock_get(path, params=None):
            captured_path["path"] = path
            return {"transaction": {}, "route": {}}
        zx._get = mock_get

        await zx.get_quote_allowance(
            chain_id=1,
            sell_token="weth",
            buy_token="usdc",
            sell_amount="1000000000000000000",
            taker="0x0000000000000000000000000000000000000001",
        )
        assert "allowance-holder" in captured_path["path"]

    @pytest.mark.asyncio
    async def test_chain_id_passed_in_params(self):
        zx = ZeroX(api_key="fake")
        captured_params = {}
        async def mock_get(path, params=None):
            captured_params.update(params or {})
            return {}
        zx._get = mock_get

        await zx.get_price(
            chain_id="polygon",
            sell_token="wmatic",
            buy_token="usdc",
            sell_amount="1000000000000000000",
        )
        assert captured_params["chainId"] == 137
        assert captured_params["sellToken"] == KNOWN_TOKENS[137]["wmatic"]
        assert captured_params["buyToken"] == KNOWN_TOKENS[137]["usdc"]

    @pytest.mark.asyncio
    async def test_bsc_token_resolution(self):
        zx = ZeroX(api_key="fake")
        captured_params = {}
        async def mock_get(path, params=None):
            captured_params.update(params or {})
            return {}
        zx._get = mock_get

        await zx.get_price(
            chain_id="bsc",
            sell_token="bnb",
            buy_token="usdt",
            sell_amount="1000000000000000000",
        )
        assert captured_params["chainId"] == 56
        assert captured_params["sellToken"] == KNOWN_TOKENS[56]["bnb"]
        assert captured_params["buyToken"] == KNOWN_TOKENS[56]["usdt"]
