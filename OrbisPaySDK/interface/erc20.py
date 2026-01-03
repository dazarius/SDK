import OrbisPaySDK
from web3 import Web3
from web3 import AsyncWeb3
from web3.providers.persistent import WebSocketProvider
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.persistent import (
    AsyncIPCProvider,
    WebSocketProvider,
)
import json
from hexbytes import HexBytes
import asyncio


from typing import Union, Optional, Dict, Any
from OrbisPaySDK.const import __ERC20_ABI__


class ERC20Token:
    def __init__(self,  w3: Optional[Web3] = None, explorer: Optional[str] = None, contract = None):
        self.web3 = w3
        self.explorer = explorer

        self.address = None
        self.contract = contract

    def set_params(self, token_address: Optional[str] = None, w3:Optional[Web3] = None):
        if w3:
            self.web3 = w3
        if token_address:
            self.address = Web3.to_checksum_address(token_address)
            self.contract = self.web3.eth.contract(address=self.address, abi=__ERC20_ABI__)

    def _ensure_contract(self):
        if not self.contract:
            raise ValueError("Token address is not set. Use set_params first.")

    def _format_tx(self, tx_hash: str) -> str:
        if self.explorer:
            return f"{self.explorer.rstrip('/')}/tx/{tx_hash}"
        return tx_hash
    def gen_wallet(self) -> str:
        account = self.web3.eth.account.create()
        return account
    def get_decimals(self) -> int:
        self._ensure_contract()

        return self.contract.functions.decimals().call()

    def get_symbol(self) -> str:
        self._ensure_contract()
        return self.contract.functions.symbol().call()

    def get_balance(self, wallet_address: str, decimals = None) -> float:
        if decimals is None:
            decimals = self.get_decimals()
        self._ensure_contract()
        raw = self.contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        data = {
            "balance":raw,
            "balance_ui":raw * (10 ** decimals)
        }
        return raw 
    def metadata(self):
        symbal = self.get_symbol()
        decimals = self.get_decimals()

        

    def allowance(self, owner: str, spender: str) -> float:
        self._ensure_contract()
        raw = self.contract.functions.allowance(
            Web3.to_checksum_address(owner),
            Web3.to_checksum_address(spender)
        ).call()
        return raw 

    def ensure_allowance(self, private_key: str, spender: str, amount, converted_amount: bool = False) -> Union[bool, str]:
        self._ensure_contract()
        account = self.web3.eth.account.from_key(private_key)
        current = self.allowance(account.address, spender)
        if current == amount:
            return True
        return self.approve(private_key, spender, amount, conveted_amount=converted_amount)

    def transfer(self, private_key: str, to: str, amount: float, decimals: int = None) -> str:
        self._ensure_contract()
        account = self.web3.eth.account.from_key(private_key)
        if decimals is None:
            decimals = self.get_decimals()
        
        amount = int(amount * (10 ** decimals))
        
        estimated_gas = self.contract.functions.transfer(
            Web3.to_checksum_address(to),
            amount
        ).estimate_gas({
            'from': account.address,
            'gasPrice': self.web3.to_wei('5', 'gwei'),
        })
        txn = self.contract.functions.transfer(
            Web3.to_checksum_address(to),
            amount
        ).build_transaction({
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': estimated_gas,
            'gasPrice': self.web3.to_wei('5', 'gwei'),
        })

        signed = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        return self._format_tx(self.web3.to_hex(tx_hash))

    def approve(self,  spender: str, amount: float,address:Optional[str] = None,  private_key: Optional[str] = None, conveted_amount: bool = True) -> str:
        
        self._ensure_contract()
        key = private_key

        if key:
            address = Web3.to_checksum_address(self.web3.eth.account.from_key(key).address)
        
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")
        txn = self.contract.functions.approve(
            Web3.to_checksum_address(spender),
            amount
        ).build_transaction({
            'from': address,
            'nonce': self.web3.eth.get_transaction_count(address),
            'gas': 60000,
            
            'gasPrice': self.web3.eth.gas_price,
        })
        

        signed = self.web3.eth.account.sign_transaction(txn, key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt.status != 1:
            raise ValueError(f"aaprove fail.\n {self._format_tx(self.web3.to_hex(tx_hash))}")
        return f"{self._format_tx(self.web3.to_hex(tx_hash))}"
    

class ERC20TokenMonitr():
    def __init__(self, wss_url, rpc_url = None, network_name = None, tokens:list = None, on_transfer_callback:callable=None,get_token_data = False, show_debug:bool=False, addresses:list = None, metadata:Dict[str, Any] = None):
        self.get_token_data = get_token_data
        self.show_debug = show_debug
        self.wss_url = wss_url
        self.rpc_url = rpc_url
        self.TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        self.on_transfer_callback = on_transfer_callback
        if on_transfer_callback is None:
            self.on_transfer_callback = self.token_transfer_callback

        self.tokens_set = {t.lower() for t in tokens} if tokens else set()
        self.addresses_set = {a.lower() for a in addresses} if addresses else set()

        if not network_name:
            self.network_name = wss_url

    async def start_transfer_monitor(self):
        
        async with AsyncWeb3(WebSocketProvider(self.wss_url)) as w3:
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if self.show_debug:
                print(f"[{self.network_name}] subscribing to Transfer logs on {self.wss_url}")

            await w3.eth.subscribe("logs", {"topics": [self.TRANSFER_TOPIC]})
            async for raw in w3.socket.process_subscriptions():
                log = None
                if isinstance(raw, dict):
                    if "params" in raw and raw["params"] is not None:
                        log = raw["params"].get("result")
                    elif "result" in raw:
                        log = raw.get("result")
                if not log:
                    continue

                # -------------------- Извлечение данных --------------------
                token_addr = log.get("address") if isinstance(log, dict) else getattr(log, "address", None)
                token_addr_norm = token_addr.lower() if isinstance(token_addr, str) else None
                if self.tokens_set and token_addr_norm not in self.tokens_set:
                    continue

                topics = log.get("topics") if isinstance(log, dict) else getattr(log, "topics", None)
                if not topics or len(topics) < 3:
                    continue

                frm = self.normalize_32byte_hex(topics[1])
                to = self.normalize_32byte_hex(topics[2])
                value = self.parse_data_value(log.get("data") if isinstance(log, dict) else getattr(log, "data", None))

                if self.addresses_set and not ((frm and frm in self.addresses_set) or (to and to in self.addresses_set)):
                    continue

                tx_hash_raw = log.get("transactionHash") if isinstance(log, dict) else getattr(log, "transactionHash", None)
                tx_hash = tx_hash_raw.hex() if isinstance(tx_hash_raw, HexBytes) else str(tx_hash_raw) if tx_hash_raw else None

                block_number_raw = log.get("blockNumber") if isinstance(log, dict) else getattr(log, "blockNumber", None)
                try:
                    if isinstance(block_number_raw, int):
                        block_number = block_number_raw
                    elif isinstance(block_number_raw, str) and block_number_raw.startswith("0x"):
                        block_number = int(block_number_raw, 16)
                    else:
                        block_number = int(block_number_raw) if block_number_raw is not None else None
                except Exception:
                    block_number = None
                # ----------------------------------------------------------
                if self.get_token_data:
                    if self.rpc_url:
                        erc20 = ERC20Token(w3=Web3(Web3.HTTPProvider(self.rpc_url)))
                        erc20.set_params(token_address=token_addr)
                        symbol = erc20.get_symbol()
                        decimals = erc20.get_decimals()
                        token_addr_norm = symbol
                        normal_value = value / (10 ** decimals)
                        value = normal_value
                        
                    else:
                        continue
                    
                ev = {
                    "network": self.network_name,
                    "token": token_addr_norm,
                    "from": frm,
                    "to": to,
                    "value": value,
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "logIndex": (log.get("logIndex") if isinstance(log, dict) else getattr(log, "logIndex", None)),
                    "raw_log": log,
                }

                try:
                    await self.on_transfer_callback(ev)
                except Exception as e:
                    print(f"[{self.network_name}] callback error:", e)

    async def token_transfer_callback(self, ev):
        print (ev)
    def normalize_32byte_hex(self, item) -> str | None:
        if item is None:
            return None
        if isinstance(item, HexBytes):
            s_ = item.hex()
            if not s_.startswith("0x"):
                s_ = "0x" + s_
        else:
            s_ = str(item).strip()
        if not s_:
            return None
        hexpart = s_[2:] if s_.startswith("0x") else s_
        if len(hexpart) >= 40:
            return "0x" + hexpart[-40:].lower()
        return None
    def parse_data_value(self, data_field) -> int | None:
        if data_field is None:
            return None
        try:
            if isinstance(data_field, HexBytes):
                s_ = data_field.hex()
                return int(s_, 16) if s_.startswith("0x") else int("0x" + s_, 16)
            s_ = str(data_field).strip()
            if s_.startswith("0x"):
                return int(s_, 16)
            return int(s_)
        except Exception:
            return None
def callback(ev):
    print(ev)
    return ev
async def main():
    rpc_url="https://bsc-testnet-rpc.publicnode.com"
    token_monitor = ERC20TokenMonitr(on_transfer_callback=callback,rpc_url=rpc_url, show_debug=True, wss_url="wss://bsc-testnet-rpc.publicnode.com", get_token_data=True)
    tasks = []
    tasks.append(asyncio.create_task(
            token_monitor.start_transfer_monitor()))


    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())