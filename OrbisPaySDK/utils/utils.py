from OrbisPaySDK.const import __SOL__MINT__,LAMPORTS_PER_SOL
from OrbisPaySDK.interface import (erc20, erc721, sol)
from OrbisPaySDK.types import EVMcheque, SOLcheque
from web3 import Web3

def modify_tx(tx: dict, w3: Web3, from_addr: str = None, to_addr: str = None, value: int = None) -> dict:
    chain_id  = w3.eth.chain_id

    nonce  = w3.eth.get_transaction_count(from_addr)
    latest = w3.eth.get_block('latest')
    gas    = w3.eth.estimate_gas({'from': from_addr, 'to': to_addr, 'value': value})

    
    if latest.get('baseFeePerGas') is not None:
        tip = w3.eth.max_priority_fee
        base = latest['baseFeePerGas']
        max_fee = base * 2 + tip
        if tx == {}:
            tx = {
                'type': 0x2, 'chainId': chain_id, 'nonce': nonce,
                'to': to_addr, 'value': value, 'gas': int(gas),
                'maxPriorityFeePerGas': int(tip),
                'maxFeePerGas': int(max_fee),
            }
    else:
        if tx == {}:
            tx = {
                'chainId': chain_id, 'nonce': nonce,
                'to': to_addr, 'value': value, 'gas': int(gas),
                'gasPrice': int(w3.eth.gas_price * 1.10),
            }
    return tx