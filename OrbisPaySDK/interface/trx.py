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
            return {"tx": txn}

        result = txn.broadcast()

        return {
            "tx": result.get("txid", ""),
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
            return {"tx": txn}

        result = txn.broadcast()

        return {
            "tx": result.get("txid", ""),
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
            "tx": result.get("txid", ""),
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

    # ── Receipt / parsing ─────────────────────────────────────────────────────

    def parse_receipt_gas(self, tx_id: str) -> dict:
        """
        Extracts energy, bandwidth, and fee breakdown for a confirmed transaction.

        TRON fee structure:
          fee = energy_fee + net_fee
          energy  ≈ EVM gas_used   (compute cost, charged in TRX if no frozen energy)
          net     ≈ tx byte size   (bandwidth, free up to daily limit)

        Args:
            tx_id (str): Transaction ID / hash string.

        Returns:
            dict: {
                "fee_sun":         int,    # total fee in sun   (≈ EVM fee_wei / SOL fee_lamports)
                "fee_trx":         float,  # total fee in TRX   (≈ EVM fee_eth  / SOL fee_sol)
                "energy_usage":    int,    # energy consumed    (≈ EVM gas_used)
                "energy_fee_sun":  int,    # TRX cost for energy in sun
                "energy_fee_trx":  float,
                "net_usage":       int,    # bandwidth bytes consumed
                "net_fee_sun":     int,    # TRX cost for bandwidth in sun
                "net_fee_trx":     float,
                "block_number":    int,    # (≈ EVM block_number / SOL slot)
                "status":          str,    # "SUCCESS" or error code
            }
        """
        info    = self.client.get_transaction_info(tx_id)
        receipt = info.get("receipt", {})

        fee_sun        = int(info.get("fee", 0) or 0)
        energy_usage   = int(receipt.get("energy_usage_total") or receipt.get("energy_usage") or 0)
        energy_fee_sun = int(receipt.get("energy_fee", 0) or 0)
        net_usage      = int(receipt.get("net_usage", 0) or 0)
        net_fee_sun    = int(receipt.get("net_fee", 0) or 0)

        return {
            "fee_sun":        fee_sun,
            "fee_trx":        fee_sun        / SUN_PER_TRX,
            "energy_usage":   energy_usage,
            "energy_fee_sun": energy_fee_sun,
            "energy_fee_trx": energy_fee_sun / SUN_PER_TRX,
            "net_usage":      net_usage,
            "net_fee_sun":    net_fee_sun,
            "net_fee_trx":    net_fee_sun    / SUN_PER_TRX,
            "block_number":   info.get("blockNumber"),
            "status":         receipt.get("result", "SUCCESS"),
        }

    def tx_to_human_view(self, tx_id: str) -> dict:
        """
        Converts a transaction ID into a human-readable summary dict.
        Fetches both raw transaction and receipt info.

        Args:
            tx_id (str): Transaction ID / hash string.

        Returns:
            dict: {
                "action":           str,         # "TRX Transfer" | "TRC20 Transfer" | "TRC20 Approve" | ...
                "from":             str | None,
                "to":               str | None,
                "amount":           float,       # human units (TRX or raw token amount)
                "symbol":           str,         # "TRX" or "TRC20@<contract[:8]>…"
                "contract_address": str | None,
                "fee_trx":          float,
                "block_number":     int | None,
                "status":           str,
                "summary":          str,
            }
        """
        tx      = self.client.get_transaction(tx_id)
        info    = self.client.get_transaction_info(tx_id)
        receipt = info.get("receipt", {})

        fee_sun  = int(info.get("fee", 0) or 0)
        status   = receipt.get("result", "SUCCESS")
        raw_data = tx.get("raw_data", {})
        contracts = raw_data.get("contract", [])

        result: Dict[str, Any] = {
            "action":           "Unknown",
            "from":             None,
            "to":               None,
            "amount":           0.0,
            "symbol":           "TRX",
            "contract_address": None,
            "fee_trx":          fee_sun / SUN_PER_TRX,
            "block_number":     info.get("blockNumber"),
            "status":           status,
            "summary":          "",
        }

        if not contracts:
            return result

        ctype = contracts[0].get("type", "")
        value = contracts[0].get("parameter", {}).get("value", {})

        def _addr(raw) -> Optional[str]:
            if not raw:
                return None
            s = raw if isinstance(raw, str) else raw.hex()
            if len(s) == 42 and s.startswith("41"):
                try:
                    from tronpy.keys import to_base58check_address
                    return to_base58check_address(bytes.fromhex(s))
                except Exception:
                    pass
            return s

        SELECTORS = {
            "a9059cbb": "TRC20 Transfer",
            "095ea7b3": "TRC20 Approve",
            "23b872dd": "TRC20 TransferFrom",
        }

        if ctype == "TransferContract":
            result["action"] = "TRX Transfer"
            result["from"]   = _addr(value.get("owner_address"))
            result["to"]     = _addr(value.get("to_address"))
            result["amount"] = int(value.get("amount", 0)) / SUN_PER_TRX
            result["symbol"] = "TRX"

        elif ctype == "TriggerSmartContract":
            ca = _addr(value.get("contract_address"))
            result["contract_address"] = ca
            result["from"] = _addr(value.get("owner_address"))
            data     = value.get("data", "")
            selector = data[:8].lower() if len(data) >= 8 else ""
            result["action"] = SELECTORS.get(selector, "Contract Call")

            if selector == "a9059cbb" and len(data) >= 136:
                result["to"]     = _addr("41" + data[32:72])
                result["amount"] = int(data[72:136], 16)
                result["symbol"] = f"TRC20@{(ca or '')[:8]}…"

        elif ctype == "TransferAssetContract":
            result["action"] = "TRC10 Transfer"
            result["from"]   = _addr(value.get("owner_address"))
            result["to"]     = _addr(value.get("to_address"))
            result["amount"] = int(value.get("amount", 0))
            result["symbol"] = value.get("asset_name", "TRC10")

        result["summary"] = (
            f"{result['action']} {result['amount']} {result['symbol']} "
            f"from {(result['from'] or '')[:8]}… → {(result['to'] or '')[:8]}… | "
            f"status: {status} | fee: {result['fee_trx']:.6f} TRX"
        )
        return result

    def parse_raw_tx(self, tx) -> dict:
        """
        Parses a raw tronpy transaction locally — no network call.
        Accepts a tronpy Transaction object (from build_tx=True) or a raw dict.

        Args:
            tx: tronpy Transaction object or dict with 'raw_data' key.

        Returns:
            dict: {
                "tx_id":             str | None,
                "tx_type":           str,         # "TRX Transfer" | "TRC20 Transfer" | "Contract Call" | ...
                "from":              str | None,
                "to":                str | None,
                "amount_sun":        int,
                "amount_trx":        float,
                "contract_type":     str,
                "contract_address":  str | None,
                "function_selector": str | None,  # decoded name or raw 4-byte hex
                "data_hex":          str | None,
                "expiration":        int | None,
                "fee_limit_sun":     int,
            }
        """
        if hasattr(tx, "raw_data"):
            raw_data = tx.raw_data
            tx_id    = getattr(tx, "txid", None)
        elif isinstance(tx, dict):
            raw_data = tx.get("raw_data", {})
            tx_id    = tx.get("txID")
        else:
            raise ValueError(f"Unsupported tx type: {type(tx)}")

        contracts  = raw_data.get("contract", [])
        fee_limit  = int(raw_data.get("fee_limit", 0) or 0)
        expiration = raw_data.get("expiration")

        result: Dict[str, Any] = {
            "tx_id":             tx_id,
            "tx_type":           "Unknown",
            "from":              None,
            "to":                None,
            "amount_sun":        0,
            "amount_trx":        0.0,
            "contract_type":     "",
            "contract_address":  None,
            "function_selector": None,
            "data_hex":          None,
            "expiration":        expiration,
            "fee_limit_sun":     fee_limit,
        }

        if not contracts:
            return result

        ctype = contracts[0].get("type", "")
        value = contracts[0].get("parameter", {}).get("value", {})
        result["contract_type"] = ctype

        def _addr(raw) -> Optional[str]:
            if not raw:
                return None
            s = raw if isinstance(raw, str) else raw.hex()
            if len(s) == 42 and s.startswith("41"):
                try:
                    from tronpy.keys import to_base58check_address
                    return to_base58check_address(bytes.fromhex(s))
                except Exception:
                    pass
            return s

        SELECTORS = {
            "a9059cbb": "transfer(address,uint256)",
            "095ea7b3": "approve(address,uint256)",
            "23b872dd": "transferFrom(address,address,uint256)",
            "70a08231": "balanceOf(address)",
            "dd62ed3e": "allowance(address,address)",
        }

        if ctype == "TransferContract":
            result["tx_type"]    = "TRX Transfer"
            result["from"]       = _addr(value.get("owner_address"))
            result["to"]         = _addr(value.get("to_address"))
            result["amount_sun"] = int(value.get("amount", 0))
            result["amount_trx"] = result["amount_sun"] / SUN_PER_TRX

        elif ctype == "TriggerSmartContract":
            result["contract_address"] = _addr(value.get("contract_address"))
            result["from"] = _addr(value.get("owner_address"))
            data     = value.get("data", "")
            selector = data[:8].lower() if len(data) >= 8 else ""
            result["data_hex"]          = data
            result["function_selector"] = SELECTORS.get(selector, selector or None)

            if selector == "a9059cbb":
                result["tx_type"] = "TRC20 Transfer"
                if len(data) >= 136:
                    result["to"]         = _addr("41" + data[32:72])
                    result["amount_sun"] = int(data[72:136], 16)
            elif selector == "095ea7b3":
                result["tx_type"] = "TRC20 Approve"
            else:
                result["tx_type"] = "Contract Call"

        elif ctype == "TransferAssetContract":
            result["tx_type"]    = "TRC10 Transfer"
            result["from"]       = _addr(value.get("owner_address"))
            result["to"]         = _addr(value.get("to_address"))
            result["amount_sun"] = int(value.get("amount", 0))

        return result

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
