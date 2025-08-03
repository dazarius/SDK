import shadowPaySDK
from web3 import Web3
import json
from typing import Union, Optional
from shadowPaySDK.const import __ERC20_ABI__


class ERC20Token:
    def __init__(self,  w3: Optional[Web3] = None, explorer: Optional[str] = None):
        self.web3 = w3
        self.explorer = explorer

        self.address = None
        self.contract = None

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

    def get_balance(self, wallet_address: str) -> float:
        self._ensure_contract()
        raw = self.contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        return raw 


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

    def transfer(self, private_key: str, to: str, amount: float) -> str:
        self._ensure_contract()
        account = self.web3.eth.account.from_key(private_key)
        
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

