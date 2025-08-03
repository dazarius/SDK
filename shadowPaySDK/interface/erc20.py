from web3 import Web3
import json
from typing import Union, Optional

ERC20_ABI = json.loads("""[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"type":"function"}
]""")


class ERC20Token:
    def __init__(self, web3: Web3, token: str, explorer: Optional[str] = None):
        self.web3 = web3
        self.explorer = explorer
        self.address = Web3.to_checksum_address(token)
        self.contract = web3.eth.contract(address=self.address, abi=ERC20_ABI)

    def _format_tx(self, tx_hash: str) -> str:
        if self.explorer:
            return f"{self.explorer.rstrip('/')}/tx/{tx_hash}"
        return tx_hash



    def get_decimals(self) -> int:
        return self.contract.functions.decimals().call()

    def get_symbol(self) -> str:
        return self.contract.functions.symbol().call()

    def get_balance(self, wallet_address: str) -> float:
        raw_balance = self.contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        return raw_balance / (10 ** self.get_decimals())

        self._ensure_contract()
        raw = self.contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        return raw
    def allowance(self, owner: str, spender: str) -> float:
        raw = self.contract.functions.allowance(
            Web3.to_checksum_address(owner),
            Web3.to_checksum_address(spender)
        ).call()
        return raw 

    def ensure_allowance(self, private_key: str, spender: str, amount: float) -> Union[bool, str]:
        account = self.web3.eth.account.from_key(private_key)
        current_allowance = self.allowance(account.address, spender)
        if current_allowance >= amount:
            return True
        return self.approve(private_key, spender, amount)
    
    def transfer(self, private_key: str, to: str, amount: float) -> str:
        account = self.web3.eth.account.from_key(private_key)
        decimals = self.get_decimals()
        value = int(amount * (10 ** decimals))

        
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
            'gas': 100_000,
            'gasPrice': self.web3.to_wei('5', 'gwei'),
        })

        signed = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        return self._format_tx(self.web3.to_hex(tx_hash))

    def approve(self, private_key: str, spender: str, amount: float) -> str:
        account = self.web3.eth.account.from_key(private_key)
        decimals = self.get_decimals()
        value = int(amount * (10 ** decimals))

        if private_key:
            address = Web3.to_checksum_address(self.web3.eth.account.from_key(private_key).address)
        
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")
        txn = self.contract.functions.approve(
            Web3.to_checksum_address(spender),
            value
        ).build_transaction({
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': 100_000,
            'gasPrice': self.web3.to_wei('5', 'gwei'),
        })

        signed = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        return self._format_tx(self.web3.to_hex(tx_hash))





