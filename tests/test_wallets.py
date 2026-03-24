"""
Unit tests for wallet generation across all chains.
No network calls — all tests are offline.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest


# ========================= EVM =========================

class TestEVMWallet:

    def test_gen_wallet_returns_keys(self):
        from OrbisPaySDK.interface.evm import EVM
        evm = EVM()
        w = evm.gen_wallet()
        assert "address" in w
        assert "private_key" in w

    def test_gen_wallet_address_format(self):
        from OrbisPaySDK.interface.evm import EVM
        w = EVM().gen_wallet()
        assert w["address"].startswith("0x")
        assert len(w["address"]) == 42

    def test_gen_wallet_private_key_format(self):
        from OrbisPaySDK.interface.evm import EVM
        w = EVM().gen_wallet()
        assert isinstance(w["private_key"], str)
        # 64 hex chars (may or may not have 0x prefix)
        raw = w["private_key"].removeprefix("0x")
        assert len(raw) == 64

    def test_gen_wallet_unique(self):
        from OrbisPaySDK.interface.evm import EVM
        evm = EVM()
        w1 = evm.gen_wallet()
        w2 = evm.gen_wallet()
        assert w1["address"] != w2["address"]
        assert w1["private_key"] != w2["private_key"]


# ========================= SOL =========================

class TestSOLWallet:

    def test_gen_wallet_returns_keys(self):
        from OrbisPaySDK.interface.sol import SOL
        s = SOL()
        w = s.gen_wallet()
        assert "public_key" in w
        assert "private_key" in w

    def test_gen_wallet_public_key_length(self):
        from OrbisPaySDK.interface.sol import SOL
        w = SOL().gen_wallet()
        # Solana public keys are base58-encoded, typically 32-44 chars
        assert len(w["public_key"]) >= 32

    def test_gen_wallet_unique(self):
        from OrbisPaySDK.interface.sol import SOL
        s = SOL()
        w1 = s.gen_wallet()
        w2 = s.gen_wallet()
        assert w1["public_key"] != w2["public_key"]


# ========================= TON =========================

class TestTONWallet:

    def test_gen_wallet_default(self):
        from OrbisPaySDK.interface.ton import TON
        w = TON.gen_wallet()
        assert "mnemonics" in w
        assert "address" in w
        assert "raw_address" in w
        assert "WR5" in w

    def test_gen_wallet_has_mnemonics(self):
        from OrbisPaySDK.interface.ton import TON
        w = TON.gen_wallet()
        words = w["mnemonics"].split()
        assert len(words) == 24

    def test_gen_wallet_v4r2(self):
        from OrbisPaySDK.interface.ton import TON
        w = TON.gen_wallet(version="v4r2")
        assert w["address"]  # non-empty
        assert w["WR5"]  # WR5 address is always included

    def test_gen_wallet_wr5(self):
        from OrbisPaySDK.interface.ton import TON
        w = TON.gen_wallet(version="wr5")
        assert w["address"]
        assert w["WR5"]
        # For wr5, address == WR5
        assert w["address"] == w["WR5"]

    def test_gen_wallet_unique(self):
        from OrbisPaySDK.interface.ton import TON
        w1 = TON.gen_wallet()
        w2 = TON.gen_wallet()
        assert w1["mnemonics"] != w2["mnemonics"]
        assert w1["address"] != w2["address"]

    def test_set_wallet_v4r2(self):
        from OrbisPaySDK.interface.ton import TON
        ton = TON()
        w = TON.gen_wallet(version="v4r2")
        mnem = w["mnemonics"].split()
        ton.set_wallet(mnem, "v4r2")
        assert ton.wallet is not None
        assert ton.wallet_version == "v4r2"
        assert ton._v5_wallet is None
        addr = ton.get_address()
        assert addr  # non-empty string

    def test_set_wallet_wr5(self):
        from OrbisPaySDK.interface.ton import TON
        ton = TON()
        w = TON.gen_wallet(version="wr5")
        mnem = w["mnemonics"].split()
        ton.set_wallet(mnem, "wr5")
        assert ton.wallet is not None
        assert ton.wallet_version == "wr5"
        assert ton._v5_wallet is not None
        assert ton._v5_client is not None
        addr = ton.get_address()
        assert addr

    def test_wallet_versions_map(self):
        from OrbisPaySDK.interface.ton import TON
        assert "v3r1" in TON.WALLET_VERSIONS
        assert "v3r2" in TON.WALLET_VERSIONS
        assert "v4r2" in TON.WALLET_VERSIONS
        assert "wr5" in TON.WALLET_VERSIONS


# ========================= TRX =========================

class TestTRXWallet:

    def test_gen_wallet_returns_keys(self):
        from OrbisPaySDK.interface.trx import TRX
        w = TRX.gen_wallet()
        assert "address" in w
        assert "private_key" in w

    def test_gen_wallet_address_starts_with_T(self):
        from OrbisPaySDK.interface.trx import TRX
        w = TRX.gen_wallet()
        # Tron base58 addresses start with T
        assert w["address"].startswith("T")

    def test_gen_wallet_unique(self):
        from OrbisPaySDK.interface.trx import TRX
        w1 = TRX.gen_wallet()
        w2 = TRX.gen_wallet()
        assert w1["address"] != w2["address"]


# ========================= BTC =========================

class TestBTCWallet:

    def test_gen_wallet_returns_keys(self):
        from OrbisPaySDK.interface.btc import BTC
        w = BTC.gen_wallet()
        assert "address" in w
        assert "private_key" in w

    def test_gen_wallet_address_format(self):
        from OrbisPaySDK.interface.btc import BTC
        w = BTC.gen_wallet()
        # Bitcoin addresses start with 1, 3, or bc1
        addr = w["address"]
        assert addr[0] in ("1", "3", "b")

    def test_gen_wallet_unique(self):
        from OrbisPaySDK.interface.btc import BTC
        w1 = BTC.gen_wallet()
        w2 = BTC.gen_wallet()
        assert w1["address"] != w2["address"]

    def test_gen_wallet_mnemonic(self):
        from OrbisPaySDK.interface.btc import BTC
        w = BTC.gen_wallet_mnemonic(words=12)
        assert "mnemonic" in w
        assert "address" in w
        words = w["mnemonic"].split()
        assert len(words) == 12
