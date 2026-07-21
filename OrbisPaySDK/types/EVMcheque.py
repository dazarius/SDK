import OrbisPaySDK
from OrbisPaySDK.const import ORBISPAY_CHEQUES_ABI, __ALLOW_CHAINS__, ORBISPAY_CONTRACT_ADDRESS, __NULL_ADDRESS__,CHEQUES_TYPE
from web3 import Web3
from typing import Optional
from eth_utils import keccak
import time
from OrbisPaySDK.const import ORBISPAY_CHEQUES_ABI, __ALLOW_CHAINS__

try:
    from web3.middleware import ExtraDataToPOAMiddleware as _POAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware as _POAMiddleware  # web3 v5



MAPS_FUNC = {
    CHEQUES_TYPE["NativeCheque"]: {
        "init": "_InitNativeCheque",
        "cashout": "_CashOutNativeCheque",
        "info": "getNativeChequeInfo",
    },
    CHEQUES_TYPE["MultiCheque"]: {
        "init": "_InitMultiCheque",
        "cashout": "_CashOutMultiCheque",
        "info": "getMultiChequeInfo",
    },
    CHEQUES_TYPE["TokenCheque"]: {
        "init": "_InitTokenCheque",
        "cashout": "_CashOutTokenCheque",
        "info": "getTokenChequeDetail",
    },
    CHEQUES_TYPE["SwapCheque"]: {
        "init": "_InitTokenChequeSwap",
        "cashout": "_CashOutSwapCheque",
        "info": "getSwapDetail",
    }

}

def _inject_poa(w3: Web3) -> None:
    """Inject POA middleware if not already present (needed for BSC, Polygon, etc.)."""
    for mw in w3.middleware_onion:
        if mw is _POAMiddleware or (hasattr(mw, 'func') and mw.func is _POAMiddleware):
            return
    w3.middleware_onion.inject(_POAMiddleware, layer=0)

