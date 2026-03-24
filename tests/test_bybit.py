"""
Tests for the Bybit API client.

Unit tests mock HTTP calls.
Integration tests (marked @pytest.mark.integration) hit real APIs.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from OrbisPaySDK.utils.bybit import Bybit, WithdrawalSummary


# ========================= Unit tests =========================

class TestBybitUnit:

    def test_symbol_resolution(self):
        bb = Bybit()
        assert bb._sym("btc") == "BTCUSDT"
        assert bb._sym("eth") == "ETHUSDT"
        assert bb._sym("bnb") == "BNBUSDT"
        assert bb._sym("sol") == "SOLUSDT"
        assert bb._sym("trx") == "TRXUSDT"
        assert bb._sym("ton") == "TONUSDT"
        assert bb._sym("BTCUSDT") == "BTCUSDT"
        assert bb._sym("xrpusdt") == "XRPUSDT"

    def test_init_mainnet(self):
        bb = Bybit()
        assert "api.bybit.com" in bb._base_url
        assert "testnet" not in bb._base_url

    def test_init_testnet(self):
        bb = Bybit(testnet=True)
        assert "testnet" in bb._base_url

    def test_init_with_keys(self):
        bb = Bybit(api_key="key123", api_secret="secret456")
        assert bb._api_key == "key123"
        assert bb._api_secret == "secret456"

    def test_auth_required_raises(self):
        bb = Bybit()  # no keys
        with pytest.raises(RuntimeError, match="API key/secret required"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                bb.get_wallet_balance()
            )

    @pytest.mark.asyncio
    async def test_get_ticker_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [{
                        "symbol": "BTCUSDT",
                        "lastPrice": "97000.50",
                        "highPrice24h": "98000",
                        "lowPrice24h": "95000",
                        "volume24h": "12345.67",
                    }]
                }
            }
        bb._get = mock_get

        ticker = await bb.get_ticker("btc")
        assert ticker is not None
        assert ticker["symbol"] == "BTCUSDT"
        assert ticker["lastPrice"] == "97000.50"

    @pytest.mark.asyncio
    async def test_get_tickers_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [
                        {"symbol": "BTCUSDT", "lastPrice": "97000"},
                        {"symbol": "ETHUSDT", "lastPrice": "2600"},
                    ]
                }
            }
        bb._get = mock_get

        tickers = await bb.get_tickers()
        assert len(tickers) == 2

    @pytest.mark.asyncio
    async def test_get_price_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [{"symbol": "BTCUSDT", "lastPrice": "97000.50"}]
                }
            }
        bb._get = mock_get

        price = await bb.get_price("btc")
        assert price == 97000.50

    @pytest.mark.asyncio
    async def test_get_price_not_found(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {"result": {"list": []}}
        bb._get = mock_get

        price = await bb.get_price("btc")
        assert price == 0.0

    @pytest.mark.asyncio
    async def test_get_prices_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [
                        {"symbol": "BTCUSDT", "lastPrice": "97000"},
                        {"symbol": "ETHUSDT", "lastPrice": "2600"},
                        {"symbol": "BNBUSDT", "lastPrice": "600"},
                        {"symbol": "SOLUSDT", "lastPrice": "80"},
                        {"symbol": "TRXUSDT", "lastPrice": "0.28"},
                        {"symbol": "TONUSDT", "lastPrice": "1.3"},
                    ]
                }
            }
        bb._get = mock_get

        prices = await bb.get_prices()
        assert prices["btc"] == 97000.0
        assert prices["eth"] == 2600.0
        assert prices["bnb"] == 600.0
        assert prices["sol"] == 80.0
        assert prices["trx"] == 0.28
        assert prices["ton"] == 1.3

    @pytest.mark.asyncio
    async def test_get_klines_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [
                        ["1700000000000", "97000", "98000", "96000", "97500", "100", "9700000"],
                    ]
                }
            }
        bb._get = mock_get

        klines = await bb.get_klines("btc", "60")
        assert len(klines) == 1
        assert klines[0][1] == "97000"

    @pytest.mark.asyncio
    async def test_get_orderbook_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "b": [["97000", "1.5"]],
                    "a": [["97001", "0.8"]],
                }
            }
        bb._get = mock_get

        ob = await bb.get_orderbook("btc")
        assert ob is not None
        assert "b" in ob
        assert "a" in ob

    @pytest.mark.asyncio
    async def test_get_recent_trades_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [
                        {"price": "97000", "size": "0.01", "side": "Buy", "time": "1700000000"},
                    ]
                }
            }
        bb._get = mock_get

        trades = await bb.get_recent_trades("btc")
        assert len(trades) == 1
        assert trades[0]["side"] == "Buy"

    @pytest.mark.asyncio
    async def test_get_instruments_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {
                "result": {
                    "list": [{"symbol": "BTCUSDT", "status": "Trading"}]
                }
            }
        bb._get = mock_get

        instruments = await bb.get_instruments("btc")
        assert len(instruments) == 1
        assert instruments[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_server_time_mock(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return {"result": {"timeSecond": "1700000000"}}
        bb._get = mock_get

        ts = await bb.get_server_time()
        assert ts == 1700000000000

    @pytest.mark.asyncio
    async def test_get_klines_empty(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return None
        bb._get = mock_get

        klines = await bb.get_klines("btc")
        assert klines == []

    @pytest.mark.asyncio
    async def test_get_recent_trades_empty(self):
        bb = Bybit()
        async def mock_get(path, params=None):
            return None
        bb._get = mock_get

        trades = await bb.get_recent_trades("btc")
        assert trades == []


# ========================= Withdrawal tests =========================

# -- sample withdrawal records for unit tests --
_SAMPLE_RECORDS = [
    {
        "coin": "USDT", "chain": "ETH", "amount": "500.5",
        "withdrawFee": "5", "status": "success",
        "toAddress": "0xabc…", "withdrawId": "1001",
        "createTime": "1700000000000", "withdrawType": 0,
    },
    {
        "coin": "USDT", "chain": "SOL", "amount": "200",
        "withdrawFee": "1", "status": "success",
        "toAddress": "Dhte…", "withdrawId": "1002",
        "createTime": "1700100000000", "withdrawType": 0,
    },
    {
        "coin": "USDT", "chain": "TRX", "amount": "100",
        "withdrawFee": "0.5", "status": "success",
        "toAddress": "TXyz…", "withdrawId": "1003",
        "createTime": "1700200000000", "withdrawType": 0,
    },
    {
        "coin": "ETH", "chain": "ETH", "amount": "1.25",
        "withdrawFee": "0.001", "status": "success",
        "toAddress": "0xdef…", "withdrawId": "2001",
        "createTime": "1700300000000", "withdrawType": 0,
    },
    {
        "coin": "ETH", "chain": "ARB", "amount": "0.5",
        "withdrawFee": "0.0005", "status": "success",
        "toAddress": "0xghi…", "withdrawId": "2002",
        "createTime": "1700400000000", "withdrawType": 0,
    },
    {
        "coin": "BTC", "chain": "BTC", "amount": "0.05",
        "withdrawFee": "0.0002", "status": "success",
        "toAddress": "bc1q…", "withdrawId": "3001",
        "createTime": "1700500000000", "withdrawType": 0,
    },
    {
        "coin": "USDT", "chain": "ETH", "amount": "1000",
        "withdrawFee": "5", "status": "SecurityCheck",
        "toAddress": "0xfail…", "withdrawId": "9001",
        "createTime": "1700600000000", "withdrawType": 0,
    },
]


class TestWithdrawalSummary:

    def test_summarize_basic(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        assert "USDT" in summary
        assert "ETH" in summary
        assert "BTC" in summary
        # USDT: 500.5 + 200 + 100 = 800.5 (the SecurityCheck one is excluded)
        assert summary["USDT"].total_amount == pytest.approx(800.5)
        assert summary["USDT"].count == 3
        assert summary["USDT"].total_fee == pytest.approx(6.5)  # 5 + 1 + 0.5

    def test_summarize_by_chain(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        usdt = summary["USDT"]
        assert "ETH" in usdt.by_chain
        assert "SOL" in usdt.by_chain
        assert "TRX" in usdt.by_chain
        assert usdt.by_chain["ETH"]["amount"] == pytest.approx(500.5)
        assert usdt.by_chain["SOL"]["amount"] == pytest.approx(200.0)
        assert usdt.by_chain["TRX"]["amount"] == pytest.approx(100.0)
        assert usdt.by_chain["ETH"]["count"] == 1
        assert usdt.by_chain["SOL"]["count"] == 1

    def test_summarize_eth(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        eth = summary["ETH"]
        assert eth.total_amount == pytest.approx(1.75)  # 1.25 + 0.5
        assert eth.count == 2
        assert "ETH" in eth.by_chain
        assert "ARB" in eth.by_chain
        assert eth.by_chain["ETH"]["amount"] == pytest.approx(1.25)
        assert eth.by_chain["ARB"]["amount"] == pytest.approx(0.5)

    def test_summarize_btc(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        btc = summary["BTC"]
        assert btc.total_amount == pytest.approx(0.05)
        assert btc.count == 1
        assert btc.total_fee == pytest.approx(0.0002)

    def test_summarize_no_status_filter(self):
        """With status_filter=None, all records are included."""
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS, status_filter=None)
        # Now the SecurityCheck USDT record is also counted
        assert summary["USDT"].total_amount == pytest.approx(1800.5)
        assert summary["USDT"].count == 4

    def test_summarize_custom_status_filter(self):
        summary = Bybit.summarize_withdrawals(
            _SAMPLE_RECORDS, status_filter="SecurityCheck",
        )
        assert "USDT" in summary
        assert summary["USDT"].total_amount == pytest.approx(1000.0)
        assert summary["USDT"].count == 1
        assert "ETH" not in summary
        assert "BTC" not in summary

    def test_summarize_empty(self):
        summary = Bybit.summarize_withdrawals([])
        assert summary == {}

    def test_records_attached(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        assert len(summary["USDT"].records) == 3
        assert all(r["coin"] == "USDT" for r in summary["USDT"].records)

    def test_repr(self):
        summary = Bybit.summarize_withdrawals(_SAMPLE_RECORDS)
        r = repr(summary["USDT"])
        assert "USDT" in r
        assert "800.5" in r

    def test_withdrawal_summary_dataclass(self):
        ws = WithdrawalSummary(coin="SOL")
        assert ws.total_amount == 0.0
        assert ws.total_fee == 0.0
        assert ws.count == 0
        assert ws.by_chain == {}
        assert ws.records == []


class TestWithdrawalRecordsMock:

    @pytest.mark.asyncio
    async def test_get_withdrawal_records_single_page(self):
        bb = Bybit(api_key="k", api_secret="s")
        async def mock_auth(method, path, params=None, body=None):
            return {
                "result": {
                    "rows": _SAMPLE_RECORDS[:3],
                    "nextPageCursor": "",
                }
            }
        bb._auth_request = mock_auth

        records = await bb.get_withdrawal_records(coin="USDT")
        assert len(records) == 3
        assert all(r["coin"] == "USDT" for r in records)

    @pytest.mark.asyncio
    async def test_get_withdrawal_records_pagination(self):
        """Simulate two pages of results."""
        bb = Bybit(api_key="k", api_secret="s")
        call_count = 0

        async def mock_auth(method, path, params=None, body=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "result": {
                        "rows": _SAMPLE_RECORDS[:2],
                        "nextPageCursor": "page2cursor",
                    }
                }
            return {
                "result": {
                    "rows": _SAMPLE_RECORDS[2:4],
                    "nextPageCursor": "",
                }
            }
        bb._auth_request = mock_auth

        records = await bb.get_withdrawal_records(limit=2)
        assert len(records) == 4
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_get_withdrawal_records_none_response(self):
        bb = Bybit(api_key="k", api_secret="s")
        async def mock_auth(method, path, params=None, body=None):
            return None
        bb._auth_request = mock_auth

        records = await bb.get_withdrawal_records()
        assert records == []

    @pytest.mark.asyncio
    async def test_get_all_withdrawal_records_dedup(self):
        """Records appearing in overlapping windows are deduplicated."""
        bb = Bybit(api_key="k", api_secret="s")

        async def mock_auth(method, path, params=None, body=None):
            # Always return the same 2 records (simulating overlap)
            return {
                "result": {
                    "rows": _SAMPLE_RECORDS[:2],
                    "nextPageCursor": "",
                }
            }
        bb._auth_request = mock_auth

        records = await bb.get_all_withdrawal_records(months=3)
        # Despite 3 windows each returning 2 records, dedup keeps 2
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_get_withdrawal_summary_mock(self):
        bb = Bybit(api_key="k", api_secret="s")
        async def mock_auth(method, path, params=None, body=None):
            return {
                "result": {
                    "rows": _SAMPLE_RECORDS[:6],  # exclude SecurityCheck
                    "nextPageCursor": "",
                }
            }
        bb._auth_request = mock_auth

        summary = await bb.get_withdrawal_summary(months=1)
        assert "USDT" in summary
        assert "ETH" in summary
        assert "BTC" in summary
        assert summary["USDT"].total_amount == pytest.approx(800.5)
        assert summary["ETH"].count == 2
        assert summary["BTC"].total_amount == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_get_withdrawal_addresses_mock(self):
        bb = Bybit(api_key="k", api_secret="s")
        async def mock_auth(method, path, params=None, body=None):
            return {
                "result": {
                    "rows": [
                        {"coin": "USDT", "chain": "ETH",
                         "address": "0x48101…", "status": 0, "verified": 1},
                        {"coin": "baseCoin", "chain": "ETH",
                         "address": "0x48101…", "remark": "Universal Address",
                         "status": 0, "verified": 0},
                    ],
                    "nextPageCursor": "",
                }
            }
        bb._auth_request = mock_auth

        addrs = await bb.get_withdrawal_addresses(coin="USDT")
        assert len(addrs) == 2
        assert addrs[0]["coin"] == "USDT"


# ========================= Integration tests =========================

@pytest.mark.integration
class TestBybitIntegration:

    @pytest.mark.asyncio
    async def test_get_ticker_real(self):
        bb = Bybit()
        ticker = await bb.get_ticker("BTCUSDT")
        assert ticker is not None
        assert float(ticker["lastPrice"]) > 0

    @pytest.mark.asyncio
    async def test_get_prices_real(self):
        bb = Bybit()
        prices = await bb.get_prices()
        assert prices["btc"] > 0
        assert prices["eth"] > 0
