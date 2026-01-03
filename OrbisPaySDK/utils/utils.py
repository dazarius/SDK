from OrbisPaySDK.const import __SOL__MINT__,LAMPORTS_PER_SOL
from OrbisPaySDK.interface import (erc20, erc721, sol)
from OrbisPaySDK.types import EVMcheque, SOLcheque
from web3 import Web3
import dataclasses
from dataclasses import dataclass
from typing import Union



@dataclass
class TokenERC20:
    symbal:any
    name:any
    decimals:any
    icon:any = None


@dataclass
class baseChainSettings:
    name:str 
    rpc:str 

@dataclass
class baseTranserParams:
    from_:any
    to:str | list
    token:any
    bc:any
    amount_ui:any
    amount:any
    contract:any
    chain:baseChainSettings
    

@dataclass
class Chaque:
    
    baseTranserParam:baseTranserParams = None 
    contract:str = None
    




def extractedParamsChain(data):
    for key in data["chains"]:
        pass
def extractParamsForCheque(transferParams:baseTranserParams) -> Chaque:
    c = Chaque(baseTranserParam=transferParams)
    return c
def extractParamsForTransfer(data)-> baseTranserParams: 
    
    t = baseTranserParams(None,None,None,None,None,None,None,None)
    c = baseChainSettings(None,None)
    transferParams = data["transferParams"]
    chainParms = data["chains"]
    print(t.__dict__.keys())
    for key in transferParams:
        for i in t.__dict__.keys():
            if key == i:
                t.__dict__.__setitem__(key, transferParams[key])
    for key in chainParms:
        for i in t.__dict__.keys():
            if key == i:
                t.__dict__.__setitem__(key, chainParms[key])
    t.chain = c
    
    return t
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
def convert_to_wei():
    pass
def _format_tx(explorer,tx_hash: str) -> str:
    if explorer:
        return f"{explorer.rstrip('/')}/tx/{tx_hash}"
    return tx_hash



if __name__ == "__main__":
    c = extractParamsForTransfer(data={
        "transferParams":{
            "bc":"EVM",
            "to":["fdcas"],
            "from_":"sca",
            "token":"afs",
            "amount_ui":"{:.18f}".format(0.000000000005).rstrip("0").rstrip("."),
            "amount":Web3.to_wei(0.000000000005, "ether"),
            "contract":"ads"
        },
        "chains":{
            "name":"data",
            "rpc":"adsf"

        }        
    })
    d = extractParamsForCheque(c)
    print(d.baseTranserParam)