class Cheque:
    def __init__(self, w3=None, private_key=None, ABI=None, allowed_chains=None, retunrn_build_tx=False, address=None, contract_address=None):
        self.w3 = w3
        self.amount = None
        self.token = None
        self.private_key = private_key
        self.ABI = ABI or ORBISPAY_CHEQUES_ABI
        self.address = address
        self.return_build_tx = retunrn_build_tx
        self.allowed_chains = allowed_chains or __ALLOW_CHAINS__
        if contract_address: 
            self.contract = self.w3.eth.contract(address=contract_address, abi=ABI)

        if self.w3 is not None:
            self.__allow__()

    @staticmethod
    def generate_cheque_id(cheque_type=None) -> dict:
        import os
        from eth_utils import keccak
        secret = os.urandom(32)
        digest = bytearray(keccak(secret))
        
        return {"secret": secret.hex(), "id": bytes(digest)}

    @staticmethod
    def _normalize_cheque_id(cheque_id) -> bytes:
        from web3 import Web3
        if isinstance(cheque_id, bytes):
            return cheque_id[:32].rjust(32, b'\x00')
        if isinstance(cheque_id, str):
            if cheque_id.startswith("0x"):
                return Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
            return bytes.fromhex(cheque_id).rjust(32, b'\x00')
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
            print(f"Failed to get cheque ID: {str(e)}")
            return False

    def __allow__(self):
        _inject_poa(self.w3)
        if self.contract:
            return self.contract
        for chain in self.allowed_chains:
            if chain == self.w3.eth.chain_id:
                self.get_contract_for_chain(chain_id=self.w3.eth.chain_id)
                return True
        raise ValueError(f"Chain not allowed: {self.w3.eth.chain_id}")

    def get_contract_for_chain(self, chain_id):
        if self.contract:
            return self.contract
        from OrbisPaySDK.const import ORBISPAY_CONTRACT_ADDRESS, ORBISPAY_CHEQUES_ABI
        chain_id = int(chain_id)
        for key, value in ORBISPAY_CONTRACT_ADDRESS.items():
            if key == chain_id:
                contract_address = self.w3.to_checksum_address(value)
                self.contract = self.w3.eth.contract(address=contract_address, abi=ORBISPAY_CHEQUES_ABI)
                return self.contract
        raise ValueError(f"Chain {chain_id} not supported")

    async def get_address(self):
        if self.address: return self.address
        elif self.w3: return self.w3.eth.default_account
        raise ValueError("No address provided")

    def set_parameters(self, chain_id=None, w3=None, amount=None, private_key=None, token=None, address=None, contract=None, ABI=None):
        if w3:
            self.w3 = w3
            _inject_poa(self.w3)
            if contract is None: self.get_contract_for_chain(chain_id=chain_id or self.w3.eth.chain_id)
        if contract: self.contract = self.w3.eth.contract(address=contract, abi=ABI)
        if amount: self.amount = amount
        if private_key:
            self.private_key = private_key
            self.address = self.w3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)
        if token: self.token = token
        if address: self.address = address

    def __convert__(self):
        return self.w3.to_wei(self.amount, 'ether')

    async def _resolve_cheque_type(self, display_id: str) -> str:
        if ":" in str(display_id):
            
            return str(display_id).split(":")[-1]
        
        cheque_id_bytes = self._normalize_cheque_id(display_id)
        code = cheque_id_bytes[31]
        if code in MAPS_FUNC:
            return code
            
        raise ValueError("Unknown cheque type from ID")

    def _resolve_cheque_id(self, display_id: str) -> bytes:
        if ":" in str(display_id):
            display_id = str(display_id).split(":")[0]
        return self._normalize_cheque_id(display_id)

    def _with_optional_expiry(self, func_name: str, core_args: list, expire_days: int) -> list:
        func = self.contract.get_function_by_name(func_name)
        if len(func.abi['inputs']) > len(core_args):
            return [*core_args, expire_days]
        return core_args
        
    def _map_outputs(self, func_name, res):
        func = self.contract.get_function_by_name(func_name)
        outputs = func.abi['outputs']
        return {out.get('name') or i: res[i] for i, out in enumerate(outputs)}

    # -- Dispatchers --
    
    async def InitCheque(self, amount, to: list, token_address=None, private_key=None, cheque_id=None, expire_days=0, type=None, **kwargs):
        if not isinstance(to, list) or len(to) == 0: raise ValueError("Recipients required")
        if type: cheque_type = type
        elif token_address: cheque_type = CHEQUES_TYPE["TokenCheque"]
        elif len(to) == 1: cheque_type = CHEQUES_TYPE["NativeCheque"]
        else: cheque_type = CHEQUES_TYPE["MultiCheque"]

        method = getattr(self, MAPS_FUNC[cheque_type]["init"])
        if cheque_type == CHEQUES_TYPE["TokenCheque"]:
            if len(to) != 1: raise ValueError("Token supports a single recipient")
            return await method(token_address, amount, to[0], private_key, cheque_id, expire_days, **kwargs)
        if cheque_type == CHEQUES_TYPE["NativeCheque"]:
            return await method(amount, to[0], private_key, cheque_id, expire_days, **kwargs)
        if cheque_type == CHEQUES_TYPE["MultiCheque"]:
            return await method(amount, to, private_key, cheque_id, expire_days, **kwargs)

    async def CashOutCheque(self, display_id: str, private_key=None, **kwargs):
        cheque_type = await self._resolve_cheque_type(display_id)
        method = getattr(self, MAPS_FUNC[cheque_type]["cashout"])
        return await method(display_id, private_key, **kwargs)

    async def RefundCheque(self, display_id: str, private_key=None, **kwargs):
        cheque_type = await self._resolve_cheque_type(display_id)
        id_bytes = self._resolve_cheque_id(display_id)
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address

        if cheque_type == CHEQUES_TYPE["SwapCheque"]:
            fn = self.contract.functions.RefundSwapCheque(id_bytes)
        elif cheque_type == CHEQUES_TYPE["NativeCheque"]:
            fn = self.contract.functions.RefundNativeCheque(id_bytes)
        elif cheque_type == CHEQUES_TYPE["MultiCheque"]:
            fn = self.contract.functions.RefundMultiCheque(id_bytes)
        elif cheque_type == CHEQUES_TYPE["TokenCheque"]:
            fn = self.contract.functions.RefundTokenCheque(id_bytes)
        else: raise ValueError("Unknown type")
        
        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = fn.estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = fn.build_transaction(tx_params)
        
        if self.return_build_tx: return {"tx": txn, "id": display_id}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": display_id}

    async def ExtendCheque(self, display_id: str, additional_days: int, private_key=None, **kwargs):
        cheque_type = await self._resolve_cheque_type(display_id)
        id_bytes = self._resolve_cheque_id(display_id)
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address

        if cheque_type == CHEQUES_TYPE["SwapCheque"]: fn = self.contract.functions.ExtendSwapCheque(id_bytes, additional_days)
        elif cheque_type == CHEQUES_TYPE["NativeCheque"]: fn = self.contract.functions.ExtendNativeCheque(id_bytes, additional_days)
        elif cheque_type == CHEQUES_TYPE["MultiCheque"]: fn = self.contract.functions.ExtendMultiCheque(id_bytes, additional_days)
        elif cheque_type == CHEQUES_TYPE["TokenCheque"]: fn = self.contract.functions.ExtendTokenCheque(id_bytes, additional_days)
        else: raise ValueError("Unknown type")
        
        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = fn.estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = fn.build_transaction(tx_params)
        
        if self.return_build_tx: return {"tx": txn, "id": display_id}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": display_id}

    # -- Implementations --

    async def _InitNativeCheque(self, amount, receiver, private_key=None, cheque_id=None, expire_days=0, **kwargs):
        key = private_key or self.private_key
        address = self.w3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        rec_cs = self.w3.to_checksum_address(receiver)
        
        cd = self.generate_cheque_id(CHEQUES_TYPE["NativeCheque"]) if not cheque_id else {"id": self._normalize_cheque_id(cheque_id), "secret": None}
        args = self._with_optional_expiry("InitNativeCheque", [cd["id"], rec_cs], expire_days)
        value_wei = self.w3.to_wei(amount, 'ether')

        tx_params = {'from': address, 'value': value_wei, 'nonce': self.w3.eth.get_transaction_count(address), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.InitNativeCheque(*args).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.InitNativeCheque(*args).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, **cd, "type": CHEQUES_TYPE["NativeCheque"]}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": cd["id"].hex(), "secret": cd["secret"], "type": CHEQUES_TYPE["NativeCheque"]}

    async def _CashOutNativeCheque(self, display_id, private_key=None, **kwargs):
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address
        id_bytes = self._resolve_cheque_id(display_id)

        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.CashOutNativeCheque(id_bytes).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.CashOutNativeCheque(id_bytes).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, "id": display_id}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": display_id}

    async def _InitMultiCheque(self, amount, receivers, private_key=None, cheque_id=None, expire_days=0, **kwargs):
        key = private_key or self.private_key
        address = self.w3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        rec_cs = [self.w3.to_checksum_address(r) for r in receivers]
        
        cd = self.generate_cheque_id(CHEQUES_TYPE["MultiCheque"]) if not cheque_id else {"id": self._normalize_cheque_id(cheque_id), "secret": None}
        args = self._with_optional_expiry("InitMultiCheque", [cd["id"], rec_cs], expire_days)
        value_wei = self.w3.to_wei(amount, 'ether')

        tx_params = {'from': address, 'value': value_wei, 'nonce': self.w3.eth.get_transaction_count(address), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.InitMultiCheque(*args).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.InitMultiCheque(*args).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, **cd, "type": CHEQUES_TYPE["MultiCheque"]}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": cd["id"].hex(), "secret": cd["secret"], "type": CHEQUES_TYPE["MultiCheque"]}

    async def _CashOutMultiCheque(self, display_id, private_key=None, **kwargs):
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address
        id_bytes = self._resolve_cheque_id(display_id)

        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.CashOutMultiCheque(id_bytes).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.CashOutMultiCheque(id_bytes).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, "id": display_id}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": display_id}

    async def _InitTokenCheque(self, token_address, amount, receiver, private_key=None, cheque_id=None, expire_days=0, **kwargs):
        key = private_key or self.private_key
        address = self.w3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        tok_cs = self.w3.to_checksum_address(token_address)
        rec_cs = self.w3.to_checksum_address(receiver)

        cd = self.generate_cheque_id(CHEQUES_TYPE["TokenCheque"]) if not cheque_id else {"id": self._normalize_cheque_id(cheque_id), "secret": None}
        args = self._with_optional_expiry("InitTokenCheque", [cd["id"], tok_cs, amount, rec_cs], expire_days)

        import OrbisPaySDK
        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=tok_cs)
        if erc20.allowance(spender=self.contract.address, owner=address) < amount:
            approve = erc20.approve(spender=self.contract.address, amount=amount, private_key=key, conveted_amount=False)
            if approve: return {"need_approve": approve}

        tx_params = {'from': address, 'nonce': self.w3.eth.get_transaction_count(address), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.InitTokenCheque(*args).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.InitTokenCheque(*args).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, **cd, "type": CHEQUES_TYPE["TokenCheque"]}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": cd["id"].hex(), "secret": cd["secret"], "type": CHEQUES_TYPE["TokenCheque"]}

    async def _CashOutTokenCheque(self, display_id, private_key=None, **kwargs):
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address
        id_bytes = self._resolve_cheque_id(display_id)

        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.CashOutTokenCheque(id_bytes).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.CashOutTokenCheque(id_bytes).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, "id": display_id}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": display_id}

    async def _InitTokenChequeSwap(self, token_in, amount_in, token_out, amount_out, receiver, private_key=None, cheque_id=None, expire_days=0, **kwargs):
        key = private_key or self.private_key
        address = self.w3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        ti_cs = self.w3.to_checksum_address(token_in)
        to_cs = self.w3.to_checksum_address(token_out)
        rec_cs = self.w3.to_checksum_address(receiver)

        cd = self.generate_cheque_id(CHEQUES_TYPE["SwapCheque"]) if not cheque_id else {"id": self._normalize_cheque_id(cheque_id), "secret": None}
        args = self._with_optional_expiry("InitSwapCheque", [cd["id"], rec_cs, ti_cs, amount_in, to_cs, amount_out], expire_days)

        import OrbisPaySDK
        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=ti_cs)
        if erc20.allowance(spender=self.contract.address, owner=address) < amount_in:
            approve = erc20.approve(spender=self.contract.address, amount=amount_in, private_key=key, conveted_amount=False)
            if not approve: return False

        tx_params = {'from': address, 'nonce': self.w3.eth.get_transaction_count(address), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.InitSwapCheque(*args).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.InitSwapCheque(*args).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, **cd, "type": CHEQUES_TYPE["SwapCheque"]}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": cd["id"].hex(), "secret": cd["secret"], "type": CHEQUES_TYPE["SwapCheque"]}

    async def _CashOutSwapCheque(self, secret: str, private_key=None, **kwargs):
        # Swap cashout requires the raw secret, not the hash.
        # So we hash it first to get the info, then pass the secret.
        key = private_key or self.private_key
        sender = self.w3.eth.account.from_key(key).address
        
        from eth_utils import keccak
        secret_bytes = bytes.fromhex(secret) if secret.startswith("0x") else bytes.fromhex(secret)
        hashed_id = bytes(keccak(secret_bytes))
        swap_detail = await self.getSwapDetail(hashed_id)
        
        amount_out = swap_detail.get("amountOut", 0)
        from OrbisPaySDK.const import __NULL_ADDRESS__
        token_out = swap_detail.get("tokenOut", __NULL_ADDRESS__)
        
        import OrbisPaySDK
        erc20 = OrbisPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_out)
        if erc20.allowance(spender=self.contract.address, owner=sender) < amount_out:
            approve = erc20.approve(spender=self.contract.address, amount=amount_out, private_key=key, conveted_amount=False)
            if approve: return {"need_approve": approve, "id": hashed_id.hex()}

        id_bytes = secret_bytes[:32].rjust(32, b'\x00') # passed directly
        tx_params = {'from': sender, 'nonce': self.w3.eth.get_transaction_count(sender), 'gasPrice': self.w3.eth.gas_price}
        tx_params['gas'] = self.contract.functions.CashOutSwapCheque(id_bytes).estimate_gas(tx_params)
        tx_params.update(kwargs)
        txn = self.contract.functions.CashOutSwapCheque(id_bytes).build_transaction(tx_params)

        if self.return_build_tx: return {"tx": txn, "id": hashed_id.hex()}
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1: return False
        return {"tx": tx_hash.hex(), "id": hashed_id.hex()}

    # -- Read Methods --

    async def getProtocolStats(self):
        s = self.contract.functions.getProtocolStats().call()
        return self._map_outputs("getProtocolStats", s)

    async def getChequeInfo(self, display_id: str, address=None):
        cheque_type, id_bytes = await self._resolve_cheque_type(display_id)
        from OrbisPaySDK.const import CHEQUES_TYPE
        
        if cheque_type == CHEQUES_TYPE["NativeCheque"]: return await self.getNativeChequeInfo(id_bytes)
        elif cheque_type == CHEQUES_TYPE["MultiCheque"]: return await self.getMultiChequeInfo(id_bytes, address)
        elif cheque_type == CHEQUES_TYPE["TokenCheque"]: return await self.getTokenChequeInfo(id_bytes)
        elif cheque_type == CHEQUES_TYPE["SwapCheque"]: return await self.getSwapDetail(display_id)
        raise ValueError("Unknown cheque type")

    async def getNativeChequeInfo(self, cheque_id: str):
        id_bytes = self._resolve_cheque_id(cheque_id)
        info = self.contract.functions.getNativeChequeInfo(id_bytes).call()
        return self._map_outputs("getNativeChequeInfo", info)

    async def getMultiChequeInfo(self, cheque_id: str, address=None):
        addr = self.w3.to_checksum_address(address) if address else self.address
        id_bytes = self._resolve_cheque_id(cheque_id)
        info = self.contract.functions.getMultiChequeInfo(id_bytes, addr).call()
        return self._map_outputs("getMultiChequeInfo", info)

    async def getTokenChequeInfo(self, cheque_id: str):
        id_bytes = self._resolve_cheque_id(cheque_id)
        # Handle ABI name differences (detail vs info)
        try:
            info = self.contract.functions.getTokenChequeDetail(id_bytes).call()
            return self._map_outputs("getTokenChequeDetail", info)
        except:
            info = self.contract.functions.getTokenChequeInfo(id_bytes).call()
            return self._map_outputs("getTokenChequeInfo", info)

    async def getSwapDetail(self, cheque_id: str):
        id_bytes = self._resolve_cheque_id(cheque_id)
        s = self.contract.functions.getSwapDetail(id_bytes).call()
        return self._map_outputs("getSwapDetail", s)

    async def getFees(self):
        try:
            f = self.contract.functions.getFee().call()
            return self._map_outputs("getFee", f)
        except:
            # Fallback for old ABI
            f = self.contract.functions.getFeeSchedule().call()
            return {"nativeBps": f[0], "multiBps": f[1], "tokenBps": f[2], "swapBps": f[3], "denominator": f[4]}

    async def getComunityPool(self): return self.contract.functions.getCollectedFee().call()
    async def getBalance(self): return self.contract.functions.getBalance().call()
    async def getOwner(self): return self.contract.functions.getOwner().call()
    async def getTreasery(self): return self.contract.functions.getTreasery().call()
    async def nextAvailableWithdraw(self): return self.contract.functions.nextAvailableWithdraw().call()

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
