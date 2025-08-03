import shadowPaySDK
from shadowPaySDK.const import __SHADOWPAY_ABI__ERC20__, __ALLOW_CHAINS__, __SHADOWPAY_CONTRACT_ADDRESS__ERC20__
from web3 import Web3
from typing import Optional
import httpx


class Cheque:
    def __init__(self, w3:Optional[Web3] = None,private_key:Optional[str] = None, ABI = __SHADOWPAY_ABI__ERC20__, allowed_chains = __ALLOW_CHAINS__, retunrn_build_tx:bool = False,address:Optional[str] = None):
        self.w3 = w3

        self.amount = None
        self.token = None
        self.private_key = private_key
        self.ABI = ABI
        self.address = address
        self.return_build_tx = retunrn_build_tx
        self.allowed_chains = allowed_chains
        if self.w3 != None:
            self.__allow__()
    
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
    def get_contract_for_chain(self,chain_id: str):
        c = None
        chain_id = int(chain_id)

        for key,value in __SHADOWPAY_CONTRACT_ADDRESS__ERC20__.items():
            print("Checking address", value, "for chain_id", chain_id)
            if key == chain_id:
                c = value
                contract_address = Web3.to_checksum_address(c)
                contract = self.w3.eth.contract(address=contract_address, abi=__SHADOWPAY_ABI__ERC20__)
                self.contract = contract
                return contract
        raise ValueError(f"Chain {chain_id} is not supported. Supported chains are: {list(__SHADOWPAY_CONTRACT_ADDRESS__ERC20__.keys())}")    
    async def get_address(self):
        if self.address:
            return self.address
        elif self.w3:
            return self.w3.eth.default_account
        else:
            raise ValueError("No address provided or Web3 instance is not set")

    def set_parameters(self,chain_id: Optional[str] = None, w3:Optional[Web3] = None, amount:Optional[int]  = None, private_key:Optional[str] = None, token:Optional[str] = None,address:Optional[str] = None):
        if  w3:
            self.w3 = w3
            self.get_contract_for_chain(chain_id=chain_id or self.w3.eth.chain_id)
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
    
    async def InitCheque(self, amount,  receiver:list, private_key:Optional[str] = None):
        if  not isinstance(receiver,list):
            raise ValueError("Receiver must be a list of addresses, [""0x1234...5678", "0x2345...6789""]")

        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
            print("InitCheque", amount, receiver, key)
        
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")





        receiver = [Web3.to_checksum_address(addr) for addr in receiver]
        estimated_gas = self.contract.functions.InitCheque(receiver).estimate_gas({
            'from': address,
            'value': self.w3.to_wei(amount, 'ether'),
            'gasPrice': self.w3.eth.gas_price
        })
        txn = self.contract.functions.InitCheque(receiver).build_transaction({
            'from': address,
            'value': self.w3.to_wei(amount, 'ether'),
            'nonce': self.w3.eth.get_transaction_count(
                address
            ),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.w3.eth.chain_id
        })
        if self.return_build_tx:
            return {
                "build_tx": txn
            }
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        insert_to_dn = None
        logs = self.get_id(txn_receipt)
        if logs:
            cheque_id = logs
        else:
            cheque_id = None
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id,
        }

 


    async def CashOutCheque(
        self,
        private_key: str,
        cheque_id: str  
    ):
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
            # EIP-1559 style
            base_fee = latest_block['baseFeePerGas']
            priority_fee = self.w3.to_wei(2, 'gwei')  # можно поднять до 5
            max_fee = base_fee + priority_fee * 2

            tx_common.update({
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee
            })
        else:
            # Legacy gas price style
            tx_common.update({
                'gasPrice': self.w3.to_wei('5', 'gwei')
            })

        txn = self.contract.functions.CashOutCheque(
            Web3.to_bytes(hexstr=cheque_id)
        ).build_transaction(tx_common)

        if self.return_build_tx:
            return {"build_tx": txn}

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            return False
        return {"hash": tx_hash.hex()}
    
    async def InitTokenCheque(self, token_address:str, amount, reciver:str, private_key:Optional[str] = None):
        key = private_key or self.private_key

        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        else:
            raise ValueError("No private key or address provided")




        
        erc20 = shadowPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_address)
        decimals = erc20.get_decimals()
        erc20.allowance( 
            spender=self.contract.address, 
            owner=address,
        )
        estimated_gas = self.contract.functions.InitTokenCheque(
            Web3.to_checksum_address(token_address),
            amount,
            Web3.to_checksum_address(reciver)
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price
        })
        txn = self.contract.functions.InitTokenCheque(
            Web3.to_checksum_address(token_address),
            amount,
            Web3.to_checksum_address(reciver)
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price
        })
        if self.return_build_tx:
            return {
                "build_tx": txn
            }
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        logs = self.get_id(txn_receipt)
        if logs:
            cheque_id = logs
        else:
            cheque_id = None
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id,
        }

    async def CashOutTokenCheque(self, cheque_id: str, private_key: Optional[str] = None):
        if private_key is None:
            private_key = self.private_key
        
        account = self.w3.eth.account.from_key(private_key)
        

        
        estimated_gas = self.contract.functions.CashOutTokenCheque(
            Web3.to_bytes(hexstr=cheque_id)  
        ).estimate_gas({
            'from': account.address or self.address,
            'gasPrice': self.w3.eth.gas_price
        })
        txn = self.contract.functions.CashOutTokenCheque(
            Web3.to_bytes(hexstr=cheque_id)  
        ).build_transaction({
            'from': account.address or self.address,
            'nonce': self.w3.eth.get_transaction_count(account.address or self.address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price,
        })
        if self.return_build_tx:
            return {
                "build_tx": txn
            }

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            return False
        return {
            "hash": tx_hash.hex(),
            "status": receipt.status  # 1 = success, 0 = fail
        }
    async def InitTokenChequeSwap(self, token_in:str, amount_in,token_out:str, amount_out, reciver:str, private_key:Optional[str] = None):
        key = private_key or self.private_key
        if key:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(key).address)
        elif self.address:
            address = Web3.to_checksum_address(self.address)
        erc20 = shadowPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_in)
        approve = erc20.allowance(
            spender=self.contract.address, 
            owner=address,
        )
        decimals = erc20.get_decimals()
        erc20.set_params(token_address=token_out)
        token_out_decinals = erc20.get_decimals()
        estimated_gas = self.contract.functions.InitSwapCheque(
            Web3.to_checksum_address(reciver),
            Web3.to_checksum_address(token_in),
            amount_in,
            Web3.to_checksum_address(token_out),
            amount_out,
        ).estimate_gas({
            'from': address,
            'gasPrice': self.w3.eth.gas_price
        })
        txn = self.contract.functions.InitSwapCheque(
            Web3.to_checksum_address(reciver),
            Web3.to_checksum_address(token_in),
            amount_in,
            Web3.to_checksum_address(token_out),
            amount_out
        ).build_transaction({
            'from': address,
            'nonce': self.w3.eth.get_transaction_count(address),
            'gas': estimated_gas,
            'gasPrice': self.w3.eth.gas_price
        })
        if self.return_build_tx:
            return {
                "build_tx": txn
            }
        signed_txn = self.w3.eth.account.sign_transaction(txn, key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        logs = self.get_id(txn_receipt)
        if logs:
            cheque_id = logs
        else:
            cheque_id = None
        if txn_receipt.status != 1:
            return False
        return {
            "hash": txn_hash.hex(),
            "chequeId": cheque_id
        }
    
    async def CashOutSwapCheque(self, cheque_id: str, private_key: Optional[str] = None):
        swapDetail = await self.getSwaoDetail(cheque_id)
        print(swapDetail)
        if private_key is None:
            private_key = self.private_key
        token_out = swapDetail["tokenOut"]
        amount_out = swapDetail["amountOut"]
        erc20 = shadowPaySDK.ERC20Token(w3=self.w3)
        erc20.set_params(token_address=token_out)
        encure_allowance = erc20.allowance(
            spender=self.contract.address, 
            owner=self.address,
        )
        if encure_allowance < amount_out:
            approve = erc20.approve(
                spender=self.contract.address, 
                amount=amount_out,
                private_key=private_key,
                conveted_amount=False
            )
            if not approve:
                return False
        print(f"contract balance: {erc20.get_balance(wallet_address=self.contract.address)}")
        estimated_gas = self.contract.functions.CashOutSwapCheque(
            Web3.to_bytes(hexstr=cheque_id)  
        ).estimate_gas({
            'from': self.w3.eth.account.from_key(private_key).address,
            'gasPrice': self.w3.eth.gas_price
        })
        swa = self.contract.functions.CashOutSwapCheque(
            Web3.to_bytes(hexstr=cheque_id)  
        ).build_transaction({
            'from': self.w3.eth.account.from_key(private_key).address,
            'nonce': self.w3.eth.get_transaction_count(self.w3.eth.account.from_key(private_key).address),
            'gas': 300_000,
            'gasPrice': self.w3.eth.gas_price
        })
        if self.return_build_tx:
            return {
                "build_tx": swa
            }
        signed_txn = self.w3.eth.account.sign_transaction(swa, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return False
        return {
            "hash": tx_hash.hex(),
        }
    
    
    
    
    async def getComunityPool(self):
        fee = self.contract.functions.getCollectedFee().call()
        half_fee_eth = self.w3.from_wei(fee // 2, 'ether')
        return half_fee_eth
    async def getOwner(self):
        return self.contract.functions.getOwner().call()
    async def getTreasery(self):
        return self.contract.functions.getTreasery().call()
    def getChequeInfo(self, cheque_id: str, address: Optional[str] = None):
        ###returns cheque info###
        # s = EVMcheque.getChequeInfo(
        #         cheque_id=chequeId,
        #         address=address
        #     )
        ### cheque_amount = s[0] - amount of cheque in wei
        ### cheque_sender = s[1] - list of sender addresses
        ### cheque_status = s[2] - status of cheque (True - claimed, False - not claimed)
        if not cheque_id:
            raise ValueError("Cheque ID is required")
        if address:
            address = Web3.to_checksum_address(address)

        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        cheque_info = self.contract.functions.getChequeInfo(
            cheque_id_bytes32,
            address or self.address
        ).call()

        return {
            "sender": cheque_info[0],
            "receiver": cheque_info[1],
            "status": "claimed" if cheque_info[2] else "unclaimed",
        }
    def getTokenChequeInfo(self, cheque_id: str):
            # f = EVMcheque.getTokenChequeInfo(
            #     cheque_id=chequeId,
            # )
            ### cheque_sender = s[0] - sender address
            ### cheque_amount = s[1] - receiver address
            ### cheque_status = s[2] - status of cheque (True - claimed, False - not claimed
            
        if not cheque_id:
            raise ValueError("Cheque ID is required")

        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00')
        cheque_info = self.contract.functions.getTokenChequeDetail(cheque_id_bytes32).call()
        return {
                "sender": cheque_info[0],
                "receivers": cheque_info[1],
                "status": "claimed" if cheque_info[2] else "unclaimed",
            }
    async def getSwaoDetail(self, cheque_id: str):
        # f = EVMcheque.getSwaoDetail(
        #     cheque_id=chequeId,
        # )
        # f[0] - tokenOut address,
        # f[1] - amountOut in wei,
        # f[2] - spender,
        # f[3] - receiver,
        # f[4] - claimed
        cheque_id_bytes32 = Web3.to_bytes(hexstr=cheque_id).rjust(32, b'\x00') 
        s = self.contract.functions.getSwapDetail(cheque_id_bytes32).call()
        return {
            "tokenOut": s[0],
            "amountOut": s[1],
            "spender": s[2],
            "receiver": s[3],
            "status": "claimed" if s[4] else "unclaimed"
        }

class NFTcheque:
    def __init__(self, w3:Web3, token:str, amount:int, spender:str):
        self.w3 = w3
        self.token = token
        self.amount = amount
        self.spender = spender

    def InitNFTCheque(self):
        pass

    def CashOutNFTCheque(self):
        pass



















