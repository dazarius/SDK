"""
Tests for get_balance_batch across all chains.

Unit tests mock network calls (run always).
Integration tests hit real APIs (run with: pytest -m integration).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


# ========================= EVM =========================

class TestEVMBalanceBatch:

    EVM_ADDRESSES = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
        "0x00000000219ab540356cBB839Cbe05303d7705Fa",
    ]

    def _make_evm(self):
        from OrbisPaySDK.interface.evm import EVM
        from web3 import Web3
        w3 = Web3()
        return EVM(w3=w3)

    def test_batch_returns_dict(self):
        evm = self._make_evm()
        mock_mc = MagicMock()
        mock_mc.functions.aggregate3.return_value.call.return_value = [
            (True, (1_000_000_000_000_000_000).to_bytes(32, "big")),
            (True, (2_000_000_000_000_000_000).to_bytes(32, "big")),
            (False, b"\x00" * 31),
        ]
        with patch.object(evm.w3.eth, "contract", return_value=mock_mc):
            result = evm.get_balance_batch(self.EVM_ADDRESSES)
        assert isinstance(result, dict)

    def test_batch_all_addresses_present(self):
        evm = self._make_evm()
        mock_mc = MagicMock()
        mock_mc.functions.aggregate3.return_value.call.return_value = [
            (True, (1_000_000_000_000_000_000).to_bytes(32, "big")),
            (True, (2_000_000_000_000_000_000).to_bytes(32, "big")),
            (True, (500_000_000_000_000_000).to_bytes(32, "big")),
        ]
        with patch.object(evm.w3.eth, "contract", return_value=mock_mc):
            result = evm.get_balance_batch(self.EVM_ADDRESSES)
        for addr in self.EVM_ADDRESSES:
            assert addr in result

    def test_batch_balances_are_floats(self):
        evm = self._make_evm()
        mock_mc = MagicMock()
        mock_mc.functions.aggregate3.return_value.call.return_value = [
            (True, (1_000_000_000_000_000_000).to_bytes(32, "big")),
            (True, (2_000_000_000_000_000_000).to_bytes(32, "big")),
            (True, (500_000_000_000_000_000).to_bytes(32, "big")),
        ]
        with patch.object(evm.w3.eth, "contract", return_value=mock_mc):
            result = evm.get_balance_batch(self.EVM_ADDRESSES)
        for val in result.values():
            assert isinstance(val, float)

    def test_batch_failed_call_returns_zero(self):
        evm = self._make_evm()
        mock_mc = MagicMock()
        mock_mc.functions.aggregate3.return_value.call.return_value = [
            (True, (1_000_000_000_000_000_000).to_bytes(32, "big")),
            (False, b"\x00" * 31),  # failed
            (True, (500_000_000_000_000_000).to_bytes(32, "big")),
        ]
        with patch.object(evm.w3.eth, "contract", return_value=mock_mc):
            result = evm.get_balance_batch(self.EVM_ADDRESSES)
        assert result[self.EVM_ADDRESSES[1]] == 0.0

    def test_batch_empty_list(self):
        evm = self._make_evm()
        mock_mc = MagicMock()
        mock_mc.functions.aggregate3.return_value.call.return_value = []
        with patch.object(evm.w3.eth, "contract", return_value=mock_mc):
            result = evm.get_balance_batch([])
        assert result == {}

    @pytest.mark.integration
    def test_batch_real_network(self):
        from OrbisPaySDK.interface.evm import EVM
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
        evm = EVM(w3=w3)
        result = evm.get_balance_batch(self.EVM_ADDRESSES)
        assert len(result) == len(self.EVM_ADDRESSES)
        for addr in self.EVM_ADDRESSES:
            assert addr in result
            assert result[addr] >= 0.0


# ========================= BTC =========================

class TestBTCBalanceBatch:

    BTC_ADDRESSES = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divfna",  # genesis
        "3FHNBLobJnbCPujupWQXQHhgmCbNnc4s1X",
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    ]

    def test_batch_returns_dict(self):
        from OrbisPaySDK.interface.btc import BTC
        mock_balance = 100_000_000  # 1 BTC in satoshi
        with patch("OrbisPaySDK.interface.btc.NetworkAPI.get_balance", return_value=mock_balance):
            result = BTC.get_balance_batch(self.BTC_ADDRESSES)
        assert isinstance(result, dict)

    def test_batch_all_addresses_present(self):
        from OrbisPaySDK.interface.btc import BTC
        with patch("OrbisPaySDK.interface.btc.NetworkAPI.get_balance", return_value=50_000_000):
            result = BTC.get_balance_batch(self.BTC_ADDRESSES)
        for addr in self.BTC_ADDRESSES:
            assert addr in result

    def test_batch_value_structure(self):
        from OrbisPaySDK.interface.btc import BTC
        with patch("OrbisPaySDK.interface.btc.NetworkAPI.get_balance", return_value=100_000_000):
            result = BTC.get_balance_batch(self.BTC_ADDRESSES)
        for val in result.values():
            assert "balance_ui" in val
            assert "balance" in val

    def test_batch_balance_conversion(self):
        from OrbisPaySDK.interface.btc import BTC
        with patch("OrbisPaySDK.interface.btc.NetworkAPI.get_balance", return_value=100_000_000):
            result = BTC.get_balance_batch([self.BTC_ADDRESSES[0]])
        assert result[self.BTC_ADDRESSES[0]]["balance_ui"] == pytest.approx(1.0)
        assert result[self.BTC_ADDRESSES[0]]["balance"] == 100_000_000

    def test_batch_network_error_returns_zero(self):
        from OrbisPaySDK.interface.btc import BTC
        with patch("OrbisPaySDK.interface.btc.NetworkAPI.get_balance", side_effect=Exception("timeout")):
            result = BTC.get_balance_batch([self.BTC_ADDRESSES[0]])
        assert result[self.BTC_ADDRESSES[0]]["balance_ui"] == 0.0
        assert result[self.BTC_ADDRESSES[0]]["balance"] == 0

    def test_batch_empty_list(self):
        from OrbisPaySDK.interface.btc import BTC
        result = BTC.get_balance_batch([])
        assert result == {}

    @pytest.mark.integration
    def test_batch_real_network(self):
        from OrbisPaySDK.interface.btc import BTC
        result = BTC.get_balance_batch(self.BTC_ADDRESSES[:2])
        assert len(result) == 2
        for addr in self.BTC_ADDRESSES[:2]:
            assert "balance_ui" in result[addr]
            assert "balance" in result[addr]
            assert result[addr]["balance"] >= 0


# ========================= SOL =========================

class TestSOLBalanceBatch:

    SOL_ADDRESSES = [
        "9zXTCt6dyoVn4GFmwtQfwGjayVVjojSjgayWK7u6GLVy",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
        "GThUX1Atko4tqhN2NaiTazFAcX74bKVodi5oGiMKGWzb",
    ]

    def test_batch_returns_dict(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()
            mock_resp = MagicMock()
            mock_resp.value = 1_000_000_000  # 1 SOL

            async def mock_get_balance(pubkey):
                return mock_resp

            s.client.get_balance = mock_get_balance
            return await s.get_balance_batch(self.SOL_ADDRESSES)

        result = asyncio.run(_run())
        assert isinstance(result, dict)

    def test_batch_all_addresses_present(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()
            mock_resp = MagicMock()
            mock_resp.value = 2_000_000_000

            async def mock_get_balance(pubkey):
                return mock_resp

            s.client.get_balance = mock_get_balance
            return await s.get_balance_batch(self.SOL_ADDRESSES)

        result = asyncio.run(_run())
        for addr in self.SOL_ADDRESSES:
            assert addr in result

    def test_batch_value_structure(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()
            mock_resp = MagicMock()
            mock_resp.value = 1_000_000_000

            async def mock_get_balance(pubkey):
                return mock_resp

            s.client.get_balance = mock_get_balance
            return await s.get_balance_batch(self.SOL_ADDRESSES)

        result = asyncio.run(_run())
        for val in result.values():
            assert "balance" in val
            assert "raw_balance" in val

    def test_batch_balance_conversion(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()
            mock_resp = MagicMock()
            mock_resp.value = 1_000_000_000  # 1 SOL in lamports

            async def mock_get_balance(pubkey):
                return mock_resp

            s.client.get_balance = mock_get_balance
            return await s.get_balance_batch([self.SOL_ADDRESSES[0]])

        result = asyncio.run(_run())
        assert result[self.SOL_ADDRESSES[0]]["balance"] == pytest.approx(1.0)
        assert result[self.SOL_ADDRESSES[0]]["raw_balance"] == 1_000_000_000

    def test_batch_error_returns_zero(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()

            async def mock_get_balance(pubkey):
                raise Exception("rpc error")

            s.client.get_balance = mock_get_balance
            return await s.get_balance_batch([self.SOL_ADDRESSES[0]])

        result = asyncio.run(_run())
        assert result[self.SOL_ADDRESSES[0]]["balance"] == 0.0
        assert result[self.SOL_ADDRESSES[0]]["raw_balance"] == 0

    def test_batch_empty_list(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL()
            return await s.get_balance_batch([])

        result = asyncio.run(_run())
        assert result == {}

    @pytest.mark.integration
    def test_batch_real_network(self):
        from OrbisPaySDK.interface.sol import SOL

        async def _run():
            s = SOL(rpc_url="https://api.mainnet-beta.solana.com")
            return await s.get_balance_batch(self.SOL_ADDRESSES)

        result = asyncio.run(_run())
        assert len(result) == len(self.SOL_ADDRESSES)
        for addr in self.SOL_ADDRESSES:
            assert "balance" in result[addr]
            assert result[addr]["balance"] >= 0.0


# ========================= TON =========================

class TestTONBalanceBatch:

    TON_ADDRESSES = [
        "EQCjk1hh952vWaE9bRguFkAhDADLuyJL8xEH0N3oBZv5HkSX",
        "UQDy3BhgaGzWWJh-K-2CFlMtjABEYNreqQfMfUrXI2xJa5C1",
        "EQBlqsm144Dq6SjbPI4jjZvA1hqTIP3CvHovbIfW_t-SCALE",
    ]

    def _mock_ton(self):
        from OrbisPaySDK.interface.ton import TON
        return TON(api_url="https://toncenter.com/api/v2", api_key="")

    def test_batch_returns_dict(self):
        ton = self._mock_ton()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": "1000000000"}

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                return await ton.get_balance_batch(self.TON_ADDRESSES)

        result = asyncio.run(_run())
        assert isinstance(result, dict)

    def test_batch_all_addresses_present(self):
        ton = self._mock_ton()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": "5000000000"}

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                return await ton.get_balance_batch(self.TON_ADDRESSES)

        result = asyncio.run(_run())
        for addr in self.TON_ADDRESSES:
            assert addr in result

    def test_batch_value_structure(self):
        ton = self._mock_ton()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": "1000000000"}

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                return await ton.get_balance_batch(self.TON_ADDRESSES)

        result = asyncio.run(_run())
        for val in result.values():
            assert "symbol" in val
            assert "decimals" in val
            assert "balance" in val
            assert "raw_balance" in val
            assert val["symbol"] == "TON"

    def test_batch_balance_conversion(self):
        ton = self._mock_ton()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": "1000000000"}  # 1 TON

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                return await ton.get_balance_batch([self.TON_ADDRESSES[0]])

        result = asyncio.run(_run())
        assert result[self.TON_ADDRESSES[0]]["balance"] == pytest.approx(1.0)
        assert result[self.TON_ADDRESSES[0]]["raw_balance"] == 1_000_000_000

    def test_batch_api_error_returns_zero(self):
        ton = self._mock_ton()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "invalid address"}

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                return await ton.get_balance_batch([self.TON_ADDRESSES[0]])

        result = asyncio.run(_run())
        assert result[self.TON_ADDRESSES[0]]["balance"] == 0.0
        assert result[self.TON_ADDRESSES[0]]["raw_balance"] == 0

    def test_batch_empty_list(self):
        ton = self._mock_ton()

        async def _run():
            return await ton.get_balance_batch([])

        result = asyncio.run(_run())
        assert result == {}

    @pytest.mark.integration
    def test_batch_real_network(self):
        ton = self._mock_ton()

        async def _run():
            return await ton.get_balance_batch(self.TON_ADDRESSES[:2])

        result = asyncio.run(_run())
        assert len(result) == 2
        for addr in self.TON_ADDRESSES[:2]:
            assert "balance" in result[addr]
            assert result[addr]["balance"] >= 0.0


# ========================= TRX =========================

class TestTRXBalanceBatch:

    TRX_ADDRESSES = [
        "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
        "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9",
        "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC",
    ]

    def _make_trx(self):
        from OrbisPaySDK.interface.trx import TRX
        return TRX()

    def test_batch_returns_dict(self):
        trx = self._make_trx()
        with patch.object(trx.client, "get_account_balance", return_value=100.0):
            result = trx.get_balance_batch(self.TRX_ADDRESSES)
        assert isinstance(result, dict)

    def test_batch_all_addresses_present(self):
        trx = self._make_trx()
        with patch.object(trx.client, "get_account_balance", return_value=50.0):
            result = trx.get_balance_batch(self.TRX_ADDRESSES)
        for addr in self.TRX_ADDRESSES:
            assert addr in result

    def test_batch_value_structure(self):
        trx = self._make_trx()
        with patch.object(trx.client, "get_account_balance", return_value=100.0):
            result = trx.get_balance_batch(self.TRX_ADDRESSES)
        for val in result.values():
            assert "balance_ui" in val
            assert "balance" in val

    def test_batch_balance_conversion(self):
        trx = self._make_trx()
        with patch.object(trx.client, "get_account_balance", return_value=100.0):
            result = trx.get_balance_batch([self.TRX_ADDRESSES[0]])
        assert result[self.TRX_ADDRESSES[0]]["balance_ui"] == pytest.approx(100.0)
        assert result[self.TRX_ADDRESSES[0]]["balance"] == 100_000_000  # in sun

    def test_batch_error_returns_zero(self):
        trx = self._make_trx()
        with patch.object(trx.client, "get_account_balance", side_effect=Exception("timeout")):
            result = trx.get_balance_batch([self.TRX_ADDRESSES[0]])
        assert result[self.TRX_ADDRESSES[0]]["balance_ui"] == 0.0
        assert result[self.TRX_ADDRESSES[0]]["balance"] == 0

    def test_batch_empty_list(self):
        trx = self._make_trx()
        result = trx.get_balance_batch([])
        assert result == {}

    @pytest.mark.integration
    def test_batch_real_network(self):
        trx = self._make_trx()
        result = trx.get_balance_batch(self.TRX_ADDRESSES)
        assert len(result) == len(self.TRX_ADDRESSES)
        for addr in self.TRX_ADDRESSES:
            assert "balance_ui" in result[addr]
            assert result[addr]["balance"] >= 0
