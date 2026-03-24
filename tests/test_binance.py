"""
Tests for the Binance API client.

Unit tests mock HTTP calls.
Integration tests (marked @pytest.mark.integration) hit real APIs.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from OrbisPaySDK.utils.binance import Binance


# ========================= Unit tests =========================

class TestBinanceUnit:

    def test_symbol_resolution(self):
        bn = Binance()
        assert bn._sym("btc") == "BTCUSDT"
        assert bn._sym("eth") == "ETHUSDT"
        assert bn._sym("bnb") == "BNBUSDT"
        assert bn._sym("sol") == "SOLUSDT"
        assert bn._sym("trx") == "TRXUSDT"
        assert bn._sym("ton") == "TONUSDT"
        assert bn._sym("BTCUSDT") == "BTCUSDT"
        assert bn._sym("xrpusdt") == "XRPUSDT"

    def test_init_mainnet(self):
        bn = Binance()
        assert "api.binance.com" in bn._base_url
        assert "testnet" not in bn._base_url

    def test_init_testnet(self):
        bn = Binance(testnet=True)
        assert "testnet" in bn._base_url

    def test_init_with_keys(self):
        bn = Binance(api_key="key123", api_secret="secret456")
        assert bn._api_key == "key123"
        assert bn._api_secret == "secret456"
        assert bn._headers.get("X-MBX-APIKEY") == "key123"

    def test_sign_params(self):
        bn = Binance(api_key="key", api_secret="secret")
        signed = bn._sign_params({"foo": "bar"})
        assert "timestamp" in signed
        assert "signature" in signed
        assert len(signed["signature"]) == 64  # HMAC-SHA256 hex

    def test_auth_required_raises(self):
        bn = Binance()
        with pytest.raises(RuntimeError, match="API key/secret required"):
            bn._sign_params({})

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {"symbol": "BTCUSDT", "price": "97000.50"}
        bn._get = mock_get

        price = await bn.get_price("btc")
        assert price == 97000.50

    @pytest.mark.asyncio
    async def test_get_price_not_found(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return None
        bn._get = mock_get

        price = await bn.get_price("btc")
        assert price == 0.0

    @pytest.mark.asyncio
    async def test_get_prices_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return [
                {"symbol": "BTCUSDT", "price": "97000"},
                {"symbol": "ETHUSDT", "price": "2600"},
                {"symbol": "BNBUSDT", "price": "600"},
                {"symbol": "SOLUSDT", "price": "80"},
                {"symbol": "TRXUSDT", "price": "0.28"},
                {"symbol": "TONUSDT", "price": "1.3"},
            ]
        bn._get = mock_get

        prices = await bn.get_prices()
        assert prices["btc"] == 97000.0
        assert prices["eth"] == 2600.0
        assert prices["bnb"] == 600.0
        assert prices["sol"] == 80.0
        assert prices["trx"] == 0.28
        assert prices["ton"] == 1.3

    @pytest.mark.asyncio
    async def test_get_prices_empty(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return None
        bn._get = mock_get

        prices = await bn.get_prices()
        assert all(v == 0.0 for v in prices.values())

    @pytest.mark.asyncio
    async def test_get_ticker_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {
                "symbol": "BTCUSDT",
                "lastPrice": "97000.50",
                "highPrice": "98000",
                "lowPrice": "95000",
                "volume": "12345.67",
                "priceChangePercent": "1.5",
            }
        bn._get = mock_get

        ticker = await bn.get_ticker("btc")
        assert ticker["symbol"] == "BTCUSDT"
        assert ticker["lastPrice"] == "97000.50"

    @pytest.mark.asyncio
    async def test_get_klines_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return [
                [1700000000000, "97000", "98000", "96000", "97500",
                 "100", 1700003600000, "9700000", 500, "50", "4850000", "0"],
            ]
        bn._get = mock_get

        klines = await bn.get_klines("btc", "1h")
        assert len(klines) == 1
        assert klines[0][1] == "97000"

    @pytest.mark.asyncio
    async def test_get_klines_empty(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return None
        bn._get = mock_get

        klines = await bn.get_klines("btc")
        assert klines == []

    @pytest.mark.asyncio
    async def test_get_orderbook_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {
                "bids": [["97000.00", "1.5"]],
                "asks": [["97001.00", "0.8"]],
            }
        bn._get = mock_get

        ob = await bn.get_orderbook("btc")
        assert ob is not None
        assert "bids" in ob
        assert "asks" in ob

    @pytest.mark.asyncio
    async def test_get_recent_trades_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return [
                {"price": "97000.00", "qty": "0.01", "isBuyerMaker": False},
            ]
        bn._get = mock_get

        trades = await bn.get_recent_trades("btc")
        assert len(trades) == 1

    @pytest.mark.asyncio
    async def test_get_recent_trades_empty(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return None
        bn._get = mock_get

        trades = await bn.get_recent_trades("btc")
        assert trades == []

    @pytest.mark.asyncio
    async def test_get_avg_price_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {"mins": 5, "price": "97000.50"}
        bn._get = mock_get

        avg = await bn.get_avg_price("btc")
        assert avg == 97000.50

    @pytest.mark.asyncio
    async def test_get_avg_price_empty(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return None
        bn._get = mock_get

        avg = await bn.get_avg_price("btc")
        assert avg == 0.0

    @pytest.mark.asyncio
    async def test_get_server_time_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {"serverTime": 1700000000000}
        bn._get = mock_get

        ts = await bn.get_server_time()
        assert ts == 1700000000000

    @pytest.mark.asyncio
    async def test_get_exchange_info_mock(self):
        bn = Binance()
        async def mock_get(path, params=None):
            return {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}]}
        bn._get = mock_get

        info = await bn.get_exchange_info("btc")
        assert info is not None
        assert len(info["symbols"]) == 1


# ========================= Integration tests =========================

@pytest.mark.integration
class TestBinanceIntegration:

    @pytest.mark.asyncio
    async def test_get_price_real(self):
        bn = Binance()
        price = await bn.get_price("BTCUSDT")
        assert price > 0

    @pytest.mark.asyncio
    async def test_get_prices_real(self):
        bn = Binance()
        prices = await bn.get_prices()
        assert prices["btc"] > 0
        assert prices["eth"] > 0
