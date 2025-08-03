import asyncio
import solana
from solana.rpc.async_api import AsyncClient, GetTokenAccountsByOwnerResp
from solders.transaction import Transaction
from solders.system_program import TransferParams as p
import spl
import spl.token
import spl.token.constants
from spl.token.instructions import get_associated_token_address, create_associated_token_account, transfer, close_account, TransferParams
from solders.system_program import transfer as ts
from solders.system_program import TransferParams as tsf
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solana.rpc.types import TxOpts, TokenAccountOpts
from solana.rpc.types import TxOpts
import solders
from solders.message import Message

# from solders.pubkey import Pubkey
# from solders.keypair import Keypair
# from solders.signature import Signature
# from solders.transaction import Transaction
from spl.token.async_client import AsyncToken


from solana.rpc.commitment import Confirmed
from solana.rpc.async_api import AsyncClient
import anchorpy
from anchorpy import Provider, Wallet, Idl
from typing import Optional, Union
import pprint
import httpx
import base64
import re


LAMPORTS_PER_SOL = 1_000_000_000  # 1 SOL = 1,000,000,000 lamports

class SOL:
    def __init__(self, rpc_url = "https://api.mainnet-beta.solana.com", KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None):
            self.rpc_url = rpc_url
    
            self.client = AsyncClient(rpc_url)
            self.KEYPAIR = None
            self.PROGRAM_ID = TOKEN_PROGRAM_ID # Default to the SPL Token Program ID
            self.TOKEN_MINT = TOKEN_MINT
            self.WRAPED_SOL_ID = spl.token.constants.WRAPPED_SOL_MINT
            if KEYPAIR:
                self.set_keypair(KEYPAIR)

    def set_keypair(self, KEYPAIR: Union[str, solders.keypair.Keypair]):
        if isinstance(KEYPAIR, str):
            try:
                self.KEYPAIR = solders.keypair.Keypair.from_base58_string(KEYPAIR)
            except Exception as e:
                raise ValueError(f"Invalid Keypair string: {e}")
        elif isinstance(KEYPAIR, solders.keypair.Keypair):
            self.KEYPAIR = KEYPAIR
        else:
            raise ValueError("KEYPAIR must be a Keypair instance or a base58 encoded string.")

    def set_params(self, rpc_url: Optional[str] = None, KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None):
        if rpc_url:
            self.rpc_url = rpc_url
            self.client = AsyncClient(rpc_url)
        if KEYPAIR:
            self.set_keypair(KEYPAIR)            
        if TOKEN_MINT:
            self.TOKEN_MINT = TOKEN_MINT

    def get_pubkey(self, returnString: Optional[bool] = None):

        
        if self.KEYPAIR:
            pubkey = self.KEYPAIR.pubkey()
            pubkey_str = str(pubkey)
            if returnString:
                return pubkey_str
            return pubkey
        
        raise ValueError("Keypair not set")

    def gen_wallet(self):
        return solders.keypair.Keypair()
    async def get_balance(self):
        resp = await self.client.get_balance(self.get_pubkey())
        lamports = resp.value
        sol_balance = lamports / LAMPORTS_PER_SOL
        return sol_balance  
    async def get_token_accounts_by_owner(self,owner_pubkey: Optional[str] = None):
        if not owner_pubkey:
            print("No owner pubkey provided, using the wallet's pubkey.")
            owner_pubkey = self.get_pubkey(returnString=True)
        headers = {
            "Content-Type": "application/json",
        }
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                str(owner_pubkey),
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.rpc_url, headers=headers, json=body)
            result = response.json()
            accounts = result["result"]["value"]

            token_data = {}
            for acc in accounts:
                parsed = acc["account"]["data"]["parsed"]["info"]
                mint = parsed["mint"]
                ui_amount = parsed["tokenAmount"]["uiAmount"]
                token_data[mint] = {"amount": ui_amount}

            

            return token_data

    async def fetch_metadata_raw(self,mint_address: str):
        METADATA_PROGRAM_ID = solders.pubkey.Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
        mint = solders.pubkey.Pubkey.from_string(mint_address)
        seeds = [
            b"metadata",
            bytes(METADATA_PROGRAM_ID),
            bytes(mint),
        ]
        pda, _ = solders.pubkey.Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                str(pda),
                {"encoding": "base64"}
            ]
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(self.rpc_url, json=payload)
            data = r.json()

        if not data["result"]["value"]:
            return None

        b64_data = data["result"]["value"]["data"][0]
        raw_bytes = base64.b64decode(b64_data)

        name = raw_bytes[1+32+32 : 1+32+32+32].decode("utf-8").rstrip("\x00")
        name = re.sub(r'[^\x20-\x7E]', '', name)     
        return {
            "mint": mint_address,
            "name": name,

        }
    async def transfer_token(self, to: str, amount: float):
       
        if not self.TOKEN_MINT:
            raise ValueError("not set TOKEN_MINT.")
        if not self.KEYPAIR:
            raise ValueError("not set KEYPAIR.")

        sender_pubkey = self.get_pubkey()
        receiver_pubkey = solders.pubkey.Pubkey.from_string(to)
        token_pubkey = solders.pubkey.Pubkey.from_string(self.TOKEN_MINT)

        token = AsyncToken(self.client, token_pubkey, TOKEN_PROGRAM_ID, self.KEYPAIR)
        sender_ata = get_associated_token_address(sender_pubkey, token_pubkey)
        receiver_ata = get_associated_token_address(receiver_pubkey, token_pubkey)

        tx = Transaction()

        res = await self.client.get_account_info(receiver_ata)
        if res.value is None:
            tx.add(
                create_associated_token_account(
                    payer=sender_pubkey,
                    owner=receiver_pubkey,
                    mint=token_pubkey
                )
            )

        decimals = (await token.get_mint_info()).decimals
        real_amount = int(amount * (10 ** decimals))
        params = TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            dest=receiver_ata,
            owner=sender_pubkey,
            amount=real_amount
        )

        tx.add(transfer(params))

        resp = await self.client.send_transaction(tx, self.KEYPAIR, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
        return resp.value


    async def transfer_native(self, to:str, amount: int):
        if not self.KEYPAIR:
            raise ValueError("not set KEYPAIR.")

        sender_pubkey = self.get_pubkey()
        receiver_pubkey = solders.pubkey.Pubkey.from_string(to)
        ixns = [
            ts(tsf(
                from_pubkey=sender_pubkey,
                to_pubkey=receiver_pubkey,
                lamports=int(amount * LAMPORTS_PER_SOL)
            ))
        ]
        msg = Message(ixns, self.get_pubkey())
        latest_blockhash_resp = await self.client.get_latest_blockhash()

        blockhash_str = latest_blockhash_resp.value.blockhash
        tx = Transaction([self.KEYPAIR], msg, blockhash_str)
        resp =  await self.client.send_transaction(tx)
        return resp.value



