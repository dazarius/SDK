from web3 import Web3
import json






class EVM():
    def __init__(self, w3:Web3 = None, key = None, address = None):
        self.w3= w3
        self.key = key





    def ensure_checksum(self,w3: Web3, addr: str) -> str:
        if addr is None:
            return None
        try:
            return Web3.to_checksum_address(addr)
        except Exception as e:
            raise ValueError(f"Invalid address '{addr}': {e}")


    def modify_tx(self, w3: Web3, from_addr: str, to_addr: str, value: int, data: bytes = b"", gas_limit_fallback: int = 21000) -> dict:
        from_addr = self.ensure_checksum(w3, from_addr)
        to_addr = self.ensure_checksum(w3, to_addr)

        nonce = w3.eth.get_transaction_count(from_addr)
        chain_id = w3.eth.chain_id

        # estimate gas (безопасно)
        try:
            gas_est = w3.eth.estimate_gas({
                "from": from_addr,
                "to": to_addr,
                "value": int(value),
                "data": data
            })
        except Exception as e:
            print("estimate_gas failed:", e)
            gas_est = gas_limit_fallback

        # fetch latest block to detect EIP-1559
        latest = w3.eth.get_block("latest")
        if latest.get("baseFeePerGas") is not None:
            # EIP-1559 chain
            try:
                max_priority = w3.eth.max_priority_fee  # helper
            except Exception:
                # fallback small tip
                max_priority = w3.to_wei(1, "gwei")
            base = latest["baseFeePerGas"]
            max_fee = int(base * 2 + max_priority)
            tx = {
                "type": 2,
                "chainId": chain_id,
                "nonce": nonce,
                "to": to_addr,
                "value": int(value),
                "gas": int(gas_est),
                "maxPriorityFeePerGas": int(max_priority),
                "maxFeePerGas": int(max_fee),
                "data": data,
            }
        else:
            # legacy tx
            gas_price = w3.eth.gas_price
            tx = {
                "chainId": chain_id,
                "nonce": nonce,
                "to": to_addr,
                "value": int(value),
                "gas": int(gas_est),
                "gasPrice": int(gas_price),
                "data": data,
            }
        
        return tx

    def sign(self,tx:dict = None,key:str = None,w3:Web3 = None,send:bool = False):
        


        
        modify_tx = self.modify_tx(w3=w3,to_addr=tx["to"], from_addr=tx["from"], value=tx["value"])
        txid = w3.eth.account.sign_transaction(modify_tx,key)
        
        if send:
            s = w3.eth.send_raw_transaction(txid)
            txid = w3.eth.wait_for_transaction_receipt(s)
        return txid
        

