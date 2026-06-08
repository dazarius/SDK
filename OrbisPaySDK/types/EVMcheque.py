import OrbisPaySDK
from OrbisPaySDK.const import __SHADOWPAY_ABI__ERC20__, __ALLOW_CHAINS__, __SHADOWPAY_CONTRACT_ADDRESS__ERC20__
from web3 import Web3
from typing import Optional
from eth_utils import keccak
import time

try:
    from web3.middleware import ExtraDataToPOAMiddleware as _POAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware as _POAMiddleware  # web3 v5


def _inject_poa(w3: Web3) -> None:
    """Inject POA middleware if not already present (needed for BSC, Polygon, etc.)."""
    for mw in w3.middleware_onion:
        if mw is _POAMiddleware or (hasattr(mw, 'func') and mw.func is _POAMiddleware):
            return
    w3.middleware_onion.inject(_POAMiddleware, layer=0)

class Cheque:
    def __init__(self, w3: Optional[Web3] = None, private_key: Optional[str] = None, ABI=__SHADOWPAY_ABI__ERC20__, allowed_chains=__ALLOW_CHAINS__, retunrn_build_tx: bool = False, address: Optional[str] = None):
        self.w3 = w3
        self.amount = None
        self.token = None
        self.private_key = private_key
        self.ABI = ABI
        self.address = address
        self.return_build_tx = retunrn_build_tx
        self.allowed_chains = allowed_chains
        if self.w3 is not None:
            self.__allow__()

    @staticmethod
    def _generate_cheque_id(sender: str, salt: str) -> bytes:
        raw = f"{sender}:{salt}:{time.time()}".encode("utf-8")
        return keccak(raw)

    @staticmethod
    def _normalize_cheque_id(cheque_id) -> bytes:
        """Normalise a user-supplied cheque_id (bytes or hex string) to bytes32."""
        if isinstance(cheque_id, bytes):
            return cheque_id[:32].rjust(32, b"\x00")
        if isinstance(cheque_id, str):
            return Web3.to_bytes(hexstr=cheque_id).rjust(32, b"\x00")
        raise ValueError("cheque_id must be bytes or a hex string")

    def get_id(self, tx):
        if isinstance(tx, str):
            try:
                tx = self.w3.eth.wait_for_transaction_receipt(tx)
            except Exception as e:
                print(f"Failed to get transaction receipt: {str(e)}")
                return False
        try:
            logs = self.contract.events.ChequeCreated().process_receipt(tx)
            cheque_id = logs[0]["args"]["id"]
            return cheque_id.hex()
        except Exception as e:
            print(f"Failed to get cheque ID from transaction receipt: {str(e)}")
            return False

    def __allow__(self):
        _inject_poa(self.w3)
        print("Checking if chain is allowed", self.w3.eth.chain_id)
        for chain in self.allowed_chains:
            if chain == self.w3.eth.chain_id:
                self.get_contract_for_chain(chain_id=self.w3.eth.chain_id)
                return True
        raise ValueError(f"Chain {str(self.w3.eth.chain_id)} is not allowed. Allowed chains are: {self.allowed_chains}")

    def get_contract_for_chain(self, chain_id: str):
        chain_id = int(chain_id)
        for key, value in __SHADOWPAY_CONTRACT_ADDRESS__ERC20__.items():
            print("Checking address", value, "for chain_id", chain_id)
            if key == chain_id:
                contract_address = Web3.to_checksum_address(value)
                self.contract = self.w3.eth.contract(address=contract_address, abi=__SHADOWPAY_ABI__ERC20__)
                return self.contract
        raise ValueError(f"Chain {chain_id} is not supported. Supported chains are: {list(__SHADOWPAY_CONTRACT_ADDRESS__ERC20__.keys())}")

    async def get_address(self):
        if self.address:
            return self.address
        elif self.w3:
            return self.w3.eth.default_account
        else:
            raise ValueError("No address provided or Web3 instance is not set")

    def set_parameters(self, chain_id: Optional[str] = None, w3: Optional[Web3] = None, amount: Optional[int] = None, private_key: Optional[str] = None, token: Optional[str] = None, address: Optional[str] = None, contract: Optional[str] = None, ABI=__SHADOWPAY_ABI__ERC20__):
        if w3:
            self.w3 = w3
            _inject_poa(self.w3)
            if contract is None:
                self.get_contract_for_chain(chain_id=chain_id or self.w3.eth.chain_id)
        if contract:
            self.contract = self.w3.eth.contract(address=contract, abi=ABI)
        if amount:
            self.amount = amount
        if private_key:
            self.private_key = private_key
            self.address = Web3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)
        if token:
            self.token = token
        if address:
            self.address = address

    def __convert__(self):
        return self.w3.to_wei(self.amount, 'ether')

    # ── Native ETH cheque — single recipient ──────────────────────────────────

    async def InitNativeCheque(self, amount, receiver: str, private_key: Optional[str] = None, cheque_id=None):
        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        receiver_cs = Web3.to_checksum_address(receiver)
        cheque_id = self._normalize_cheque_id(cheque_id) if cheque_id else self._generate_cheque_id(address, f"{receiver_cs}:{amount}")
        value_wei = self.w3.to_wei(amount, 'ether')

        estimated_gas = self.contract.functions.InitNativeCheque(
            cheque_id, receiver_cs
        ).estimate_gas({
            'from': address,
            'value': value_wei,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitNativeCheque(
            cheque_id, receiver_cs
        ).build_transaction({
            'from': address,
            'value': value_wei,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.w3.eth.chain_id,
        })
        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id.hex()}

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {"tx": txn_hash.hex(), "id": cheque_id.hex()}

    async def CashOutNativeCheque(self, cheque_id: str, private_key: Optional[str] = None):
        key = private_key or self.private_key
        account = self.w3.eth.account.from_key(key)
        sender_address = account.address

        nonce = self.w3.eth.get_transaction_count(sender_address)
        latest_block = self.w3.eth.get_block('latest')
        supports_eip1559 = 'baseFeePerGas' in latest_block

        tx_common = {
            'from': sender_address,
            'nonce': nonce,
            'gas': 100_000,
        }
        if supports_eip1559:
            base_fee = latest_block['baseFeePerGas']
            priority_fee = self.w3.to_wei(2, 'gwei')
            tx_common.update({
                'maxFeePerGas': base_fee + priority_fee * 2,
                'maxPriorityFeePerGas': priority_fee,
            })
        else:
            tx_common.update({'gasPrice': self.w3.to_wei('5', 'gwei')})

        txn = self.contract.functions.CashOutNativeCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction(tx_common)

        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id}

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"tx": tx_hash.hex(), "id": cheque_id}

    # ── Native ETH cheque — multi recipient ───────────────────────────────────

    async def InitMultiCheque(self, amount, receivers: list, private_key: Optional[str] = None, cheque_id=None):
        if not isinstance(receivers, list) or len(receivers) == 0:
            raise ValueError("Receivers must be a non-empty list of addresses")

        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        receivers_cs = [Web3.to_checksum_address(addr) for addr in receivers]
        cheque_id = self._normalize_cheque_id(cheque_id) if cheque_id else self._generate_cheque_id(address, f"{receivers_cs}:{amount}")
        value_wei = self.w3.to_wei(amount, 'ether')

        estimated_gas = self.contract.functions.InitMultiCheque(
            cheque_id, receivers_cs
        ).estimate_gas({
            'from': address,
            'value': value_wei,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitMultiCheque(
            cheque_id, receivers_cs
        ).build_transaction({
            'from': address,
            'value': value_wei,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.w3.eth.chain_id,
        })
        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id.hex()}

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {"tx": txn_hash.hex(), "id": cheque_id.hex()}

    async def CashOutMultiCheque(self, cheque_id: str, private_key: str = None):
        if not private_key:
            private_key = self.private_key

        account = self.w3.eth.account.from_key(private_key)
        sender_address = account.address or self.address
        nonce = self.w3.eth.get_transaction_count(sender_address)

        latest_block = self.w3.eth.get_block('latest')
        supports_eip1559 = 'baseFeePerGas' in latest_block

        tx_common = {
            'from': sender_address,
            'nonce': nonce,
            'gas': 300_000,
        }

        if supports_eip1559:
            base_fee = latest_block['baseFeePerGas']
            priority_fee = self.w3.to_wei(2, 'gwei')
            tx_common.update({
                'maxFeePerGas': base_fee + priority_fee * 2,
                'maxPriorityFeePerGas': priority_fee,
            })
        else:
            tx_common.update({'gasPrice': self.w3.to_wei('5', 'gwei')})

        txn = self.contract.functions.CashOutMultiCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction(tx_common)

        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id}

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"tx": tx_hash.hex(), "id": cheque_id}

    # ── ERC-20 token cheque ────────────────────────────────────────────────────

    async def InitTokenCheque(self, token_address: str, amount, receiver: str, private_key: Optional[str] = None, cheque_id=None):
        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        token_cs = Web3.to_checksum_address(token_address)
        receiver_cs = Web3.to_checksum_address(receiver)
        cheque_id = self._normalize_cheque_id(cheque_id) if cheque_id else self._generate_cheque_id(address, f"{token_cs}:{amount}:{receiver_cs}")

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3, build_tx=True)
        erc20.set_params(token_address=token_cs)
        current_allowance = erc20.allowance(spender=self.contract.address, owner=address)
        if current_allowance < amount:
            approve = erc20.approve(
                spender=self.contract.address,
                amount=amount,
                private_key=key,
                conveted_amount=False,
            )
            if approve:
                return {"need_approve": approve}

        estimated_gas = self.contract.functions.InitTokenCheque(
            cheque_id, token_cs, amount, receiver_cs
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitTokenCheque(
            cheque_id, token_cs, amount, receiver_cs
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id.hex()}

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {"tx": txn_hash.hex(), "id": cheque_id.hex()}

    async def CashOutTokenCheque(self, cheque_id: str, private_key: Optional[str] = None):
        if private_key is None:
            private_key = self.private_key

        account = self.w3.eth.account.from_key(private_key)
        sender_address = account.address or self.address

        estimated_gas = self.contract.functions.CashOutTokenCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).estimate_gas({
            'from': sender_address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.CashOutTokenCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction({
            'from': sender_address,
            'nonce': self.w3.eth.get_transaction_count(sender_address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id}

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"tx": tx_hash.hex(), "id": cheque_id}

    # ── Swap cheque ────────────────────────────────────────────────────────────

    async def InitTokenChequeSwap(self, token_in: str, amount_in, token_out: str, amount_out, receiver: str, private_key: Optional[str] = None, cheque_id=None):
        key = private_key or self.private_key
        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        token_in_cs = Web3.to_checksum_address(token_in)
        token_out_cs = Web3.to_checksum_address(token_out)
        receiver_cs = Web3.to_checksum_address(receiver)
        cheque_id = self._normalize_cheque_id(cheque_id) if cheque_id else self._generate_cheque_id(address, f"{token_in_cs}:{amount_in}:{token_out_cs}:{amount_out}:{receiver_cs}")

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_in_cs)
        current_allowance = erc20.allowance(spender=self.contract.address, owner=address)
        if current_allowance < amount_in:
            approve = erc20.approve(
                spender=self.contract.address,
                amount=amount_in,
                private_key=key,
                conveted_amount=False,
            )
            if not approve:
                return False

        estimated_gas = self.contract.functions.InitSwapCheque(
            cheque_id, receiver_cs, token_in_cs, amount_in, token_out_cs, amount_out
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitSwapCheque(
            cheque_id, receiver_cs, token_in_cs, amount_in, token_out_cs, amount_out
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return {"tx": txn, "id": cheque_id.hex()}

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {"tx": txn_hash.hex(), "id": cheque_id.hex()}

    async def CashOutSwapCheque(self, cheque_id: str, private_key: Optional[str] = None):
        if private_key is None:
            private_key = self.private_key

        swap_detail = await self.getSwapDetail(cheque_id)
        token_out = swap_detail["tokenOut"]
        amount_out = swap_detail["amountOut"]

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_out)
        current_allowance = erc20.allowance(spender=self.contract.address, owner=self.address)
        if current_allowance < amount_out:
            approve = erc20.approve(
                spender=self.contract.address,
                amount=amount_out,
                private_key=private_key,
                conveted_amount=False,
            )
            if not approve:
                return False

        sender = self.w3.eth.account.from_key(private_key).address
        estimated_gas = self.contract.functions.CashOutSwapCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).estimate_gas({
            'from': sender,
            'gasPrice': self.w3.eth.gas_price,
        })
        swa = self.contract.functions.CashOutSwapCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction({
            'from': sender,
            'nonce': self.w3.eth.get_transaction_count(sender),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return {"tx": swa, "id": cheque_id}

        signed_txn = self.w3.eth.account.sign_transaction(swa, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"tx": tx_hash.hex(), "id": cheque_id}

    # ── Read functions ─────────────────────────────────────────────────────────

    async def getComunityPool(self):
        return self.contract.functions.getCollectedFee().call()

    async def getBalance(self):
        return self.contract.functions.getBalance().call()

    async def getOwner(self):
        return self.contract.functions.getOwner().call()

    async def getTreasery(self):
        return self.contract.functions.getTreasery().call()

    async def getProtocolStats(self):
        s = self.contract.functions.getProtocolStats().call()
        return {
            "balance": s[0],
            "collectedFees": s[1],
            "feeBps": s[2],
            "feeDenominator": s[3],
            "treasury": s[4],
            "owner": s[5],
            "active": s[6],
            "nextWithdraw": s[7],
        }

    async def nextAvailableWithdraw(self):
        return self.contract.functions.nextAvailableWithdraw().call()

    async def getNativeChequeInfo(self, cheque_id: str):
        if not cheque_id:
            raise ValueError("Cheque ID is required")
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        info = self.contract.functions.getNativeChequeInfo(cheque_id_bytes32).call()
        return {
            "to": info[0],
            "amount": info[1],
            "claimed": info[2],
        }

    async def getMultiChequeInfo(self, cheque_id: str, address: Optional[str] = None):
        if not cheque_id:
            raise ValueError("Cheque ID is required")

        addr = Web3.to_checksum_address(address) if address else self.address
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        info = self.contract.functions.getMultiChequeInfo(cheque_id_bytes32, addr).call()
        return {
            "amount": info[0],
            "receivers": info[1],
            "claimed": info[2],
        }

    async def getTokenChequeInfo(self, cheque_id: str):
        if not cheque_id:
            raise ValueError("Cheque ID is required")
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        cheque_info = self.contract.functions.getTokenChequeDetail(cheque_id_bytes32).call()
        return {
            "sender": cheque_info[0],
            "token": cheque_info[1],
            "amount": cheque_info[2],
            "receiver": cheque_info[3],
            "claimed": cheque_info[4],
        }

    async def getSwapDetail(self, cheque_id: str):
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        s = self.contract.functions.getSwapDetail(cheque_id_bytes32).call()
        return {
            "tokenIn": s[0],
            "amountIn": s[1],
            "tokenOut": s[2],
            "amountOut": s[3],
            "spender": s[4],
            "receiver": s[5],
            "claimed": s[6],
        }

    async def getFees(self):
        feesData = self.contract.functions.getFeeData().call()
        return {
            "bps": feesData[0],
            "FEE_DENOMINATOR": feesData[1],
        }


class NFTcheque:
    def __init__(self, w3: Web3, token: str, amount: int, spender: str):
        self.w3 = w3
        self.token = token
        self.amount = amount
        self.spender = spender

    def InitNFTCheque(self):
        pass

    def CashOutNFTCheque(self):
        pass


class Invoice:
    """
    Python SDK for OrbisInvoice (InvoiceHub) smart contract.

    Supports:
      - ETH and ERC20 invoices
      - Partial payments, tips, deadlines, fixed-payer restriction
      - Auto fee calculation (fetched from contract)
      - Auto ERC20 approve when needed
    """

    NULL_TOKEN = "0x0000000000000000000000000000000000000000"

    def __init__(
        self,
        w3: Optional[Web3] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        ABI = None,
        build_tx: bool = False,
        address: Optional[str] = None,
    ):
        self.w3           = w3
        self.private_key  = private_key
        self.address      = address
        self.build_tx     = build_tx
        self.contract     = None
        if w3 and contract_address and ABI:
            self.contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_address), abi=ABI
            )

    def set_params(
        self,
        w3: Optional[Web3] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        ABI = None,
        build_tx: Optional[bool] = None,
        address: Optional[str] = None,
    ):
        if w3:
            self.w3 = w3
        if private_key:
            self.private_key = private_key
            self.address = Web3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)
        if address:
            self.address = address
        if build_tx is not None:
            self.build_tx = build_tx
        if contract_address and ABI:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address), abi=ABI
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _signer(self, private_key=None):
        key = private_key or self.private_key
        if key:
            return key, Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        if self.address:
            return None, Web3.to_checksum_address(self.address)
        raise ValueError("No private key or address provided")

    @staticmethod
    def _to_bytes32(invoice_id) -> bytes:
        if isinstance(invoice_id, bytes):
            return invoice_id.rjust(32, b'\x00')
        return bytes.fromhex(str(invoice_id).lstrip("0x")).rjust(32, b'\x00')

    def _gas(self, fn, from_addr: str, value: int = 0) -> dict:
        gas = fn.estimate_gas({'from': from_addr, 'value': value, 'gasPrice': self.w3.eth.gas_price})
        return {
            'from': from_addr,
            'value': value,
            'nonce': self.w3.eth.get_transaction_count(from_addr),
            'gas': gas,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.w3.eth.chain_id,
        }

    def _send(self, txn, key):
        signed  = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return tx_hash.hex()

    # ── ID helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def generate_id(
        merchant: str,
        token: str,
        amount: int,
        due_at: int,
        payer: str,
        salt: Optional[bytes] = None,
    ) -> bytes:
        """
        Local mirror of contract's computeId:
            keccak256(abi.encodePacked(merchant, token, amount, dueAt, payer, salt))
        """
        import os
        if salt is None:
            salt = os.urandom(32)
        salt = (salt + b'\x00' * 32)[:32]
        return Web3.solidity_keccak(
            ['address', 'address', 'uint128', 'uint64', 'address', 'bytes32'],
            [
                Web3.to_checksum_address(merchant),
                Web3.to_checksum_address(token),
                amount, due_at,
                Web3.to_checksum_address(payer),
                salt,
            ],
        )

    async def compute_id(
        self,
        merchant: str,
        token: str,
        amount: int,
        due_at: int,
        payer: str,
        salt: bytes,
    ) -> bytes:
        """On-chain computeId call."""
        return self.contract.functions.computeId(
            Web3.to_checksum_address(merchant),
            Web3.to_checksum_address(token),
            amount, due_at,
            Web3.to_checksum_address(payer),
            (salt + b'\x00' * 32)[:32],
        ).call()

    # ── Fee helpers ───────────────────────────────────────────────────────────

    async def get_fee_params(self) -> dict:
        """Fetch current fee params from the contract (getFee)."""
        r = self.contract.functions.getFee().call()
        return {
            "base_fee":        r[0],   # flat ETH fee in wei
            "max_fee":         r[1],   # max ETH fee cap in wei
            "fee_bps":         r[2],   # creation fee in BPS
            "nex_fee_bps":     r[3],   # payment fee in BPS
            "fee_denominator": r[4],
        }

    # ── Write functions ───────────────────────────────────────────────────────

    async def createInvoice(
        self,
        invoice_id,
        merchant: str,
        amount: int,
        token: Optional[str] = None,
        due_at: int = 0,
        payer: Optional[str] = None,
        allow_tips: bool = False,
        allow_partial: bool = False,
        private_key: Optional[str] = None,
    ):
        """
        Creates a new invoice on-chain.

        Args:
            invoice_id:    bytes32 ID — use generate_id() or compute_id()
            merchant:      recipient address
            amount:        raw amount (wei for ETH, token units for ERC20)
            token:         ERC20 address, or None / NULL for native ETH invoice
            due_at:        unix expiry timestamp (0 = no deadline)
            payer:         fixed payer address, or None for open invoice
            allow_tips:    whether tips are allowed
            allow_partial: whether partial payments are allowed

        Returns:
            (tx_hash, invoice_id_hex) | unsigned txn dict (build_tx=True) | False on failure
        """
        key, from_addr = self._signer(private_key)
        NULL      = Web3.to_checksum_address(self.NULL_TOKEN)
        token_cs  = Web3.to_checksum_address(token) if token else NULL
        merch_cs  = Web3.to_checksum_address(merchant)
        payer_cs  = Web3.to_checksum_address(payer) if payer else NULL
        id_bytes  = self._to_bytes32(invoice_id)

        fp     = await self.get_fee_params()
        is_eth = token_cs == NULL

        if is_eth:
            msg_value = (amount * fp["fee_bps"]) // fp["fee_denominator"] + fp["base_fee"]
        else:
            msg_value = fp["base_fee"]
            token_fee = (amount * fp["fee_bps"]) // fp["fee_denominator"]
            if token_fee > 0:
                erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
                erc20.set_params(token_address=token_cs)
                if erc20.allowance(spender=self.contract.address, owner=from_addr) < token_fee:
                    if not erc20.approve(spender=self.contract.address, amount=token_fee,
                                         private_key=key, conveted_amount=False):
                        return False

        fn  = self.contract.functions.createInvoice(
            id_bytes, merch_cs, token_cs, amount, due_at, payer_cs, allow_tips, allow_partial
        )
        txn = fn.build_transaction(self._gas(fn, from_addr, msg_value))

        if self.build_tx:
            return {"tx": txn, "id": id_bytes.hex()}

        result = self._send(txn, key)
        return {"tx": result, "id": id_bytes.hex()} if result else False

    async def cancelInvoice(self, invoice_id, private_key: Optional[str] = None):
        """
        Cancels an invoice. Only callable by the merchant.

        Returns:
            tx_hash | False
        """
        key, from_addr = self._signer(private_key)
        id_bytes = self._to_bytes32(invoice_id)
        fn  = self.contract.functions.cancelInvoice(id_bytes)
        txn = fn.build_transaction(self._gas(fn, from_addr))

        if self.build_tx:
            return {"tx": txn, "id": id_bytes.hex()}

        result = self._send(txn, key)
        return {"tx": result, "id": id_bytes.hex()} if result else False

    async def payETH(
        self,
        invoice_id,
        amount: int,
        tip: int = 0,
        private_key: Optional[str] = None,
    ):
        """
        Pays an ETH invoice.
        msg.value = amount + tip + payment_fee (auto-calculated).

        Args:
            invoice_id: bytes32 invoice ID
            amount:     payment amount in wei (counts toward invoice total)
            tip:        optional tip in wei (goes to merchant, fee-free)
        """
        key, from_addr = self._signer(private_key)
        id_bytes = self._to_bytes32(invoice_id)

        fp        = await self.get_fee_params()
        fee       = (amount * fp["nex_fee_bps"]) // fp["fee_denominator"]
        msg_value = amount + tip + fee

        fn  = self.contract.functions.payETH(id_bytes, amount, tip)
        txn = fn.build_transaction(self._gas(fn, from_addr, msg_value))

        if self.build_tx:
            return {"tx": txn, "id": id_bytes.hex()}

        result = self._send(txn, key)
        return {"tx": result, "id": id_bytes.hex()} if result else False

    async def payERC20(
        self,
        invoice_id,
        amount: int,
        tip: int = 0,
        private_key: Optional[str] = None,
    ):
        """
        Pays an ERC20 invoice.
        Handles approve automatically.
        Sends baseFee in msg.value for repeat payments (paid > 0).

        Args:
            invoice_id: bytes32 invoice ID
            amount:     token amount (raw, decimals already applied)
            tip:        optional tip in raw token units
        """
        key, from_addr = self._signer(private_key)
        id_bytes = self._to_bytes32(invoice_id)

        fp    = await self.get_fee_params()
        inv   = await self.getInvoice(invoice_id)
        token_cs   = Web3.to_checksum_address(inv["token"])
        token_fee  = (amount * fp["nex_fee_bps"]) // fp["fee_denominator"]
        approve_amt = amount + tip + token_fee

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_cs)
        if erc20.allowance(spender=self.contract.address, owner=from_addr) < approve_amt:
            if not erc20.approve(spender=self.contract.address, amount=approve_amt,
                                  private_key=key, conveted_amount=False):
                return False

        msg_value = fp["base_fee"] if inv["paid"] > 0 else 0

        fn  = self.contract.functions.payERC20(id_bytes, amount, tip)
        txn = fn.build_transaction(self._gas(fn, from_addr, msg_value))

        if self.build_tx:
            return {"tx": txn, "id": id_bytes.hex()}

        result = self._send(txn, key)
        return {"tx": result, "id": id_bytes.hex()} if result else False

    # ── Read functions ────────────────────────────────────────────────────────

    async def getInvoice(self, invoice_id) -> dict:
        """Returns the full Invoice struct as a dict."""
        id_bytes = self._to_bytes32(invoice_id)
        inv = self.contract.functions.getInvoice(id_bytes).call()
        return {
            "merchant":      inv[0],
            "token":         inv[1],
            "amount":        inv[2],
            "fact_paid":     inv[3],
            "paid":          inv[4],
            "created_at":    inv[5],
            "due_at":        inv[6],
            "payer":         inv[7],
            "allow_tips":    inv[8],
            "allow_partial": inv[9],
            "base_fee_paid": inv[10],
            "canceled":      inv[11],
            "count":         inv[12],
        }

    async def getFee(self) -> dict:
        """Returns current fee parameters (alias for get_fee_params)."""
        return await self.get_fee_params()

    async def getCollectedFee(self) -> int:
        """Returns total accumulated ETH fees in wei."""
        return self.contract.functions.getCollectedFee().call()
