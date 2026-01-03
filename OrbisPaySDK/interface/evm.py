from web3 import Web3
import json
import OrbisPaySDK.utils as utils






class EVM():
    def __init__(self, w3:Web3 = None, key = None, address = None):
        self.w3= w3
        self.key = key
        self.address = address

    def set_params(self, w3:Web3 = None,key:str = None, address:str = None):
        if w3:
            self.w3 = w3
        if key:
            self.key = key
        if address:
            self.address = address
    def get_address(self):
        acc = self.w3.eth.account.from_key(self.key)
        return acc.address


    def ensure_checksum(self,w3: Web3, addr: str) -> str:
        if addr is None:
            return None
        try:
            return Web3.to_checksum_address(addr)
        except Exception as e:
            raise ValueError(f"Invalid address '{addr}': {e}")


    

    def sign_and_sand(self,tx:dict = None,key:str = None,w3:Web3 = None,send:bool = False):
        

        
        signed = w3.eth.account.sign_transaction(tx)
        
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
        if tx_receipt.status != 1:
            return False
        return f"{self.w3.to_hex(tx_hash)}"
    def sign(self,tx:dict = None,key:str = None,w3:Web3 = None,send:bool = False):
        if w3 is None:
            w3 = self.w3
        if key is None:
            key = self.key

        
        txid = w3.eth.account.sign_transaction(tx, key)
        


        return txid
            
    def send(self, tx):
        tx_hash = self.w3.eth.send_raw_transaction(tx.raw_transaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
        if tx_receipt.status != 1:
            return False
        return f"{self.w3.to_hex(tx_hash)}"
    