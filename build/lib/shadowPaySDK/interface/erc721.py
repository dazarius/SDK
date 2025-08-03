from web3 import Web3
import json
from typing import Optional, Union



ERC721_ABI = json.loads("""[
  {"constant":true,"inputs":[{"name":"_tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"name":"owner","type":"address"}],"type":"function"},
  {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
  {"constant":true,"inputs":[{"name":"_tokenId","type":"uint256"}],"name":"tokenURI","outputs":[{"name":"uri","type":"string"}],"type":"function"},
  {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_tokenId","type":"uint256"}],"name":"transfer","outputs":[],"type":"function"},
  {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_tokenId","type":"uint256"}],"name":"approve","outputs":[],"type":"function"},
  {"constant":true,"inputs":[{"name":"_tokenId","type":"uint256"}],"name":"getApproved","outputs":[{"name":"approved","type":"address"}],"type":"function"}
]""")

class ERC721Token:
    def __init__(self, web3: Web3, address: str):   
        self.web3 = web3
        self.address = Web3.to_checksum_address(address)
        self.contract = self.web3.eth.contract(address=self.address, abi=ERC721_ABI)

    def owner_of(self, token_id: int) -> str:
        return self.contract.functions.ownerOf(token_id).call()

    def balance_of(self, owner: Union[str, bytes]) -> int:
        return self.contract.functions.balanceOf(Web3.to_checksum_address(owner)).call()

    def token_uri(self, token_id: int) -> str:
        return self.contract.functions.tokenURI(token_id).call()

    def get_approved(self, token_id: int) -> str:
        return self.contract.functions.getApproved(token_id).call()

    def approve(self, private_key: str, to: str, token_id: int) -> str:
        account = self.web3.eth.account.from_key(private_key)

        txn = self.contract.functions.approve(
            Web3.to_checksum_address(to),
            token_id
        ).build_transaction({
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': 100_000,
            'gasPrice': self.web3.to_wei('5', 'gwei')
        })

        signed = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return self.web3.to_hex(tx_hash)

    def transfer(self, private_key: str, to: str, token_id: int) -> str:
        account = self.web3.eth.account.from_key(private_key)

        txn = self.contract.functions.transfer(
            Web3.to_checksum_address(to),
            token_id
        ).build_transaction({
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': 150_000,
            'gasPrice': self.web3.to_wei('5', 'gwei')
        })

        signed = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return self.web3.to_hex(tx_hash)