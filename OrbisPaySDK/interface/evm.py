from web3 import Web3
import json
import OrbisPaySDK.utils as utils
from OrbisPaySDK.const import ERC20_SIGNATURES, __NULL_ADDRESS__, __ORBISPAY_DOMAIN_ABI, __MULTICALL3__,__MULTICALL3_ABI__
from eth_account import Account
from eth_account.messages import encode_defunct


from datetime import datetime, timezone





class EVM():
    def __init__(self, w3:Web3 = None, key = None, address = None, decimals = 18, contract = __NULL_ADDRESS__, currency = "ETH", build_tx: bool = False):
        """
        Args:
            w3       (Web3):  Connected Web3 instance. Can be set later via set_params.
            key      (str):   Hex private key (with or without 0x prefix). Optional.
            address  (str):   Wallet address. If not set, derived from key on demand.
            decimals (int):   Token decimals used in balance display. Default: 18.
            contract (str):   ERC20 contract address. Default: null address (native only).
            currency (str):   Currency symbol shown in balance dicts. Default: "ETH".
            build_tx (bool):  If True, sign_and_sand returns raw signed tx hex instead of broadcasting.
        """
        self.w3= w3
        self.key = key
        self.address = address
        self.decimals = decimals
        self.contract = contract
        self.currency = currency
        self.build_tx = build_tx

    def set_params(self, w3:Web3 = None, key:str = None, address:str = None, currency:str = None, build_tx: bool = None):
        """
        Updates instance parameters at runtime.

        Args:
            w3       (Web3): New connected Web3 instance.
            key      (str):  New hex private key.
            address  (str):  New wallet address.
            currency (str):  New currency symbol.
            build_tx (bool): New value for the build_tx flag.
        """
        if w3:
            self.w3 = w3
        if key:
            self.key = key
        if address:
            self.address = address
        if currency:
            self.currency = currency
        if build_tx is not None:
            self.build_tx = build_tx
    def gen_wallet(self):
        """
        Generates a new random EVM wallet.

        Returns:
            dict: { "address": str, "private_key": str (hex with 0x) }
        """
        account = Web3().eth.account.create()
        return {
            "address": account.address,
            "private_key": account.key.hex()
        }
    def parse_transaction(self, tx_hash: str, rpc_url: str = None) -> dict:
        """
        Fetches and parses a transaction by hash into a structured dict.
        Automatically fetches receipt and block for full context.

        Args:
            tx_hash (str): Transaction hash (hex string with 0x).
            rpc_url (str): RPC endpoint to use if self.w3 is not set.

        Returns:
            dict: {
                "tx_hash":                    str,
                "status":                     "success" | "failed" | "pending" | "error" | "not_found",
                "error":                      str | None,
                "from_address":               str,
                "to_address":                 str,
                "value_wei":                  int,
                "value_eth":                  str,
                "gas_limit":                  int,
                "gas_price_wei":              int,
                "gas_price_gwei":             str,
                "max_fee_per_gas":            int | None,   # EIP-1559
                "max_priority_fee_per_gas":   int | None,   # EIP-1559
                "nonce":                      int,
                "block_number":               int | None,
                "block_hash":                 str | None,
                "transaction_index":          int | None,
                "input_data":                 str,          # raw calldata hex
                "chain_id":                   int | None,
                "tx_type":                    int,          # 0=legacy, 2=EIP-1559
                "tx_category":                "native_transfer" | "contract_call" | "contract_creation",
                "method_id":                  str | None,   # first 4 bytes of calldata
                "gas_used":                   int,          # from receipt
                "effective_gas_price":        int,
                "fee_wei":                    int,
                "fee_eth":                    str,
                "logs":                       list[dict],
                "logs_count":                 int,
                "contract_address":           str | None,   # set on contract creation
                "timestamp":                  int | None,
                "confirmed_at":               str | None,
            }
        """
        if not self.w3:
            self.set_params(w3=Web3(Web3.HTTPProvider(rpc_url)))
        
        result = {
            "tx_hash": tx_hash,
            "status": "not_found",
            "error": None,
        }
        
        try:
            # Получаем данные транзакции
            tx = self.w3.eth.get_transaction(tx_hash)
            if tx is None:
                result["error"] = "Transaction not found"
                return result
            
            # Базовые данные транзакции
            result.update({
                "from_address": tx.get("from", ""),
                "to_address": tx.get("to", "") or "",  # None для contract creation
                "value_wei": tx.get("value", 0),
                "value_eth": str(self.w3.from_wei(tx.get("value", 0), "ether")),
                "gas_limit": tx.get("gas", 0),
                "gas_price_wei": tx.get("gasPrice", 0),
                "gas_price_gwei": str(self.w3.from_wei(tx.get("gasPrice", 0), "gwei")) if tx.get("gasPrice") else "0",
                "max_fee_per_gas": tx.get("maxFeePerGas"),
                "max_priority_fee_per_gas": tx.get("maxPriorityFeePerGas"),
                "nonce": tx.get("nonce", 0),
                "block_number": tx.get("blockNumber"),
                "block_hash": tx.get("blockHash").hex() if tx.get("blockHash") else None,
                "transaction_index": tx.get("transactionIndex"),
                "input_data": tx.get("input", "0x"),
                "chain_id": tx.get("chainId"),
                "tx_type": tx.get("type", 0),  # 0 = legacy, 2 = EIP-1559
            })
            
            input_data = tx.get("input", "0x")
            if tx.get("to") is None:
                result["tx_category"] = "contract_creation"
            elif input_data == "0x" or input_data == b"":
                result["tx_category"] = "native_transfer"
            else:
                result["tx_category"] = "contract_call"
                # Извлекаем method signature (первые 4 байта)
                if len(input_data) >= 10:
                    result["method_id"] = input_data[:10] if isinstance(input_data, str) else "0x" + input_data[:4].hex()
            
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    result.update({
                        "status": "success" if receipt.get("status") == 1 else "failed",
                        "gas_used": receipt.get("gasUsed", 0),
                        "effective_gas_price": receipt.get("effectiveGasPrice"),
                        "cumulative_gas_used": receipt.get("cumulativeGasUsed"),
                        "contract_address": receipt.get("contractAddress"),  # Для contract creation
                        "logs_count": len(receipt.get("logs", [])),
                        "logs_bloom": receipt.get("logsBloom").hex() if receipt.get("logsBloom") else None,
                    })
                    
                    # Рассчитываем комиссию
                    gas_used = receipt.get("gasUsed", 0)
                    effective_price = receipt.get("effectiveGasPrice") or tx.get("gasPrice", 0)
                    fee_wei = gas_used * effective_price
                    result["fee_wei"] = fee_wei
                    result["fee_eth"] = str(self.w3.from_wei(fee_wei, "ether"))
                    
                    # Парсим логи (events)
                    logs = receipt.get("logs", [])
                    parsed_logs = []
                    for log in logs:
                        parsed_logs.append({
                            "address": log.get("address", ""),
                            "topics": [t.hex() if isinstance(t, bytes) else t for t in log.get("topics", [])],
                            "data": log.get("data", "0x"),
                            "log_index": log.get("logIndex"),
                        })
                    result["logs"] = parsed_logs
            except Exception as e:
                result["status"] = "pending"
                result["receipt_error"] = str(e)
            
            if result.get("block_number"):
                try:
                    block = self.w3.eth.get_block(result["block_number"])
                    if block:
                        result["timestamp"] = block.get("timestamp")
                        result["confirmed_at"] = datetime.fromtimestamp(
                            block.get("timestamp", 0), tz=timezone.utc
                        ).strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    pass
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    
    
    
    def get_address(self) -> str:
        """
        Derives the wallet address from the stored private key.

        Returns:
            str: Checksummed EVM address.
        """
        acc = self.w3.eth.account.from_key(self.key)
        return acc.address
    def get_balance(self, address: str = None) -> dict:
        """
        Returns the native coin balance for an address.

        Args:
            address (str): EVM address to query. Defaults to self.address.

        Returns:
            dict: {
                "contract":   str,    # ERC20 contract address or null address
                "balance_ui": Decimal,  # human-readable amount
                "balance":    int,      # raw wei amount
                "decimals":   int,
                "symbol":     str,
            }
        """
        if address is None:
            address = self.address
        checksum_address = Web3.to_checksum_address(address)
        balance_wei = self.w3.eth.get_balance(checksum_address)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        return {
            "contract": self.contract,
            "balance_ui":balance_eth,
            "balance":balance_wei,
            "decimals": self.decimals,
            "symbol": self.currency
        }


    def get_balance_batch(self, address_list: list) -> dict:
        """
        Fetches native coin balances for multiple addresses in one Multicall3 call.
        Uses the aggregate3 function — batches up to 500 addresses per call.

        Args:
            address_list (list[str]): List of EVM addresses.

        Returns:
            dict: { address: float (balance in ETH/native coin) }
                  Returns 0.0 for failed individual calls.
        """
        GET_ETH_BALANCE = "0x4d2301cc"
        mc = self.w3.eth.contract(address=__MULTICALL3__, abi=__MULTICALL3_ABI__)
        
        def build_call(addr):
            padded = addr.lower().removeprefix("0x").zfill(64)
            return (__MULTICALL3__, True, bytes.fromhex(GET_ETH_BALANCE[2:] + padded))
        
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i+n]
        
        clean_res = {}
        for batch in chunk(address_list, 500):
            calls = [build_call(addr) for addr in batch]
            results = mc.functions.aggregate3(calls).call()
            for addr, (success, data) in zip(batch, results):
                clean_res[addr] = int(data.hex(), 16) / 10**18 if success and len(data) == 32 else 0.0
        
        return clean_res



    def ensure_checksum(self, w3: Web3, addr: str) -> str:
        """
        Converts an address to EIP-55 checksum format.

        Args:
            w3   (Web3): Web3 instance (unused, kept for signature compatibility).
            addr (str):  Raw EVM address string.

        Returns:
            str: Checksummed address.

        Raises:
            ValueError: If the address is invalid.
        """
        if addr is None:
            return None
        try:
            return Web3.to_checksum_address(addr)
        except Exception as e:
            raise ValueError(f"Invalid address '{addr}': {e}")
    def _native_transfer(self, to: str, amount: float):
        """
        Sends native coin (ETH/BNB/MATIC etc.) to an address and waits for confirmation.

        Args:
            to     (str):   Recipient address.
            amount (float): Amount in native coin units (e.g. ETH).

        Returns:
            tuple: (tx_hash_hex,) on success, False on failure.
        """
        checksum_to = Web3.to_checksum_address(to)
        
        nonce = self.w3.eth.get_transaction_count(self.address)
        gas_price = self.w3.eth.gas_price
        
        tx = {
            "from": self.address,
            "to": checksum_to,
            "value": self.w3.to_wei(amount, "ether"),
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": self.w3.eth.chain_id,
        }
        
        return self.sign_and_sand(tx)
    def sign_and_sand(self, tx: dict, key: str = None):
        """
        Signs a transaction dict, broadcasts it, and waits for confirmation.

        Args:
            tx  (dict): Unsigned transaction dict (from, to, value, gas, gasPrice, nonce, chainId).
            key (str):  Hex private key to sign with. Falls back to self.key if not provided.

        Returns:
            tuple | False: (tx_hash_hex,) on success, False if receipt status != 1.

        Raises:
            ValueError: If self.w3 is not initialised.
        """
        if not self.w3:
            raise ValueError("Web3 instance is not initialized in EVM class")
        
        # Если ключ не передан в метод, берем тот, что в self.key
        target_key = key if key else self.key

        # 1. Подписываем. Используем target_key!
        signed = self.w3.eth.account.sign_transaction(tx, target_key)

        if self.build_tx:
            return self.w3.to_hex(signed.raw_transaction)

        # 2. Отправляем
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        # 3. Ждем подтверждения
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if tx_receipt.status != 1:
            return False


        return self.w3.to_hex(tx_hash),
    def tx_to_human_view(self, tx_raw: dict) -> dict:
        """
        Converts a raw transaction dict into a human-readable summary.
        Decodes ERC20 transfer / approve calldata and Uniswap swap method IDs.

        Args:
            tx_raw (dict): Raw transaction dict as returned by web3.eth.get_transaction().

        Returns:
            dict: {
                "symbol":               str,           # "Native" or token symbol
                "amount":               Decimal | str, # amount in native/token units
                "action":               str,           # e.g. "Transfer", "Approve", "Contract Call"
                "from":                 str,
                "to":                   str,
                "contract_interaction": bool,
                "method_id":            str | None,    # first 4 bytes of calldata
                "to_contract":          str | None,    # contract address if interacted
                "description":          str | None,    # human description from ERC20_SIGNATURES
                "amount_raw":           int | None,    # raw token amount if decoded
                "error":                str | None,    # set if decoding failed
            }
        """
        # Начальные значения
        data_hex = tx_raw.get('data', '0x')
        value_native = tx_raw.get('value', 0)
        
        # Базовая структура meta
        meta = {
            "symbol": "Native",
            "amount": self.w3.from_wei(value_native, 'ether'),
            "action": "Transfer",
            "from": tx_raw.get('from'),
            "to": tx_raw.get('to'),
            "contract_interaction": False,
            "method_id": None
        }

        # Если данных нет — это обычный перевод ETH/BNB
        if not data_hex or data_hex == '0x':
            return meta

        # Если есть data — это работа с контрактом
        method_id = data_hex[:10].lower()
        meta["method_id"] = method_id
        meta["contract_interaction"] = True
        meta["to_contract"] = tx_raw.get('to') # Адрес самого контракта
        
        # Получаем инфо из твоего словаря сигнатур
        method_name, method_desc = self.ERC20_SIGNATURES.get(
            method_id, ("Contract Call", "Interaction with smart-contract")
        )
        meta["action"] = method_name
        meta["description"] = method_desc

        try:
            # ПАРСИНГ ПАРАМЕТРОВ (Transfer и Approve имеют одинаковую структуру аргументов)
            # Смещение: 10 (method_id) + 64 (первый аргумент) + 64 (второй аргумент)
            if method_id in ["0xa9059cbb", "0x095ea7b3"]:
                # Аргумент 1: Адрес (убираем лишние нули слева)
                # data[10:74] -> это 32 байта. Адрес занимает последние 20 байт (40 символов).
                raw_address = data_hex[10:74]
                clean_address = "0x" + raw_address[-40:]
                
                # Аргумент 2: Число (Amount/Value)
                raw_amount = data_hex[74:138]
                clean_amount = int(raw_amount, 16)
                
                meta["to"] = self.w3.to_checksum_address(clean_address)
                meta["amount_raw"] = clean_amount
                # Мы пока не знаем decimals токена здесь, поэтому пишем raw
                meta["amount"] = str(clean_amount) 

            # Для Swap (Uniswap V2 / Pancake) — обычно последние 32 байта это amountOutMin или подобное
            elif "0x7ff36ab5" in method_id:
                # Тут структура сложнее, но часто можно выцепить входящую сумму
                raw_amount = data_hex[74:138]
                meta["amount"] = str(int(raw_amount, 16))

        except Exception as e:
            meta["error"] = f"Decoding failed: {str(e)}"

        return meta
    def sign(self, tx: dict = None, key: str = None, w3: Web3 = None, send: bool = False):
        """
        Signs a transaction without broadcasting it.

        Args:
            tx   (dict): Unsigned transaction dict.
            key  (str):  Hex private key. Falls back to self.key.
            w3   (Web3): Web3 instance. Falls back to self.w3.
            send (bool): Unused flag (kept for API compatibility).

        Returns:
            SignedTransaction: Signed transaction object with .raw_transaction attribute.
        """
        if w3 is None:
            w3 = self.w3
        if key is None:
            key = self.key

        
        txid = w3.eth.account.sign_transaction(tx, key)
        


        return txid
            
    def send(self, tx) -> str | bool:
        """
        Broadcasts a pre-signed transaction and waits for confirmation.

        Args:
            tx (SignedTransaction): Signed transaction object (from sign()).

        Returns:
            str | False: Transaction hash hex string on success, False if status != 1.
        """
        tx_hash = self.w3.eth.send_raw_transaction(tx.raw_transaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
        if tx_receipt.status != 1:
            return False
        return f"{self.w3.to_hex(tx_hash)}"



    def sign_msg(self, msg: str, key: str = None, w3: Web3 = None) -> str:
        """
        Signs a plain text message using EIP-191 (eth_sign prefix).

        Args:
            msg (str):  Message to sign.
            key (str):  Hex private key. Falls back to self.key.
            w3  (Web3): Web3 instance. Falls back to self.w3.

        Returns:
            str: 65-byte ECDSA signature as a hex string (with 0x).
        """
        if w3 is None:
            w3 = self.w3
        if key is None:
            key = self.key

        message = w3.eth.account.sign_message(
            encode_defunct(text=msg),
            private_key=key
        )
        return message.signature.hex()  


class DomainService:
    """
    Python client for interacting with the DomainService smart contract.

    Usage:
        ds = DomainService(
            rpc_url="https://mainnet.infura.io/v3/YOUR_KEY",
            contract_address="0xYourContractAddress",
            private_key="0xYourPrivateKey"   # optional, needed for write calls
        )
        ds.register("mysite", "ipfs://Qm...", years=1)
        info = ds.get_domain("mysite")
    """

    def __init__(self, rpc_url: str, contract_address: str, private_key: str = None):
        """
        Args:
            rpc_url:          HTTP RPC endpoint for the chain where DomainService is deployed.
            contract_address: Deployed DomainService contract address.
            private_key:      Hex private key for write operations. Optional for read-only use.

        Raises:
            ConnectionError: If unable to connect to the RPC endpoint.
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=__ORBISPAY_DOMAIN_ABI
        )

        self.private_key = private_key
        self.account = None

        if private_key:
            self.account = Account.from_key(private_key)

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _send_tx(self, fn, value_wei: int = 0) -> str:
        """
        Builds, signs, and broadcasts a contract write transaction.

        Args:
            fn        (ContractFunction): Prepared contract function call (e.g. contract.functions.register(...)).
            value_wei (int):              Native coin value attached to the transaction (default 0).

        Returns:
            str: Transaction hash hex string.

        Raises:
            ValueError: If no private key is set.
        """
        if not self.account:
            raise ValueError("Private key is required for write operations")

        tx = fn.build_transaction({
            "from":     self.account.address,
            "value":    value_wei,
            "nonce":    self.w3.eth.get_transaction_count(self.account.address),
            "gas":      fn.estimate_gas({"from": self.account.address, "value": value_wei}),
            "gasPrice": self.w3.eth.gas_price,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.to_hex(tx_hash)

    def _wait(self, tx_hash: str) -> dict:
        """
        Blocks until a transaction is included in a block.

        Args:
            tx_hash (str): Transaction hash to wait for.

        Returns:
            dict: Transaction receipt from web3.
        """
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    # ─── Read functions ───────────────────────────────────────────────────────

    def get_domain(self, label: str) -> dict:
        """
        Returns the full on-chain record for a .orbis domain.

        Args:
            label (str): Domain label without the .orbis suffix (e.g. "mysite").

        Returns:
            dict: { label, full_name, owner, record, registered_at, expires_at,
                    transfer_locked, active }
        """
        owner, record, registered_at, expires_at, transfer_locked, active = \
            self.contract.functions.getDomain(label).call()
        return {
            "label":          label,
            "full_name":      f"{label}.orbis",
            "owner":          owner,
            "record":         record,
            "registered_at":  registered_at,
            "expires_at":     expires_at,
            "transfer_locked": transfer_locked,
            "active":         active,
        }

    def is_available(self, label: str) -> bool:
        """
        Checks if a .orbis domain label is available for registration.

        Args:
            label (str): Domain label without .orbis suffix.

        Returns:
            bool: True if available, False if already registered.
        """
        return self.contract.functions.isAvailable(label).call()

    def calculate_fee(self, label: str, years: int) -> dict:
        """
        Calculates the registration or renewal fee for a domain.

        Args:
            label (str): Domain label (length determines the price tier).
            years (int): Number of years to register/renew.

        Returns:
            dict: { "wei": int, "eth": float }
        """
        wei = self.contract.functions.calculateFee(label, years).call()
        return {
            "wei": wei,
            "eth": float(Web3.from_wei(wei, "ether")),
        }

    def get_owner_domains(self, address: str) -> list[str]:
        """
        Returns all .orbis domain labels owned by an address.

        Args:
            address (str): EVM address to query.

        Returns:
            list[str]: List of domain labels (without .orbis suffix).
        """
        return self.contract.functions.getOwnerDomains(
            Web3.to_checksum_address(address)
        ).call()

    def get_full_name(self, label: str) -> str:
        """
        Returns the full domain name with .orbis suffix as stored on-chain.

        Args:
            label (str): Domain label without suffix.

        Returns:
            str: e.g. "mysite.orbis"
        """
        return self.contract.functions.getFullName(label).call()

    def get_prices(self) -> dict:
        """
        Returns the current domain pricing tiers from the contract.

        Returns:
            dict: {
                "3_chars": { "wei": int, "eth": float },
                "4_chars": { "wei": int, "eth": float },
                "5_plus":  { "wei": int, "eth": float },
            }
        """
        p3 = self.contract.functions.price3chars().call()
        p4 = self.contract.functions.price4chars().call()
        p5 = self.contract.functions.price5plus().call()
        return {
            "3_chars": {"wei": p3, "eth": float(Web3.from_wei(p3, "ether"))},
            "4_chars": {"wei": p4, "eth": float(Web3.from_wei(p4, "ether"))},
            "5_plus":  {"wei": p5, "eth": float(Web3.from_wei(p5, "ether"))},
        }

    def get_contract_owner(self) -> str:
        """
        Returns the address of the contract owner (admin).

        Returns:
            str: Checksummed owner address.
        """
        return self.contract.functions.contractOwner().call()

    # ─── Write functions ──────────────────────────────────────────────────────

    def register(self, label: str, record: str, years: int, wait: bool = True) -> str:
        """
        Registers a new .orbis domain. Fee is calculated automatically.

        Args:
            label  (str):  Domain label to register.
            record (str):  IPFS/IP record to associate (e.g. "ipfs://Qm...").
            years  (int):  Registration duration in years.
            wait   (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        fee = self.contract.functions.calculateFee(label, years).call()
        tx_hash = self._send_tx(
            self.contract.functions.register(label, record, years),
            value_wei=fee
        )
        print(f"[register] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[register] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def renew(self, label: str, years: int, wait: bool = True) -> str:
        """
        Renews an existing .orbis domain. Fee is calculated automatically.

        Args:
            label (str):  Domain label to renew.
            years (int):  Number of years to extend.
            wait  (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        fee = self.contract.functions.calculateFee(label, years).call()
        tx_hash = self._send_tx(
            self.contract.functions.renew(label, years),
            value_wei=fee
        )
        print(f"[renew] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[renew] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def update_record(self, label: str, new_record: str, wait: bool = True) -> str:
        """
        Updates the IPFS/IP record associated with an owned domain.

        Args:
            label      (str):  Domain label to update.
            new_record (str):  New record value (e.g. "ipfs://Qm..." or an IP address).
            wait       (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.updateRecord(label, new_record)
        )
        print(f"[update_record] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[update_record] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def transfer(self, label: str, to_address: str, wait: bool = True) -> str:
        """
        Transfers ownership of a .orbis domain to another address.
        Domain must not have transfer_locked = True.

        Args:
            label      (str):  Domain label to transfer.
            to_address (str):  Recipient EVM address.
            wait       (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.transfer(label, Web3.to_checksum_address(to_address))
        )
        print(f"[transfer] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[transfer] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def set_transfer_lock(self, label: str, locked: bool, wait: bool = True) -> str:
        """
        Enables or disables the transfer lock on an owned domain.

        Args:
            label  (str):  Domain label.
            locked (bool): True to lock transfers, False to unlock.
            wait   (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.setTransferLock(label, locked)
        )
        print(f"[set_transfer_lock] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[set_transfer_lock] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def release(self, label: str, wait: bool = True) -> str:
        """
        Releases an expired domain back to the public pool.
        Can only be called on domains past their expiry date.

        Args:
            label (str):  Expired domain label to release.
            wait  (bool): If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.release(label)
        )
        print(f"[release] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[release] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    # ─── Admin functions ──────────────────────────────────────────────────────

    def set_prices(
        self,
        price_3chars_eth: float,
        price_4chars_eth: float,
        price_5plus_eth: float,
        wait: bool = True
    ) -> str:
        """
        Updates the domain pricing tiers. Contract owner only.

        Args:
            price_3chars_eth (float): Price for 3-character domains in ETH.
            price_4chars_eth (float): Price for 4-character domains in ETH.
            price_5plus_eth  (float): Price for 5+ character domains in ETH.
            wait             (bool):  If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.setPrices(
                Web3.to_wei(price_3chars_eth, "ether"),
                Web3.to_wei(price_4chars_eth, "ether"),
                Web3.to_wei(price_5plus_eth,  "ether"),
            )
        )
        print(f"[set_prices] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[set_prices] confirmed in block {receipt['blockNumber']}")
        return tx_hash

    def withdraw(self, to_address: str, amount_eth: float, wait: bool = True) -> str:
        """
        Withdraws ETH collected from registrations. Contract owner only.

        Args:
            to_address (str):   Recipient address for the withdrawn ETH.
            amount_eth (float): Amount in ETH to withdraw.
            wait       (bool):  If True, blocks until confirmed. Default: True.

        Returns:
            str: Transaction hash hex string.
        """
        tx_hash = self._send_tx(
            self.contract.functions.withdraw(
                Web3.to_checksum_address(to_address),
                Web3.to_wei(amount_eth, "ether")
            )
        )
        print(f"[withdraw] tx sent: {tx_hash}")
        if wait:
            receipt = self._wait(tx_hash)
            print(f"[withdraw] confirmed in block {receipt['blockNumber']}")
        return tx_hash