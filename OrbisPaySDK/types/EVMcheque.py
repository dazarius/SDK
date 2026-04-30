import token
import OrbisPaySDK
from OrbisPaySDK.const import __SHADOWPAY_ABI__ERC20__, __ALLOW_CHAINS__, __SHADOWPAY_CONTRACT_ADDRESS__ERC20__, __NULL_ADDRESS__
from web3 import Web3
from typing import Optional
import httpx
from eth_abi import encode
from eth_abi.packed import encode_packed

from eth_utils import keccak, to_checksum_address
import time

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

    # ── Native ETH cheque ──────────────────────────────────────────────────────

    async def InitCheque(self, support_bps, amount, receiver: list, private_key: Optional[str] = None):
        if not isinstance(receiver, list):
            raise ValueError("Receiver must be a list of addresses")

        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        receiver = [Web3.to_checksum_address(addr) for addr in receiver]
        cheque_id = self._generate_cheque_id(address, f"{receiver}:{amount}")

        estimated_gas = self.contract.functions.InitCheque(
            cheque_id, receiver, support_bps
        ).estimate_gas({
            'from': address,
            'value': self.w3.to_wei(amount, 'ether'),
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitCheque(
            cheque_id, receiver, support_bps
        ).build_transaction({
            'from': address,
            'value': self.w3.to_wei(amount, 'ether'),
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.w3.eth.chain_id,
        })
        if self.return_build_tx:
            return txn

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id.hex(),
        }

    async def CashOutCheque(self, private_key: str, cheque_id: str):
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

        txn = self.contract.functions.CashOutCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction(tx_common)

        if self.return_build_tx:
            return txn

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"hash": tx_hash.hex()}

    # ── ERC-20 token cheque ────────────────────────────────────────────────────

    async def InitTokenCheque(self, support_bps, token_address: str, amount, reciver: str, private_key: Optional[str] = None):
        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        token_cs = Web3.to_checksum_address(token_address)
        reciver_cs = Web3.to_checksum_address(reciver)
        cheque_id = self._generate_cheque_id(address, f"{token_cs}:{amount}:{reciver_cs}")

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_cs)
        erc20.allowance(spender=self.contract.address, owner=address)

        estimated_gas = self.contract.functions.InitTokenCheque(
            cheque_id, token_cs, amount, reciver_cs, support_bps
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitTokenCheque(
            cheque_id, token_cs, amount, reciver_cs, support_bps
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return txn

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id.hex(),
        }

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
            return txn

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"hash": tx_hash.hex(), "status": receipt.status}

    # ── Swap cheque ────────────────────────────────────────────────────────────

    async def InitTokenChequeSwap(self, support_bps, token_in: str, amount_in, token_out: str, amount_out, reciver: str, private_key: Optional[str] = None):
        key = private_key or self.private_key
        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")

        token_in_cs = Web3.to_checksum_address(token_in)
        token_out_cs = Web3.to_checksum_address(token_out)
        reciver_cs = Web3.to_checksum_address(reciver)
        cheque_id = self._generate_cheque_id(address, f"{token_in_cs}:{amount_in}:{token_out_cs}:{amount_out}:{reciver_cs}")

        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_in_cs)
        erc20.allowance(spender=self.contract.address, owner=address)

        estimated_gas = self.contract.functions.InitSwapCheque(
            cheque_id, reciver_cs, token_in_cs, amount_in, token_out_cs, amount_out, support_bps
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.InitSwapCheque(
            cheque_id, reciver_cs, token_in_cs, amount_in, token_out_cs, amount_out, support_bps
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return txn

        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id.hex(),
        }

    async def CashOutSwapCheque(self, cheque_id: str, private_key: Optional[str] = None):
        if private_key is None:
            private_key = self.private_key

        swap_detail = await self.getSwaoDetail(cheque_id)
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
            return swa

        signed_txn = self.w3.eth.account.sign_transaction(swa, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {"hash": tx_hash.hex()}

    # ── Invoice logic ──────────────────────────────────────────────────────────

    async def getInvoiceFee(self):
        fee = self.contract.functions.getFee().call()
        return {
            "baseFee": fee[0],
            "maxFee": fee[1],
            "feeBps": fee[2],
            "nextFeeBps": fee[3],
            "FEE_DENOMINATOR": fee[4],
        }

    async def createInvoice(self, payer: str, deadline: int, amount: int, merchant: str, value: int, currency: str = None, allowTips=False, allowPartial=False, private_key: Optional[str] = None):
        if private_key is None:
            private_key = self.private_key

        timestamp = int(time.time())
        acc = self.w3.eth.account.from_key(private_key)
        nonce = self.w3.eth.get_transaction_count(acc.address)

        packed = encode_packed(
            ['address', 'address', 'uint256', 'uint256', 'uint256'],
            [merchant, payer, amount, deadline, timestamp]
        )
        id = Web3.keccak(packed)
        hex_id = id.hex()

        estimated_gas = self.contract.functions.createInvoice(
            id,
            Web3.to_checksum_address(merchant),
            Web3.to_checksum_address(currency),
            amount,
            deadline,
            Web3.to_checksum_address(payer),
            allowTips,
            allowPartial,
        ).estimate_gas({
            "value": value,
            'from': acc.address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.createInvoice(
            id,
            Web3.to_checksum_address(merchant),
            Web3.to_checksum_address(currency),
            amount,
            deadline,
            Web3.to_checksum_address(payer),
            allowTips,
            allowPartial,
        ).build_transaction({
            "value": value,
            'from': acc.address,
            'nonce': nonce,
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        try:
            sign_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
            tx = self.w3.eth.send_raw_transaction(sign_txn.raw_transaction)
            if self.w3.eth.wait_for_transaction_receipt(tx).status != 1:
                return False
            return hex_id, tx.hex()
        except Exception as e:
            print(f"Error creating invoice: {e}")
            return False

    async def payETHInvoice(self, id: str, amount: int, private_key: Optional[str] = None, tip=0):
        fees = await self.getInvoiceFee()
        if private_key is None:
            private_key = self.private_key
        value = amount + (tip * fees["nextFeeBps"]) // fees["FEE_DENOMINATOR"]

        acc = self.w3.eth.account.from_key(private_key)
        nonce = self.w3.eth.get_transaction_count(acc.address)
        estimated_gas = self.contract.functions.payETH(
            Web3.to_bytes(hexstr=id), amount, tip
        ).estimate_gas({
            'value': value,
            'from': acc.address,
            'gasPrice': self.w3.eth.gas_price,
        })
        txn = self.contract.functions.payETH(
            Web3.to_bytes(hexstr=id), amount, tip
        ).build_transaction({
            "value": value,
            'from': acc.address,
            'nonce': nonce,
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        try:
            sign_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
            tx = self.w3.eth.send_raw_transaction(sign_txn.raw_transaction)
            if self.w3.eth.wait_for_transaction_receipt(tx).status != 1:
                return False
            return tx.hex()
        except Exception as e:
            print(f"Error paying invoice: {e}")
            return False

    async def payERC20invoice(self, id, amount, tip=0, private_key=None):
        fees = await self.getInvoiceFee()
        value = fees["baseFee"]
        if private_key is None:
            private_key = self.private_key

        sender = self.w3.eth.account.from_key(private_key).address
        nonce = self.w3.eth.get_transaction_count(sender)
        estimated_gas = self.contract.functions.payERC20(
            Web3.to_bytes(hexstr=id), amount, tip
        ).estimate_gas({
            'value': value,
            'from': sender,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        txn = self.contract.functions.payERC20(
            Web3.to_bytes(hexstr=id), amount, tip
        ).build_transaction({
            'value': value,
            'from': sender,
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        try:
            sign_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
            tx = self.w3.eth.send_raw_transaction(sign_txn.raw_transaction)
            if self.w3.eth.wait_for_transaction_receipt(tx).status != 1:
                return False
            return tx.hex()
        except Exception as e:
            print(f"Error paying invoice: {e}")
            return False

    # ── Read functions ─────────────────────────────────────────────────────────

    async def getComunityPool(self):
        return self.contract.functions.getCollectedFee().call()

    async def getOwner(self):
        return self.contract.functions.getOwner().call()

    async def getTreasery(self):
        return self.contract.functions.getTreasery().call()

    async def getChequeInfo(self, cheque_id: str, address: Optional[str] = None):
        if not cheque_id:
            raise ValueError("Cheque ID is required")
        if address:
            address = Web3.to_checksum_address(address)

        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        cheque_info = self.contract.functions.getChequeInfo(
            cheque_id_bytes32, address or self.address
        ).call()
        return {
            "sender": cheque_info[0],
            "receiver": cheque_info[1],
            "status": "claimed" if cheque_info[2] else "unclaimed",
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
            "receivers": cheque_info[3],
            "status": cheque_info[4],
        }

    async def getSwaoDetail(self, cheque_id: str):
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        s = self.contract.functions.getSwapDetail(cheque_id_bytes32).call()
        return {
            "tokenIn": s[0],
            "amountIn": s[1],
            "tokenOut": s[2],
            "amountOut": s[3],
            "spender": s[4],
            "receiver": s[5],
            "status": "claimed" if s[6] else "unclaimed",
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
