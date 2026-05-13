from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from typing import Optional, Union, Dict, Any

SUN_PER_TRX = 1_000_000  # 1 TRX = 1,000,000 sun

TRX_NETWORKS = {
    "mainnet": "https://api.trongrid.io",
    "shasta": "https://api.shasta.trongrid.io",
    "nile": "https://nile.trongrid.io",
}

# Standard TRC20 ABI (transfer, balanceOf, approve, allowance, decimals, symbol)
TRC20_TRANSFER_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]


class TRX:
    """
    Tron (TRX) blockchain interface for OrbisPaySDK.
    Supports native TRX transfers, TRC20 token operations,
    balance queries, and wallet management via tronpy.
    """

    def __init__(
        self,
        network: str = "mainnet",
        private_key: Optional[str] = None,
        provider_url: Optional[str] = None,
        api_key: Optional[str] = None,
        build_tx: bool = False,
    ):
        """
        Args:
            network      (str): Network name — "mainnet", "shasta" (testnet), or "nile" (testnet).
                                Default: "mainnet".
            private_key  (str): Hex private key (64-char). Optional — can be set later.
            provider_url (str): Custom TronGrid/TronStack HTTP endpoint. Overrides network param.
            api_key      (str): TronGrid API key for higher rate limits. Optional.
            build_tx     (bool): If True, transfer_* methods return the signed transaction
                                 instead of broadcasting to the network.
        """
        # support embedded api_key in URL: https://api.trongrid.io?api_key=xxx
        if api_key is None and provider_url and "api_key=" in provider_url:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(provider_url)
            params = parse_qs(parsed.query)
            extracted = params.pop("api_key", [None])[0]
            clean_query = urlencode({k: v[0] for k, v in params.items()})
            provider_url = urlunparse(parsed._replace(query=clean_query))
            api_key = extracted

        self.network = network
        self.private_key = None
        self.address = None
        self.api_key = api_key
        self.build_tx = build_tx

        if provider_url:
            provider = HTTPProvider(provider_url, api_key=api_key) if api_key else HTTPProvider(provider_url)
        else:
            base_url = TRX_NETWORKS.get(network, TRX_NETWORKS["mainnet"])
            provider = HTTPProvider(base_url, api_key=api_key) if api_key else HTTPProvider(base_url)

        # attach retry adapter: auto-retry on 429/503 with backoff
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        _retry = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=[429, 503],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        provider.sess.mount("https://", HTTPAdapter(max_retries=_retry))
        provider.sess.mount("http://",  HTTPAdapter(max_retries=_retry))
        self.client = Tron(provider=provider)

        if private_key:
            self.set_private_key(private_key)

    def set_private_key(self, private_key: str):
        """
        Sets the private key used for signing transactions.
        Also derives and stores the corresponding wallet address.

        Args:
            private_key (str | PrivateKey): Hex string (64 chars) or PrivateKey instance.

        Raises:
            ValueError: If the type is unsupported.
        """
        if isinstance(private_key, str):
            self.private_key = PrivateKey(bytes.fromhex(private_key))
        elif isinstance(private_key, PrivateKey):
            self.private_key = private_key
        else:
            raise ValueError("private_key must be a hex string or PrivateKey instance.")
        self.address = self.private_key.public_key.to_base58check_address()

    def set_params(
        self,
        network: Optional[str] = None,
        private_key: Optional[str] = None,
        provider_url: Optional[str] = None,
        api_key: Optional[str] = None,
        build_tx: Optional[bool] = None,
    ):
        """
        Updates instance parameters at runtime without recreating the object.

        Args:
            network      (str):  New network name ("mainnet", "shasta", "nile").
            private_key  (str):  New hex private key.
            provider_url (str):  New custom HTTP provider URL (takes priority over network).
            api_key      (str):  New TronGrid API key.
            build_tx     (bool): New value for the build_tx flag.
        """
        if api_key:
            self.api_key = api_key
        if network:
            self.network = network
        if provider_url:
            provider = HTTPProvider(provider_url, api_key=self.api_key) if self.api_key else HTTPProvider(provider_url)
            self.client = Tron(provider=provider)
        elif network:
            self.client = Tron(network=network)
        if build_tx is not None:
            self.build_tx = build_tx
        if private_key:
            self.set_private_key(private_key)

    @staticmethod
    def gen_wallet() -> dict:
        """
        Generates a new random Tron wallet.

        Returns:
            dict: {
                "private_key": str,   # hex-encoded private key (64 chars)
                "address":     str,   # base58check address (starts with T)
                "public_key":  str,   # hex-encoded public key
            }
        """
        priv = PrivateKey.random()
        return {
            "private_key": priv.hex(),
            "address": priv.public_key.to_base58check_address(),
            "public_key": priv.public_key.hex(),
        }

    def get_address(self) -> str:
        """
        Returns the current wallet address derived from the stored private key.

        Returns:
            str: Base58check address (starts with T on mainnet).

        Raises:
            ValueError: If no private key has been set.
        """
        if not self.address:
            raise ValueError("Private key not set. Use set_private_key() first.")
        return self.address

    def sign_msg(self, msg: str, private_key: Optional[str] = None) -> str:
        """
        Signs an arbitrary message by hashing it and signing the hash.

        Args:
            msg         (str): Message to sign (encoded as UTF-8 bytes).
            private_key (str): Hex private key override. Falls back to self.private_key.

        Returns:
            str: Hex-encoded signature string.
        """
        from tronpy.keys import PrivateKey
        key = PrivateKey(bytes.fromhex(private_key or self.private_key))
        msg_bytes = msg.encode("utf-8")
        signature = key.sign_msg_hash(msg_bytes)
        return signature.hex()

    def get_balance(self, address: Optional[str] = None) -> dict:
        """
        Returns the TRX balance for an address.

        Args:
            address (str): Tron address to query. Defaults to the active wallet address.

        Returns:
            dict: { "balance_ui": float (TRX), "balance": int (sun) }
        """
        if not address:
            address = self.get_address()
        balance = self.client.get_account_balance(address)
        return {
            "balance_ui": float(balance),
            "balance": int(balance * SUN_PER_TRX),
        }

    def get_balance_batch(self, address_list: list) -> dict:
        """
        Fetches TRX balances for multiple addresses concurrently using a thread pool.

        Args:
            address_list (list[str]): List of Tron base58check addresses.

        Returns:
            dict: { address: {"balance_ui": float (TRX), "balance": int (sun)} }
                  Returns 0.0 / 0 on error for a given address.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def fetch(addr):
            try:
                balance = self.client.get_account_balance(addr)
                return addr, {"balance_ui": float(balance), "balance": int(balance * SUN_PER_TRX)}
            except Exception:
                return addr, {"balance_ui": 0.0, "balance": 0}

        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch, addr): addr for addr in address_list}
            for future in as_completed(futures):
                addr, data = future.result()
                results[addr] = data
        return results

    def transfer_native(self, to: str, amount: float, private_key: Optional[str] = None) -> dict:
        """
        Transfer native TRX.

        Args:
            to: Recipient address (base58check format, starts with T).
            amount: Amount in TRX.
            private_key: Optional hex private key (uses stored key if not provided).

        Returns:
            dict with tx hash and status.
        """
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()
        amount_sun = int(amount * SUN_PER_TRX)

        txn = (
            self.client.trx.transfer(from_addr, to, amount_sun)
            .build()
            .sign(key)
        )

        if self.build_tx:
            return txn

        result = txn.broadcast()

        return {
            "tx_hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "amount": amount,
            "to": to,
            "raw_result": result,
        }

    def transfer_trc20(
        self,
        contract_address: str,
        to: str,
        amount: float,
        decimals: Optional[int] = None,
        fee_limit: int = 10_000_000,
        private_key: Optional[str] = None,
    ) -> dict:
        """
        Transfer TRC20 tokens.

        Args:
            contract_address: TRC20 token contract address.
            to: Recipient address.
            amount: Amount in human-readable units (will be converted using decimals).
            decimals: Token decimals (auto-detected if None).
            fee_limit: Max TRX (in sun) allowed for energy consumption (default 10 TRX).
            private_key: Optional hex private key.

        Returns:
            dict with tx hash and status.
        """
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        contract = self.client.get_contract(contract_address)

        if decimals is None:
            decimals = contract.functions.decimals()

        raw_amount = int(amount * (10 ** decimals))

        txn = (
            contract.functions.transfer(to, raw_amount)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
            .sign(key)
        )

        if self.build_tx:
            return txn

        result = txn.broadcast()

        return {
            "tx_hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "amount": amount,
            "to": to,
            "token": contract_address,
            "raw_result": result,
        }

    def get_trc20_balance(
        self,
        contract_address: str,
        address: Optional[str] = None,
        decimals: Optional[int] = None,
    ) -> dict:
        """
        Returns the TRC20 token balance for an address.

        Args:
            contract_address (str): TRC20 contract address.
            address          (str): Owner address. Defaults to active wallet address.
            decimals         (int): Token decimals. Auto-detected from contract if not provided.

        Returns:
            dict: { "balance": int (raw), "balance_ui": float, "decimals": int }
        """
        if not address:
            address = self.get_address()

        contract = self.client.get_contract(contract_address)

        if decimals is None:
            decimals = contract.functions.decimals()

        raw_balance = contract.functions.balanceOf(address)

        return {
            "balance": raw_balance,
            "balance_ui": raw_balance / (10 ** decimals),
            "decimals": decimals,
        }

    def get_trc20_info(self, contract_address: str) -> dict:
        """
        Returns basic metadata for a TRC20 token contract.

        Args:
            contract_address (str): TRC20 contract address.

        Returns:
            dict: { "name": str, "symbol": str, "decimals": int }
        """
        contract = self.client.get_contract(contract_address)
        return {
            "name": contract.functions.name(),
            "symbol": contract.functions.symbol(),
            "decimals": contract.functions.decimals(),
        }

    def approve_trc20(
        self,
        contract_address: str,
        spender: str,
        amount: int,
        fee_limit: int = 10_000_000,
        private_key: Optional[str] = None,
    ) -> dict:
        """
        Approves a spender to transfer TRC20 tokens on behalf of the wallet.

        Args:
            contract_address (str): TRC20 token contract address.
            spender          (str): Address authorised to spend tokens.
            amount           (int): Raw allowance amount (decimals already applied).
            fee_limit        (int): Maximum energy cost in sun. Default: 10 TRX.
            private_key      (str): Hex private key override. Falls back to self.private_key.

        Returns:
            dict: { "tx_hash": str, "status": "success"|"failed", "spender": str,
                    "amount": int, "raw_result": dict }
        """
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        contract = self.client.get_contract(contract_address)

        txn = (
            contract.functions.approve(spender, amount)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
            .sign(key)
        )
        result = txn.broadcast()

        return {
            "tx_hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "spender": spender,
            "amount": amount,
            "raw_result": result,
        }

    def allowance_trc20(
        self,
        contract_address: str,
        owner: Optional[str] = None,
        spender: str = "",
    ) -> int:
        """
        Returns the current TRC20 spending allowance granted by owner to spender.

        Args:
            contract_address (str): TRC20 token contract address.
            owner            (str): Token owner address. Defaults to active wallet address.
            spender          (str): Address whose allowance to check.

        Returns:
            int: Remaining allowance in raw token units.
        """
        if not owner:
            owner = self.get_address()
        contract = self.client.get_contract(contract_address)
        return contract.functions.allowance(owner, spender)

    def get_transaction(self, tx_id: str) -> dict:
        """
        Returns the raw transaction object from the Tron node by transaction ID.

        Args:
            tx_id (str): Transaction hash / ID string.

        Returns:
            dict: Raw transaction dict as returned by tronpy.
        """
        return self.client.get_transaction(tx_id)

    def get_transaction_info(self, tx_id: str) -> dict:
        """
        Returns detailed transaction info including receipt, fee, and energy/bandwidth usage.

        Args:
            tx_id (str): Transaction hash / ID string.

        Returns:
            dict: Extended transaction info dict from tronpy (contains receipt, log, contractResult, etc.).
        """
        return self.client.get_transaction_info(tx_id)

    def get_account_resource(self, address: Optional[str] = None) -> dict:
        """
        Returns resource info for an account — bandwidth, energy, and freeze state.

        Args:
            address (str): Tron address to query. Defaults to the active wallet address.

        Returns:
            dict: Resource dict from tronpy with keys like freeNetUsed, NetLimit, EnergyLimit, etc.
        """
        if not address:
            address = self.get_address()
        return self.client.get_account_resource(address)

    def _resolve_key(self, private_key: Optional[str] = None) -> PrivateKey:
        """
        Resolves the PrivateKey to use for signing, from parameter or stored key.

        Args:
            private_key (str): Hex private key override. If None, uses self.private_key.

        Returns:
            PrivateKey: tronpy PrivateKey instance.

        Raises:
            ValueError: If no key is provided or stored.
        """
        if private_key:
            return PrivateKey(bytes.fromhex(private_key))
        if self.private_key:
            return self.private_key
        raise ValueError("No private key provided or stored.")
