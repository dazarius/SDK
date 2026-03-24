from bit import Key, PrivateKeyTestnet
from bit.network import NetworkAPI
from typing import Optional, Union, List, Dict, Any

from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39SeedGenerator,
    Bip39MnemonicValidator,
    Bip39WordsNum,
    Bip44,
    Bip44Coins,
    Bip44Changes,
    Bip84,
    Bip84Coins,
    Bip49,
    Bip49Coins,
)

SATOSHI_PER_BTC = 100_000_000  # 1 BTC = 100,000,000 satoshi

# BIP derivation path standards
BIP44_PATH = "m/44'/0'/0'/0/{index}"    # Legacy P2PKH
BIP49_PATH = "m/49'/0'/0'/0/{index}"    # Wrapped SegWit P2SH-P2WPKH
BIP84_PATH = "m/84'/0'/0'/0/{index}"    # Native SegWit P2WPKH (bech32)

# Testnet equivalents
BIP44_TESTNET_PATH = "m/44'/1'/0'/0/{index}"
BIP49_TESTNET_PATH = "m/49'/1'/0'/0/{index}"
BIP84_TESTNET_PATH = "m/84'/1'/0'/0/{index}"


class BTC:
    """
    Bitcoin blockchain interface for OrbisPaySDK.
    Supports BIP39 mnemonic generation, HD wallet derivation (BIP44/49/84),
    native BTC transfers, balance queries, UTXO management.

    Libraries: bit (transactions), bip_utils (HD wallet / mnemonic).
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        mnemonics: Optional[Union[str, List[str]]] = None,
        passphrase: str = "",
        address_index: int = 0,
        address_type: str = "bip84",
        testnet: bool = False,
    ):
        """
        Args:
            private_key: WIF private key (overrides mnemonic if both given).
            mnemonics: BIP39 mnemonic phrase (str or list of words).
            passphrase: Optional BIP39 passphrase for seed generation.
            address_index: Address index for HD derivation (default 0).
            address_type: Derivation standard — 'bip44' (legacy), 'bip49' (wrapped segwit), 'bip84' (native segwit).
            testnet: Use testnet instead of mainnet.
        """
        self.testnet = testnet
        self.key = None
        self.mnemonics = None
        self.passphrase = passphrase
        self.address_index = address_index
        self.address_type = address_type
        self._seed = None
        self._derived_info = None

        if mnemonics:
            self.from_mnemonic(mnemonics, passphrase, address_index, address_type)
        elif private_key:
            self.set_private_key(private_key)

    # ========================= Mnemonic / HD Wallet =========================

    @staticmethod
    def generate_mnemonic(words: int = 12) -> str:
        """
        Generate a new BIP39 mnemonic phrase.

        Args:
            words: Number of words (12 or 24).

        Returns:
            Mnemonic phrase as a string.
        """
        words_map = {
            12: Bip39WordsNum.WORDS_NUM_12,
            15: Bip39WordsNum.WORDS_NUM_15,
            18: Bip39WordsNum.WORDS_NUM_18,
            21: Bip39WordsNum.WORDS_NUM_21,
            24: Bip39WordsNum.WORDS_NUM_24,
        }
        if words not in words_map:
            raise ValueError(f"Invalid word count: {words}. Allowed: {list(words_map.keys())}")

        mnemonic = Bip39MnemonicGenerator().FromWordsNumber(words_map[words])
        return mnemonic.ToStr()

    @staticmethod
    def validate_mnemonic(mnemonic: Union[str, List[str]]) -> bool:
        """
        Validate a BIP39 mnemonic phrase.

        Args:
            mnemonic: Mnemonic as string or list of words.

        Returns:
            True if valid, False otherwise.
        """
        if isinstance(mnemonic, list):
            mnemonic = " ".join(mnemonic)
        return Bip39MnemonicValidator(mnemonic).IsValid()

    def from_mnemonic(
        self,
        mnemonic: Union[str, List[str]],
        passphrase: str = "",
        address_index: int = 0,
        address_type: str = "bip84",
    ):
        """
        Load wallet from BIP39 mnemonic. Derives the private key using
        the specified BIP standard and address index.

        Args:
            mnemonic: BIP39 mnemonic phrase (string or list of words).
            passphrase: Optional BIP39 passphrase (extra security layer).
            address_index: HD derivation address index (default 0).
            address_type: 'bip44' (legacy P2PKH), 'bip49' (P2SH-P2WPKH), 'bip84' (native segwit bech32).
        """
        if isinstance(mnemonic, list):
            mnemonic = " ".join(mnemonic)

        if not Bip39MnemonicValidator(mnemonic).IsValid():
            raise ValueError("Invalid BIP39 mnemonic phrase.")

        self.mnemonics = mnemonic
        self.passphrase = passphrase
        self.address_index = address_index
        self.address_type = address_type

        # Generate seed
        self._seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)

        # Derive key
        self._derived_info = self._derive_key(
            seed=self._seed,
            address_type=address_type,
            address_index=address_index,
            testnet=self.testnet,
        )

        # Set bit Key from the derived WIF
        wif = self._derived_info["wif"]
        if self.testnet:
            self.key = PrivateKeyTestnet(wif)
        else:
            self.key = Key(wif)

    @staticmethod
    def _derive_key(
        seed: bytes,
        address_type: str = "bip84",
        address_index: int = 0,
        account: int = 0,
        testnet: bool = False,
    ) -> dict:
        """
        Derive a key from seed using the specified BIP standard.

        Returns:
            dict with wif, address, private_key_hex, public_key_hex, path.
        """
        if address_type == "bip44":
            coin = Bip44Coins.BITCOIN_TESTNET if testnet else Bip44Coins.BITCOIN
            ctx = Bip44.FromSeed(seed, coin)
            derived = (
                ctx.Purpose()
                .Coin()
                .Account(account)
                .Change(Bip44Changes.CHAIN_EXT)
                .AddressIndex(address_index)
            )
            path = (BIP44_TESTNET_PATH if testnet else BIP44_PATH).format(index=address_index)

        elif address_type == "bip49":
            coin = Bip49Coins.BITCOIN_TESTNET if testnet else Bip49Coins.BITCOIN
            ctx = Bip49.FromSeed(seed, coin)
            derived = (
                ctx.Purpose()
                .Coin()
                .Account(account)
                .Change(Bip44Changes.CHAIN_EXT)
                .AddressIndex(address_index)
            )
            path = (BIP49_TESTNET_PATH if testnet else BIP49_PATH).format(index=address_index)

        elif address_type == "bip84":
            coin = Bip84Coins.BITCOIN_TESTNET if testnet else Bip84Coins.BITCOIN
            ctx = Bip84.FromSeed(seed, coin)
            derived = (
                ctx.Purpose()
                .Coin()
                .Account(account)
                .Change(Bip44Changes.CHAIN_EXT)
                .AddressIndex(address_index)
            )
            path = (BIP84_TESTNET_PATH if testnet else BIP84_PATH).format(index=address_index)

        else:
            raise ValueError(f"Unknown address_type: {address_type}. Use 'bip44', 'bip49', or 'bip84'.")

        return {
            "wif": derived.PrivateKey().ToWif(),
            "address": derived.PublicKey().ToAddress(),
            "private_key_hex": derived.PrivateKey().Raw().ToHex(),
            "public_key_hex": derived.PublicKey().RawCompressed().ToHex(),
            "path": path,
        }

    def derive_address(
        self,
        index: int,
        address_type: Optional[str] = None,
        account: int = 0,
    ) -> dict:
        """
        Derive a specific address by index from the current mnemonic.

        Args:
            index: Address index in the derivation path.
            address_type: Override derivation standard (defaults to current).
            account: Account index (default 0).

        Returns:
            dict with wif, address, private_key_hex, public_key_hex, path.
        """
        if not self._seed:
            raise ValueError("No mnemonic loaded. Use from_mnemonic() first.")

        at = address_type or self.address_type
        return self._derive_key(
            seed=self._seed,
            address_type=at,
            address_index=index,
            account=account,
            testnet=self.testnet,
        )

    def derive_addresses(
        self,
        count: int = 5,
        start_index: int = 0,
        address_type: Optional[str] = None,
        account: int = 0,
    ) -> List[dict]:
        """
        Derive multiple addresses from the current mnemonic.

        Args:
            count: Number of addresses to derive.
            start_index: Starting address index.
            address_type: Override derivation standard.
            account: Account index.

        Returns:
            List of dicts, each with wif, address, path, etc.
        """
        if not self._seed:
            raise ValueError("No mnemonic loaded. Use from_mnemonic() first.")

        at = address_type or self.address_type
        results = []
        for i in range(start_index, start_index + count):
            info = self._derive_key(
                seed=self._seed,
                address_type=at,
                address_index=i,
                account=account,
                testnet=self.testnet,
            )
            results.append(info)
        return results

    def get_all_address_types(self, index: int = 0) -> dict:
        """
        Derive an address in all 3 standards (BIP44, BIP49, BIP84) at the given index.

        Returns:
            dict with keys 'bip44', 'bip49', 'bip84', each containing address info.
        """
        if not self._seed:
            raise ValueError("No mnemonic loaded. Use from_mnemonic() first.")

        return {
            "bip44": self._derive_key(self._seed, "bip44", index, testnet=self.testnet),
            "bip49": self._derive_key(self._seed, "bip49", index, testnet=self.testnet),
            "bip84": self._derive_key(self._seed, "bip84", index, testnet=self.testnet),
        }

    @staticmethod
    def gen_wallet_mnemonic(
        words: int = 12,
        passphrase: str = "",
        address_type: str = "bip84",
        testnet: bool = False,
    ) -> dict:
        """
        Generate a brand-new HD wallet with mnemonic.

        Args:
            words: Number of mnemonic words (12 or 24).
            passphrase: Optional BIP39 passphrase.
            address_type: 'bip44', 'bip49', or 'bip84'.
            testnet: Use testnet.

        Returns:
            dict with mnemonic, seed_hex, address info for index 0.
        """
        # Generate mnemonic
        words_map = {
            12: Bip39WordsNum.WORDS_NUM_12,
            15: Bip39WordsNum.WORDS_NUM_15,
            18: Bip39WordsNum.WORDS_NUM_18,
            21: Bip39WordsNum.WORDS_NUM_21,
            24: Bip39WordsNum.WORDS_NUM_24,
        }
        if words not in words_map:
            raise ValueError(f"Invalid word count: {words}. Use 12, 15, 18, 21, or 24.")

        mnemonic = Bip39MnemonicGenerator().FromWordsNumber(words_map[words])
        mnemonic_str = mnemonic.ToStr()

        # Generate seed
        seed = Bip39SeedGenerator(mnemonic_str).Generate(passphrase)

        # Derive first address
        derived = BTC._derive_key(
            seed=seed,
            address_type=address_type,
            address_index=0,
            testnet=testnet,
        )

        return {
            "mnemonic": mnemonic_str,
            "seed_hex": seed.hex(),
            "wif": derived["wif"],
            "address": derived["address"],
            "private_key_hex": derived["private_key_hex"],
            "public_key_hex": derived["public_key_hex"],
            "path": derived["path"],
            "address_type": address_type,
            "testnet": testnet,
        }

    # ========================= Key Management =========================

    def set_private_key(self, private_key: str):
        """
        Set private key (WIF format). Clears any mnemonic state.
        """
        self.mnemonics = None
        self._seed = None
        self._derived_info = None

        if self.testnet:
            self.key = PrivateKeyTestnet(private_key)
        else:
            self.key = Key(private_key)

    def set_params(
        self,
        private_key: Optional[str] = None,
        mnemonics: Optional[Union[str, List[str]]] = None,
        passphrase: Optional[str] = None,
        address_index: Optional[int] = None,
        address_type: Optional[str] = None,
        testnet: Optional[bool] = None,
    ):
        if testnet is not None:
            self.testnet = testnet
        if passphrase is not None:
            self.passphrase = passphrase
        if address_type is not None:
            self.address_type = address_type
        if address_index is not None:
            self.address_index = address_index

        if mnemonics:
            self.from_mnemonic(
                mnemonics,
                passphrase=self.passphrase,
                address_index=self.address_index,
                address_type=self.address_type,
            )
        elif private_key:
            self.set_private_key(private_key)

    @staticmethod
    def gen_wallet(testnet: bool = False) -> dict:
        """
        Generate a simple Bitcoin wallet (random key, no mnemonic).

        Returns:
            dict with private_key (WIF), address (P2PKH), and segwit_address.
        """
        if testnet:
            key = PrivateKeyTestnet()
        else:
            key = Key()

        return {
            "private_key": key.to_wif(),
            "address": key.address,
            "segwit_address": key.segwit_address,
            "public_key": key.public_key.hex(),
        }

    # ========================= Address / Info =========================

    def get_address(self) -> str:
        """Get the current active address."""
        if self._derived_info:
            return self._derived_info["address"]
        if not self.key:
            raise ValueError("No key set. Use set_private_key() or from_mnemonic().")
        return self.key.address

    def get_segwit_address(self) -> str:
        """Get the SegWit (P2SH-P2WPKH) address from the bit Key."""
        if not self.key:
            raise ValueError("No key set.")
        return self.key.segwit_address

    def get_wallet_info(self) -> dict:
        """Get full info about the current wallet state."""
        info = {
            "testnet": self.testnet,
            "has_key": self.key is not None,
            "has_mnemonic": self.mnemonics is not None,
        }

        if self.key:
            info["address_p2pkh"] = self.key.address
            info["address_segwit"] = self.key.segwit_address

        if self._derived_info:
            info["hd_address"] = self._derived_info["address"]
            info["hd_path"] = self._derived_info["path"]
            info["address_type"] = self.address_type
            info["address_index"] = self.address_index

        return info

    # ========================= Balance =========================

    def get_balance(self, currency: str = "btc") -> dict:
        """
        Get wallet balance.

        Returns:
            dict with balance_ui (BTC) and balance (satoshi).
        """
        if not self.key:
            raise ValueError("No key set.")

        balance_satoshi = int(self.key.get_balance("satoshi"))
        balance_btc = balance_satoshi / SATOSHI_PER_BTC

        return {
            "balance_ui": balance_btc,
            "balance": balance_satoshi,
        }

    @staticmethod
    def get_balance_by_address(address: str, testnet: bool = False) -> dict:
        """Get balance for any Bitcoin address."""
        if testnet:
            balance_satoshi = int(NetworkAPI.get_balance_testnet(address))
        else:
            balance_satoshi = int(NetworkAPI.get_balance(address))

        return {
            "balance_ui": balance_satoshi / SATOSHI_PER_BTC,
            "balance": balance_satoshi,
        }

    # ========================= Transfers =========================

    def transfer(
        self,
        to: str,
        amount: float,
        fee: Optional[int] = None,
        absolute_fee: bool = False,
        message: Optional[str] = None,
    ) -> str:
        """
        Transfer BTC.

        Args:
            to: Recipient Bitcoin address.
            amount: Amount in BTC.
            fee: Fee in satoshi/byte (auto if None). If absolute_fee=True, total fee in satoshi.
            absolute_fee: If True, 'fee' is the total fee.
            message: Optional OP_RETURN message (max 80 bytes).

        Returns:
            Transaction hash (txid).
        """
        if not self.key:
            raise ValueError("No key set.")

        outputs = [(to, amount, "btc")]

        if message:
            outputs.append((message, 0, "op_return"))

        kwargs = {}
        if fee is not None:
            kwargs["fee"] = fee

        tx_hash = self.key.send(outputs, **kwargs)
        return tx_hash

    def transfer_satoshi(
        self,
        to: str,
        amount: int,
        fee: Optional[int] = None,
        message: Optional[str] = None,
    ) -> str:
        """
        Transfer BTC in satoshi units.

        Args:
            to: Recipient address.
            amount: Amount in satoshi.
            fee: Fee in satoshi/byte.
            message: Optional OP_RETURN message.

        Returns:
            Transaction hash.
        """
        if not self.key:
            raise ValueError("No key set.")

        outputs = [(to, amount, "satoshi")]

        if message:
            outputs.append((message, 0, "op_return"))

        kwargs = {}
        if fee is not None:
            kwargs["fee"] = fee

        tx_hash = self.key.send(outputs, **kwargs)
        return tx_hash

    # ========================= UTXO / Transactions =========================

    def get_unspents(self) -> list:
        """Get unspent transaction outputs (UTXOs)."""
        if not self.key:
            raise ValueError("No key set.")
        return self.key.get_unspents()

    def get_transactions(self) -> list:
        """Get list of transaction hashes for the wallet."""
        if not self.key:
            raise ValueError("No key set.")
        return self.key.get_transactions()

    @staticmethod
    def get_transactions_by_address(address: str, testnet: bool = False) -> list:
        """Get transactions for any address."""
        if testnet:
            return NetworkAPI.get_transactions_testnet(address)
        return NetworkAPI.get_transactions(address)

    @staticmethod
    def get_unspents_by_address(address: str, testnet: bool = False) -> list:
        """Get UTXOs for any address."""
        if testnet:
            return NetworkAPI.get_unspent_testnet(address)
        return NetworkAPI.get_unspent(address)

    # ========================= Build / Estimate =========================

    def build_transaction(
        self,
        to: str,
        amount: float,
        fee: Optional[int] = None,
        message: Optional[str] = None,
    ) -> str:
        """
        Build a signed transaction without broadcasting.

        Returns:
            Raw signed transaction hex.
        """
        if not self.key:
            raise ValueError("No key set.")

        outputs = [(to, amount, "btc")]

        if message:
            outputs.append((message, 0, "op_return"))

        kwargs = {}
        if fee is not None:
            kwargs["fee"] = fee

        tx_hex = self.key.create_transaction(outputs, **kwargs)
        return tx_hex

    def estimate_fee(self, to: str, amount: float) -> dict:
        """
        Estimate transaction fee.

        Returns:
            dict with available balance, amount, and UTXO count.
        """
        if not self.key:
            raise ValueError("No key set.")

        unspents = self.key.get_unspents()
        total_available = sum(u.amount for u in unspents)
        amount_satoshi = int(amount * SATOSHI_PER_BTC)

        return {
            "available_satoshi": total_available,
            "amount_satoshi": amount_satoshi,
            "utxo_count": len(unspents),
        }
