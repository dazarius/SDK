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
from OrbisPaySDK.const import __SOL__NATIVE__, WRAPED_SOL, __SOL__WS__
from typing import List, Dict, Any, Optional


# from solders.pubkey import Pubkey
from solders.keypair import Keypair
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
import base58


LAMPORTS_PER_SOL = 1_000_000_000  # 1 SOL = 1,000,000,000 lamports
coigeco_id = "sol"
currency_sym = "$"




class SOL:
    def __init__(self, rpc_url = "https://api.mainnet-beta.solana.com", KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None,build_tx:bool = False):
            self.rpc_url = rpc_url
            self.build_tx = build_tx
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

    def set_params(self, rpc_url: Optional[str] = None, KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None, build_tx = None):
        if rpc_url:
            self.rpc_url = rpc_url
            self.client = AsyncClient(rpc_url)
        if KEYPAIR:
            self.set_keypair(KEYPAIR)            
        if TOKEN_MINT:
            self.TOKEN_MINT = TOKEN_MINT
        if build_tx:
            self.build_tx = build_tx

    def get_pubkey(self, returnString: Optional[bool] = None):

        
        if self.KEYPAIR:
            pubkey = self.KEYPAIR.pubkey()
            pubkey_str = str(pubkey)
            if returnString:
                return pubkey_str
            return pubkey
        
        raise ValueError("Keypair not set")

    def gen_wallet(self):
        acc = solders.keypair.Keypair()
        return {
            "private_key": base58.b58encode(bytes(acc)).decode("utf-8"),
            "public_key": str(acc.pubkey())
        }
    async def get_balance(self):
        resp = await self.client.get_balance(self.get_pubkey())
        lamports = resp.value
        sol_balance = lamports / LAMPORTS_PER_SOL
        return {
            "balance": sol_balance,
            "ui_balance": sol_balance,
            "string_ui_balance": f"{sol_balance:.9f}",
            "raw_balance": lamports,
        }  
    async def get_balance_batch(self, address_list: list) -> dict:
        """
        Get SOL balances for multiple addresses in parallel.

        Returns:
            dict {address: {"balance": float, "raw_balance": int}}
        """
        from solders.pubkey import Pubkey

        async def fetch(addr):
            try:
                pubkey = Pubkey.from_string(addr)
                resp = await self.client.get_balance(pubkey)
                lamports = resp.value
                return addr, {"balance": lamports / LAMPORTS_PER_SOL, "raw_balance": lamports}
            except Exception:
                return addr, {"balance": 0.0, "raw_balance": 0}

        results = await asyncio.gather(*[fetch(addr) for addr in address_list])
        return dict(results)

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
                tokenAmount = parsed["tokenAmount"]
                mint = parsed["mint"]
                metadata = await self.fetch_metadata_raw(mint)

                ui_amount = parsed["tokenAmount"]["uiAmount"]
                token_data[mint] = {
                    "ui_balance": ui_amount,
                    "raw_balance": tokenAmount["amount"], 
                    "string_ui_balance": tokenAmount["uiAmountString"],
                    "fullData": acc,
                    "metadata": metadata
                    }

            

            return token_data
    async def get_token_balance(self, data:dict):
        owner_pubkey:list = data.get("owner_pubkeys")
        tokens:list = data.get("tokens")
        if not owner_pubkey or not tokens:
            print("No owner pubkey or token list provided, using the wallet's pubkey.")
        for owner in owner_pubkey:
            pass
        pass
    async def fetch_metadata_raw(self, mint_address: str):
        METADATA_PROGRAM_ID = solders.pubkey.Pubkey.from_string(
            "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        )
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
            "params": [str(pda), {"encoding": "base64"}]
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(self.rpc_url, json=payload)
            data = r.json()

     

        result = data.get("result", {})
        if not result or not result.get("value"):
            return None

        b64_data = result["value"]["data"][0]
        raw_bytes = base64.b64decode(b64_data)


        # Metaplex metadata layout:
        # [0]      = discriminator (1 byte)
        # [1:33]   = update authority (32 bytes)
        # [33:65]  = mint (32 bytes)
        # [65:69]  = name length (4 bytes, little-endian u32)
        # [69:...]  = name string

        offset = 65

        name_len = int.from_bytes(raw_bytes[offset:offset+4], "little")
        offset += 4
        name = raw_bytes[offset:offset+name_len].decode("utf-8", errors="ignore").rstrip("\x00")
        offset += name_len

        symbol_len = int.from_bytes(raw_bytes[offset:offset+4], "little")
        offset += 4
        symbol = raw_bytes[offset:offset+symbol_len].decode("utf-8", errors="ignore").rstrip("\x00")
        offset += symbol_len

        uri_len = int.from_bytes(raw_bytes[offset:offset+4], "little")
        offset += 4
        uri = raw_bytes[offset:offset+uri_len].decode("utf-8", errors="ignore").rstrip("\x00")

        return {
            "mint": mint_address,
            "name": name.strip(),
            "symbol": symbol.strip(),
            "uri": uri.strip(),  
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
        if self.build_tx:
            return tx

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
                lamports=amount * LAMPORTS_PER_SOL
            ))
        ]
        msg = Message(ixns, self.get_pubkey())
        latest_blockhash_resp = await self.client.get_latest_blockhash()

        blockhash_str = latest_blockhash_resp.value.blockhash
        tx = Transaction([self.KEYPAIR], msg, blockhash_str)
        if self.build_tx:
            return tx
        resp =  await self.client.send_transaction(tx)
        return resp.value
    async def build_transaction(self,data):
        recent_blockhash = self.client.get_latest_blockhash(Confirmed).value.blockhash

        _from = solders.pubkey.Pubkey.from_string(data["_from"])
        _to = solders.pubkey.Pubkey.from_string(data["_to"])
        _amount = data["_amount"]
        
                
        tx = Transaction()
        if data["_token"] == __SOL__NATIVE__:
            lamports = int(_amount * LAMPORTS_PER_SOL)
            instruction = transfer(
                TransferParams(
                    from_pubkey=_from,
                    to_pubkey=_to,
                    lamports=lamports
                )
            )

            message = Message([instruction], _from)
            tx = Transaction(message, recent_blockhash)
        return {
            "tx": tx.to_solders().to_bytes().hex(),
            "recent_blockhash": str(recent_blockhash),
        }
    async def _send_tx(self, tx, key: str = None):
        """
        Аналог EVM sign_and_send для Solana.
        tx может быть объектом Transaction или Message.
        """
        try:
            # 1. Подготовка ключа (Keypair)
            # Если ключ передан как строка Base58, конвертим его в Keypair
            if key:
                from solders.keypair import Keypair
                signer = Keypair.from_base58_string(key)
            else:
                signer = self.KEYPAIR # Берем дефолтный из класса

            if not signer:
                raise ValueError("No keypair provided for signing")

            # 2. Подпись транзакции
            # В Solana Transaction(signatures, message, blockhash)
            # Если tx пришел как готовый объект, мы просто добавляем подпись
            if hasattr(tx, 'message'):
                # Собираем финальную транзу с подписью
                from solders.transaction import Transaction
                final_tx = Transaction([signer], tx.message, tx.recent_blockhash)
            else:
                # Если tx это список инструкций (ixns), нужно сначала собрать Transaction
                # Но лучше передавать уже собранный объект Transaction из build_tx
                raise ValueError("tx must be a Transaction object with message and blockhash")

            # 3. Отправка (аналог send_raw_transaction)
            # send_transaction сам делает serialize() под капотом
            resp = await self.client.send_transaction(final_tx)
            tx_hash = str(resp.value) # Это сигнатура (хеш)

            # 4. Ожидание подтверждения (аналог wait_for_transaction_receipt)
            # В Solana используем confirm_transaction
            confirm = await self.client.confirm_transaction(resp.value)
            
            if not confirm.value:
                return False

            # 5. Возвращаем результат в твоем формате
            # tx_to_human_view для соланы напишем ниже, если нужно
            return {
                "tx": tx_hash,
                "meta": {
                    "symbol": "SOL",
                    "status": "Success",
                    "signature": tx_hash
                }
            }

        except Exception as e:
            return False
    async def  _parse_transaction(self, signature: str, retries: int = 5, retry_delay: float = 2.0) -> dict:

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "finalized",
                }
            ]
        }

        data = None
        for attempt in range(retries):
            async with httpx.AsyncClient() as client:
                r = await client.post(self.rpc_url, json=payload, timeout=15)
                data = r.json()
            if data.get("result"):
                break
            if attempt < retries - 1:
                await asyncio.sleep(retry_delay)

        tx = data.get("result")
        if not tx:
            return {"error": "Transaction not found", "signature": signature}

        meta       = tx.get("meta", {}) or {}
        message    = tx.get("transaction", {}).get("message", {})
        block_time = tx.get("blockTime")
        fee        = meta.get("fee", 0)
        err        = meta.get("err")

        # Аккаунты
        account_keys = [
            acc.get("pubkey") if isinstance(acc, dict) else acc
            for acc in message.get("accountKeys", [])
        ]

        result = {
            "signature":   signature,
            "status":      "failed" if err else "success",
            "error":       err,
            "slot":        tx.get("slot"),
            "timestamp":   block_time,
            "fee_lamports": fee,
            "fee_sol":     fee / LAMPORTS_PER_SOL,
            "transfers":   [],
            "token_transfers": [],
            "programs":    [],
            "tx_type":     "unknown",
        }

        # SOL балансы
        pre_balances  = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
            diff = post - pre
            if diff != 0 and i < len(account_keys):
                result["transfers"].append({
                    "account":        account_keys[i],
                    "change_lamports": diff,
                    "change_sol":     diff / LAMPORTS_PER_SOL,
                    "direction":      "in" if diff > 0 else "out",
                })

        pre_token  = meta.get("preTokenBalances",  []) or []
        post_token = meta.get("postTokenBalances", []) or []
        post_token_map = {t["accountIndex"]: t for t in post_token}

        for pre in pre_token:
            idx         = pre["accountIndex"]
            post        = post_token_map.get(idx, {})
            pre_amount  = float(pre.get("uiTokenAmount", {}).get("uiAmount") or 0)
            post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount") or 0)
            diff        = post_amount - pre_amount

            if diff != 0:
                result["token_transfers"].append({
                    "account":   account_keys[idx] if idx < len(account_keys) else "unknown",
                    "mint":      pre.get("mint"),
                    "owner":     pre.get("owner"),
                    "change":    diff,
                    "direction": "in" if diff > 0 else "out",
                    "decimals":  pre.get("uiTokenAmount", {}).get("decimals"),
                })

        for ix in message.get("instructions", []):
            program = ix.get("program") or ix.get("programId")
            parsed  = ix.get("parsed")
            prog_info = {"program": program}
            if parsed:
                prog_info["type"] = parsed.get("type")
                prog_info["info"] = parsed.get("info")
            result["programs"].append(prog_info)

        programs = [p.get("program") for p in result["programs"]]
        types    = [p.get("type")    for p in result["programs"]]

        if "spl-token" in programs and any(t in types for t in ("transfer", "transferChecked")):
            result["tx_type"] = "token_transfer"
        elif any(p in programs for p in ("Jupiter", "jupiterAggregator")):
            result["tx_type"] = "swap"
        elif result["transfers"] and not result["token_transfers"]:
            result["tx_type"] = "sol_transfer"
        elif result["token_transfers"]:
            result["tx_type"] = "swap"

        return result

    async def monitor(
        self,
        callback,
        addresses: list = None,
        ws_url: str = __SOL__WS__,
        commitment: str = "finalized",
        reconnect_delay: float = 3.0,
        parsed: bool = False,
        batch_size: int = 10,
    ):
        """
        Monitor Solana blockchain via WebSocket for new transactions.

        Args:
            callback:     async function — всегда вызывается с raw value dict
                          если parsed=True — дополнительно вызывается с {sig: tx}
                          когда накопится batch_size транзакций
            addresses:    список адресов для фильтра (пусто = все транзакции)
            ws_url:       WebSocket endpoint (default: __SOL__WS__)
            commitment:   "finalized" | "confirmed" | "processed"
            reconnect_delay: секунд до переподключения при обрыве
            parsed:       если True — дополнительно парсить пачками
            batch_size:   сколько сигнатур накопить перед парсингом
        """
        import websockets
        import json as _json

        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": addresses} if addresses else "all",
                {"commitment": commitment},
            ],
        }

        queue: list[str] = []

        sem = asyncio.Semaphore(3)

        async def parse_one(sig):
            async with sem:
                return await self._parse_transaction(sig)

        async def flush_queue():
            batch, queue[:] = queue[:], []
            results = await asyncio.gather(
                *[parse_one(sig) for sig in batch],
                return_exceptions=False,
            )
            parsed_batch = {
                sig: tx for sig, tx in zip(batch, results)
                if "error" not in tx
            }
            if parsed_batch:
                try:
                    await callback({"parsed": parsed_batch})
                except Exception as cb_err:
                    pass

        while True:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=30,
                ) as ws:
                    await ws.send(_json.dumps(subscribe_msg))
                    await ws.recv()  # skip subscription confirmation

                    while True:
                        raw = await ws.recv()
                        msg = _json.loads(raw)
                        params = msg.get("params")
                        if not params:
                            continue

                        value = params.get("result", {}).get("value", {})
                        signature = value.get("signature")
                        if not signature:
                            continue

                        try:
                            await callback(value)
                        except Exception as cb_err:
                            print(f"[monitor] callback error: {cb_err}")

                        if parsed:
                            queue.append(signature)
                            if len(queue) >= batch_size:
                                asyncio.create_task(flush_queue())

            except (websockets.ConnectionClosed, websockets.InvalidStatusCode):
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                print(f"[monitor] error: {e}")
                await asyncio.sleep(reconnect_delay)
            except (websockets.ConnectionClosed, websockets.InvalidStatusCode):
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                print(f"[monitor] error: {e}")
                await asyncio.sleep(reconnect_delay)

    async def get_transactions(self, limit: int = 10, before: str = None) -> list[dict]:
       
        # 1. Получаем сигнатуры
        params = [str(self.get_pubkey()), {"limit": limit}]
        if before:
            params[1]["before"] = before

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": params,
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(self.rpc_url, json=payload, timeout=15)
            data = r.json()

        signatures = [s["signature"] for s in (data.get("result") or [])]

        # 2. Парсим каждую параллельно
        import asyncio
        tasks = [self._parse_transaction(sig) for sig in signatures]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]



# if __name__ == "__main__":
#     s = SOL()
#     instruction = [Instruction(
#     Instruction {
#         program_id: 11111111111111111111111111111111,
#         accounts: [
#             AccountMeta {
#                 pubkey: C3MhUqKFRkkTRBRZcH7EKoD8c1iose9T3tPb7qiytzxs,
#                 is_signer: true,
#                 is_writable: true,
#             },
#             AccountMeta {
#                 pubkey: C3MhUqKFRkkTRBRZcH7EKoD8c1iose9T3tPb7qiytzxs,
#                 is_signer: false,
#                 is_writable: true,
#             },
#         ],
#         data: [
#             2,
#             0,
#             0,
#             0,
#             0,
#             225,
#             245,
#             5,
#             0,
#             0,
#             0,
#             0,
#         ],
#     },
# )]

#     run = s.sign_and_send()

