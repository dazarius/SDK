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
    ):
        self.network = network
        self.private_key = None
        self.address = None
        self.api_key = api_key

        if provider_url:
            provider = HTTPProvider(provider_url, api_key=api_key) if api_key else HTTPProvider(provider_url)
            self.client = Tron(provider=provider)
        else:
            self.client = Tron(network=network)

        if private_key:
            self.set_private_key(private_key)

    def set_private_key(self, private_key: str):
        """Set the private key for signing transactions."""
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
    ):
        if api_key:
            self.api_key = api_key
        if network:
            self.network = network
        if provider_url:
            provider = HTTPProvider(provider_url, api_key=self.api_key) if self.api_key else HTTPProvider(provider_url)
            self.client = Tron(provider=provider)
        elif network:
            self.client = Tron(network=network)
        if private_key:
            self.set_private_key(private_key)

    @staticmethod
    def gen_wallet() -> dict:
        """Generate a new Tron wallet."""
        priv = PrivateKey.random()
        return {
            "private_key": priv.hex(),
            "address": priv.public_key.to_base58check_address(),
            "public_key": priv.public_key.hex(),
        }

    def get_address(self) -> str:
        """Get the current wallet address."""
        if not self.address:
            raise ValueError("Private key not set. Use set_private_key() first.")
        return self.address

    def get_balance(self, address: Optional[str] = None) -> dict:
        """
        Get TRX balance.

        Returns:
            dict with balance_ui (TRX) and balance (sun).
        """
        if not address:
            address = self.get_address()
        balance = self.client.get_account_balance(address)
        return {
            "balance_ui": float(balance),
            "balance": int(balance * SUN_PER_TRX),
        }

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
        Get TRC20 token balance.

        Returns:
            dict with balance (raw) and balance_ui (human-readable).
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
        """Get TRC20 token info (name, symbol, decimals)."""
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
        Approve TRC20 token spending.

        Args:
            contract_address: TRC20 token contract address.
            spender: Address allowed to spend tokens.
            amount: Raw amount to approve (with decimals already applied).
            fee_limit: Max energy cost in sun.
            private_key: Optional hex private key.
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
        """Check TRC20 allowance."""
        if not owner:
            owner = self.get_address()
        contract = self.client.get_contract(contract_address)
        return contract.functions.allowance(owner, spender)

    def get_transaction(self, tx_id: str) -> dict:
        """Get transaction details by ID."""
        return self.client.get_transaction(tx_id)

    def get_transaction_info(self, tx_id: str) -> dict:
        """Get detailed transaction info (including receipt, energy usage, etc.)."""
        return self.client.get_transaction_info(tx_id)

    def get_account_resource(self, address: Optional[str] = None) -> dict:
        """Get account resource info (bandwidth, energy)."""
        if not address:
            address = self.get_address()
        return self.client.get_account_resource(address)

    def _resolve_key(self, private_key: Optional[str] = None) -> PrivateKey:
        """Resolve private key from parameter or stored key."""
        if private_key:
            return PrivateKey(bytes.fromhex(private_key))
        if self.private_key:
            return self.private_key
        raise ValueError("No private key provided or stored.")
