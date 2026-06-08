import asyncio
import solana
from solana.rpc.async_api import AsyncClient, GetTokenAccountsByOwnerResp
from solders.transaction import Transaction

from solders.system_program import TransferParams as p
import spl
import spl.token
import spl.token.constants
from spl.token.instructions import get_associated_token_address, create_associated_token_account, transfer, close_account, CloseAccountParams, TransferParams
from solders.system_program import transfer as ts
from solders.system_program import TransferParams as tsf
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solana.rpc.types import TxOpts, TokenAccountOpts
from solana.rpc.types import TxOpts
import solders
from solders.message import Message
from OrbisPaySDK.const import __SOL__NATIVE__, WRAPED_SOL, __SOL__WS__, __SOL__WS__DEVNET__, __SOL__EXPLORERS__
from typing import List, Dict, Any, Optional


# from solders.pubkey import Pubkey
from solders.keypair import Keypair
# from solders.signature import Signature
# from solders.transaction import Transaction

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
from jupiter_python_sdk.jupiter import Jupiter

LAMPORTS_PER_SOL = 1_000_000_000  # 1 SOL = 1,000,000,000 lamports
coigeco_id = "sol"
currency_sym = "$"




class SOL:
    def __init__(self, rpc_url = "https://api.mainnet-beta.solana.com", KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None,build_tx:bool = False):
        """
        Args:
            rpc_url    (str):           Solana RPC endpoint. Default: mainnet-beta.
            KEYPAIR    (str|Keypair):   Base58 private key string or Keypair object. Optional.
            TOKEN_MINT (str):           SPL token mint address used by transfer_token. Optional.
            build_tx   (bool):          If True, transfer_* methods return a Transaction object
                                        instead of broadcasting to the network.
        """
        self.rpc_url = rpc_url
        self.build_tx = build_tx
        self.client = AsyncClient(rpc_url)
        self.KEYPAIR = None
        self.external_signers: list = []  # persistent co-signers added via add_signer()
        self.PROGRAM_ID = TOKEN_PROGRAM_ID # Default to the SPL Token Program ID
        self.TOKEN_MINT = TOKEN_MINT
        self.WRAPED_SOL_ID = spl.token.constants.WRAPPED_SOL_MINT
        if KEYPAIR:
            self.set_keypair(KEYPAIR)
    

    def set_keypair(self, KEYPAIR: Union[str, solders.keypair.Keypair]):
        """
        Sets the keypair used to sign transactions.

        Args:
            KEYPAIR (str | Keypair): Base58 private key string or a Keypair object.

        Raises:
            ValueError: If the string is invalid or the type is unsupported.
        """
        if isinstance(KEYPAIR, str):
            try:
                self.KEYPAIR = solders.keypair.Keypair.from_base58_string(KEYPAIR)
            except Exception as e:
                raise ValueError(f"Invalid Keypair string: {e}")
        elif isinstance(KEYPAIR, solders.keypair.Keypair):
            self.KEYPAIR = KEYPAIR
        else:
            raise ValueError("KEYPAIR must be a Keypair instance or a base58 encoded string.")

    def add_signer(self, keypair) -> None:
        """
        Adds a keypair to the persistent external_signers list.

        The signer will be automatically included in every subsequent transaction
        built by send_instructions and multi_send_* methods. Duplicates are ignored.

        Args:
            keypair (str | Keypair): Base58 private key string or Keypair object.
        """
        kp = self._resolve_keypair(keypair)
        pk = str(kp.pubkey())
        if not any(str(s.pubkey()) == pk for s in self.external_signers):
            self.external_signers.append(kp)

    def remove_signer(self, keypair) -> bool:
        """
        Removes a keypair from the external_signers list.

        Args:
            keypair (str | Keypair): Base58 private key string, Keypair object,
                                     or Base58 public key string.

        Returns:
            bool: True if the signer was found and removed, False otherwise.
        """
        try:
            kp = self._resolve_keypair(keypair)
            pk = str(kp.pubkey())
        except Exception:
            pk = str(keypair)  # treat as pubkey string directly

        before = len(self.external_signers)
        self.external_signers = [s for s in self.external_signers if str(s.pubkey()) != pk]
        return len(self.external_signers) < before

    def set_params(self, rpc_url: Optional[str] = None, KEYPAIR: Optional[Union[str, solders.keypair.Keypair]] = None,TOKEN_MINT: Optional[str] = None, build_tx = None):
        """
        Updates instance parameters at runtime without recreating the object.

        Args:
            rpc_url    (str):         New RPC endpoint.
            KEYPAIR    (str|Keypair): New keypair.
            TOKEN_MINT (str):         New token mint address.
            build_tx   (bool):        New value for the build_tx flag.
        """
        if rpc_url:
            self.rpc_url = rpc_url
            self.client = AsyncClient(rpc_url)
        if KEYPAIR:
            self.set_keypair(KEYPAIR)            
        if TOKEN_MINT:
            self.TOKEN_MINT = TOKEN_MINT
        if build_tx:
            self.build_tx = build_tx

    def get_pubkey(self, addr = None, returnString: Optional[bool] = None):
        """
        Returns the public key derived from the current keypair.

        Args:
            returnString (bool): If True, returns a Base58 string; otherwise returns a Pubkey object.

        Returns:
            str | Pubkey: The public key.

        Raises:
            ValueError: If no keypair has been set.
        """
        if addr:
            return solders.pubkey.Pubkey.from_string(addr)
        if self.KEYPAIR:
            pubkey = self.KEYPAIR.pubkey()
            pubkey_str = str(pubkey)
            if returnString:
                return pubkey_str
            return pubkey
        
        raise ValueError("Keypair not set")

    @staticmethod
    def format_tx_url(explorer: str, signature: str, _format = "/tx/") -> str:
        """
        Builds a block explorer URL for a given transaction signature.

        Args:
            explorer  (str): Explorer base URL or alias "mainnet" / "devnet".
            signature (str): Transaction signature.
            _format   (str): Unused legacy parameter.

        Returns:
            str: Full URL, e.g. https://solscan.io/tx/<signature>.
        """
        from urllib.parse import urlparse, urlunparse
        if explorer in ["mainnet", "devnet"]:
            explorer = __SOL__EXPLORERS__.get(explorer, __SOL__EXPLORERS__["mainnet"]).get("solscan")
        p = urlparse(explorer)
        path = p.path.rstrip("/") + f"/tx/{signature}"
        return urlunparse((p.scheme, p.netloc, path, p.params, p.query, p.fragment))

    def sign_msg(self, msg: str, keypair=None) -> str:
        """
        Signs an arbitrary UTF-8 message with the keypair.

        Args:
            msg     (str):     Message to sign.
            keypair (Keypair): Optional keypair to use instead of self.KEYPAIR.

        Returns:
            str: 64-byte Ed25519 signature as a hex string.

        Raises:
            ValueError: If no keypair is provided and none is set on the instance.
        """
        import hashlib
        kp = keypair or self.KEYPAIR
        if not kp:
            raise ValueError("Keypair not set")
        msg_bytes = msg.encode("utf-8")
        signed = kp.sign_message(msg_bytes)
        return bytes(signed).hex()

    def gen_wallet(self):
        """
        Generates a new random Solana wallet.

        Returns:
            dict: {
                "private_key": str,   # Base58-encoded full keypair (64 bytes)
                "public_key":  str,   # Base58 public key
            }
        """
        acc = solders.keypair.Keypair()
        return {
            "private_key": base58.b58encode(bytes(acc)).decode("utf-8"),
            "public_key": str(acc.pubkey())
        }
    async def get_balance(self):
        """
        Returns the SOL balance of the wallet set in self.KEYPAIR.

        Returns:
            dict: {
                "balance":           float,  # SOL amount
                "ui_balance":        float,  # same as balance (compatibility alias)
                "string_ui_balance": str,    # formatted string, e.g. "0.000000000"
                "raw_balance":       int,    # amount in lamports
            }
        """
        resp = await self.client.get_balance(self.get_pubkey())
        lamports = resp.value
        sol_balance = lamports / LAMPORTS_PER_SOL
        return {
            "balance": sol_balance,
            "ui_balance": sol_balance,
            "string_ui_balance": f"{sol_balance:.9f}",
            "raw_balance": lamports,
        }  
    async def get_balance_batch(
        self,
        address_list: list,
        include_tokens: bool = True,
    ) -> dict:
        """
        Fetches SOL balances for multiple addresses concurrently.
        Optionally also fetches all SPL token balances via get_token_accounts_by_owner.

        Args:
            address_list   (list[str]): List of Base58 public key strings.
            include_tokens (bool):      If True, each entry also contains a "tokens" key
                                        with the output of get_token_accounts_by_owner.

        Returns:
            dict: {
                address: {
                    "balance":     float,       # SOL amount
                    "raw_balance": int,          # lamports
                    "tokens":      dict | None,  # present only if include_tokens=True
                                                 # { mint: {ui_balance, raw_balance, ...} }
                }
            }
            On error for a given address the SOL fields are 0 and tokens is {}.
        """
        from solders.pubkey import Pubkey

        async def fetch(addr):
            try:
                pubkey = Pubkey.from_string(addr)
                resp = await self.client.get_balance(pubkey)
                lamports = resp.value
                entry = {
                    "balance":     lamports / LAMPORTS_PER_SOL,
                    "raw_balance": lamports,
                }
                if include_tokens:
                    try:
                        entry["tokens"] = await self.get_token_accounts_by_owner(addr)
                    except Exception:
                        entry["tokens"] = {}
                return addr, entry
            except Exception:
                entry = {"balance": 0.0, "raw_balance": 0}
                if include_tokens:
                    entry["tokens"] = {}
                return addr, entry

        results = await asyncio.gather(*[fetch(addr) for addr in address_list])
        return dict(results)

    async def get_token_accounts_by_owner(self, owner_pubkey: Optional[str] = None):
        """
        Returns all SPL token accounts owned by an address, with balances and Metaplex metadata.

        Args:
            owner_pubkey (str): Base58 owner address. Falls back to self.KEYPAIR if not provided.

        Returns:
            dict: { mint_address: {
                "ui_balance":        float | None,
                "raw_balance":       str,         # raw integer amount as string
                "string_ui_balance": str,
                "fullData":          dict,         # raw RPC response for the account
                "metadata":          dict | None,  # Metaplex name, symbol, uri
            }}
        """
        if not owner_pubkey:
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
    async def get_token_balance(self, data: dict):
        """
        Fetches balances and Metaplex metadata for specific token mints across multiple wallets.

        Args:
            data (dict): {
                "owner_pubkeys": list[str],  # owner addresses; falls back to self.KEYPAIR
                "tokens":        list[str],  # token mint addresses to query
            }

        Returns:
            dict: {
                owner_address: {
                    mint_address: {
                        "ui_balance":        float,
                        "raw_balance":       str,
                        "string_ui_balance": str,
                        "metadata":          dict | None,  # name, symbol, uri
                    }
                }
            }
        """
        from solders.pubkey import Pubkey

        owner_pubkeys: list = data.get("owner_pubkeys") or []
        tokens: list = data.get("tokens") or []

        if not owner_pubkeys:
            owner_pubkeys = [self.get_pubkey(returnString=True)]
        if not tokens:
            return {}

        unique_mints = list(set(tokens))
        meta_results = await asyncio.gather(
            *[self.fetch_metadata_raw(mint) for mint in unique_mints],
            return_exceptions=True,
        )
        metadata_map = {
            mint: (meta if not isinstance(meta, Exception) else None)
            for mint, meta in zip(unique_mints, meta_results)
        }

        async def fetch_balance(owner: str, mint: str):
            try:
                ata = get_associated_token_address(
                    Pubkey.from_string(owner),
                    Pubkey.from_string(mint),
                )
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountBalance",
                    "params": [str(ata)],
                }
                async with httpx.AsyncClient() as client:
                    r = await client.post(self.rpc_url, json=payload, timeout=10)
                    result = r.json()
                value = (result.get("result") or {}).get("value")
                if not value:
                    return owner, mint, {"ui_balance": 0.0, "raw_balance": "0", "string_ui_balance": "0"}
                return owner, mint, {
                    "ui_balance":        value.get("uiAmount") or 0.0,
                    "raw_balance":       value.get("amount", "0"),
                    "string_ui_balance": value.get("uiAmountString", "0"),
                }
            except Exception:
                return owner, mint, {"ui_balance": 0.0, "raw_balance": "0", "string_ui_balance": "0"}

        pairs = [(owner, mint) for owner in owner_pubkeys for mint in tokens]
        results = await asyncio.gather(
            *[fetch_balance(owner, mint) for owner, mint in pairs],
            return_exceptions=True,
        )

        output: dict = {}
        for res in results:
            if isinstance(res, Exception):
                continue
            owner, mint, bal = res
            output.setdefault(owner, {})[mint] = {**bal, "metadata": metadata_map.get(mint)}
        return output
    async def fetch_metadata_raw(self, mint_address: str):
        """
        Reads Metaplex on-chain metadata for a token directly from the metadata PDA account.

        Args:
            mint_address (str): Base58 token mint address.

        Returns:
            dict | None: { "mint": str, "name": str, "symbol": str, "uri": str }
                         None if the metadata account does not exist.
        """
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
    async def transfer_token(self, to: str, amount, token_mint:str = None):
        """
        Transfers an SPL token to the given address.
        Automatically creates the recipient's ATA if it does not exist.

        Args:
            to     (str):   Base58 recipient address.
            amount (float): Token amount in token units (not raw lamport-equivalent).

        Returns:
            Transaction | Signature: If build_tx=True returns a Transaction object,
                                     otherwise returns the broadcast transaction signature.

        Raises:
            ValueError: If TOKEN_MINT or KEYPAIR is not set.
        """
        if token_mint:
            self.TOKEN_MINT = token_mint
        if not self.TOKEN_MINT:
            raise ValueError("not set TOKEN_MINT.")
        if not self.KEYPAIR:
            raise ValueError("not set KEYPAIR.")

        sender_pubkey = self.get_pubkey()
        receiver_pubkey = solders.pubkey.Pubkey.from_string(to)
        token_pubkey = solders.pubkey.Pubkey.from_string(self.TOKEN_MINT)

        sender_ata = get_associated_token_address(sender_pubkey, token_pubkey)
        receiver_ata = get_associated_token_address(receiver_pubkey, token_pubkey)

        ixs = []
        res = await self.client.get_account_info(receiver_ata)
        if res.value is None:
            ixs.append(create_associated_token_account(
                payer=sender_pubkey,
                owner=receiver_pubkey,
                mint=token_pubkey,
            ))

        ixs.append(transfer(TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            dest=receiver_ata,
            owner=sender_pubkey,
            amount=amount,
        )))

        blockhash = (await self.client.get_latest_blockhash()).value.blockhash
        msg = Message(ixs, sender_pubkey)
        tx = Transaction([self.KEYPAIR], msg, blockhash)

        if self.build_tx:
            return {"tx": base64.b64encode(bytes(tx)).decode()}

        resp = await self.client.send_transaction(tx, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
        return {"tx": str(resp.value)}


    async def transfer_native(self, to: str, amount: int):
        """
        Transfers native SOL via the System Program.

        Args:
            to     (str): Base58 recipient address.
            amount (int): Amount in lamports (1 SOL = 1_000_000_000 lamports).

        Returns:
            Transaction | Signature: If build_tx=True returns a Transaction object,
                                     otherwise returns the broadcast transaction signature.

        Raises:
            ValueError: If KEYPAIR is not set.
        """
        if not self.KEYPAIR:
            raise ValueError("not set KEYPAIR.")

        sender_pubkey = self.get_pubkey()
        receiver_pubkey = solders.pubkey.Pubkey.from_string(to)
        ixns = [
            ts(tsf(
                from_pubkey=sender_pubkey,
                to_pubkey=receiver_pubkey,
                lamports=amount
            ))
        ]
        msg = Message(ixns, self.get_pubkey())
        latest_blockhash_resp = await self.client.get_latest_blockhash()

        blockhash_str = latest_blockhash_resp.value.blockhash
        tx = Transaction([self.KEYPAIR], msg, blockhash_str)
        if self.build_tx:
            return {"tx": base64.b64encode(bytes(tx)).decode()}
        resp = await self.client.send_transaction(tx)
        return {"tx": str(resp.value)}

    async def close_token_account(
        self,
        mint: str,
        destination: str = None,
        fee_receiver: str = None,
        keypair=None,
    ) -> str:
        """
        Closes a SPL token ATA and sends the recovered rent lamports to destination.
        If fee_receiver is provided, 10% of the rent goes to them and 90% to the owner.

        Args:
            mint         (str):           Token mint address of the ATA to close.
            destination  (str):           Recipient of the rent lamports.
                                          Ignored when fee_receiver is set (rent always
                                          lands on owner first, then gets split).
                                          Defaults to the owner's pubkey (self.KEYPAIR).
            fee_receiver (str):           Optional address that receives 10% of the rent.
                                          Owner keeps the remaining 90%.
            keypair      (str|Keypair):   Account owner. Defaults to self.KEYPAIR.

        Returns:
            str: Transaction signature, or base64-encoded transaction if build_tx=True.

        Raises:
            ValueError: If KEYPAIR is not set.
        """
        kp = self._resolve_keypair(keypair) if keypair else self.KEYPAIR
        if not kp:
            raise ValueError("KEYPAIR is not set.")

        owner = kp.pubkey()
        token_pubkey = solders.pubkey.Pubkey.from_string(mint)
        ata = get_associated_token_address(owner, token_pubkey)

        ixs = []

        if fee_receiver:
            acc_info = await self.client.get_account_info(ata)
            rent_lamports = acc_info.value.lamports if acc_info.value else 0
            fee_lamports = rent_lamports * 10 // 100

            ixs.append(close_account(CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=ata,
                dest=owner,
                owner=owner,
            )))

            if fee_lamports > 0:
                ixs.append(ts(tsf(
                    from_pubkey=owner,
                    to_pubkey=solders.pubkey.Pubkey.from_string(fee_receiver),
                    lamports=fee_lamports,
                )))
        else:
            dest = solders.pubkey.Pubkey.from_string(destination) if destination else owner
            ixs.append(close_account(CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=ata,
                dest=dest,
                owner=owner,
            )))

        blockhash = (await self.client.get_latest_blockhash()).value.blockhash
        msg = Message(ixs, owner)
        tx = Transaction([kp], msg, blockhash)

        if self.build_tx:
            return {"tx": base64.b64encode(bytes(tx)).decode()}

        resp = await self.client.send_transaction(tx, opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed))
        return {"tx": str(resp.value)}

    # ------------------------------------------------------------------ #
    #  Instruction builders  (for composing multi-send transactions)       #
    # ------------------------------------------------------------------ #

    def build_sol_transfer_ix(
        self,
        to: str,
        lamports: int = None,
        from_pubkey=None,
    ) -> list:
        """
        Builds a single native SOL transfer instruction (System Program).
        Does NOT broadcast anything — returns a list so you can extend your
        instruction list and batch multiple transfers into one transaction.

        Accepts two calling styles:

        **Explicit args:**
            build_sol_transfer_ix(to="<addr>", lamports=100000)
            build_sol_transfer_ix(to="<addr>", lamports=100000, from_pubkey=kp.pubkey())

        **Packed string** (comma or dot separated, lamports must be omitted):
            ``"<to>,<lamports>"``          — sender defaults to self.KEYPAIR
            ``"<from>,<to>,<lamports>"``   — explicit sender address
            ``"<to>.<lamports>"``          — dot separator also accepted

        Examples:
            build_sol_transfer_ix("BjxJ...,100000")
            build_sol_transfer_ix("A8tr...,2U4M...,100000")

        Args:
            to          (str):    Base58 recipient address, or a packed string.
            lamports    (int):    Amount in lamports. Omit when using a packed string.
            from_pubkey (Pubkey): Sender pubkey. Defaults to self.KEYPAIR pubkey.

        Returns:
            list[Instruction]: One-element list containing the transfer instruction.

        Raises:
            ValueError: If no sender pubkey is available or the packed string is malformed.
        """
        if lamports is None:
            parts = re.split(r"[,.]", to.strip())
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) == 3:
                from_pubkey = parts[0]
                to = parts[1]
                lamports = int(parts[2])
            elif len(parts) == 2:
                to = parts[0]
                lamports = int(parts[1])
            else:
                raise ValueError(
                    "build_sol_transfer_ix: packed string must be "
                    "'to,lamports' or 'from,to,lamports'"
                )

        sender = from_pubkey or self.get_pubkey()
        if isinstance(sender, str):
            sender = solders.pubkey.Pubkey.from_string(sender)
        receiver = solders.pubkey.Pubkey.from_string(to)
        ix = ts(tsf(from_pubkey=sender, to_pubkey=receiver, lamports=lamports))
        return [ix]

    async def build_token_transfer_ix(
        self,
        to: str,
        amount: int,
        mint: str = None,
        from_pubkey=None,
    ) -> list:
        """
        Builds SPL token transfer instruction(s).
        If the recipient's Associated Token Account (ATA) does not exist,
        a create_associated_token_account instruction is prepended automatically.

        Args:
            to          (str):    Base58 recipient owner address (not their ATA).
            amount      (int):    Raw token amount (decimals already applied).
            mint        (str):    Token mint address. Falls back to self.TOKEN_MINT.
            from_pubkey (Pubkey): Sender pubkey. Defaults to self.KEYPAIR pubkey.

        Returns:
            list[Instruction]: [create_ata_ix (optional), transfer_ix]

        Raises:
            ValueError: If mint is not provided and self.TOKEN_MINT is not set.
        """
        mint_addr = mint or self.TOKEN_MINT
        if not mint_addr:
            raise ValueError("Token mint not provided and TOKEN_MINT is not set.")

        sender = from_pubkey or self.get_pubkey()
        if isinstance(sender, str):
            sender = solders.pubkey.Pubkey.from_string(sender)
        receiver_pubkey = solders.pubkey.Pubkey.from_string(to)
        token_pubkey    = solders.pubkey.Pubkey.from_string(mint_addr)

        sender_ata   = get_associated_token_address(sender, token_pubkey)
        receiver_ata = get_associated_token_address(receiver_pubkey, token_pubkey)

        ixs = []
        res = await self.client.get_account_info(receiver_ata)
        if res.value is None:
            ixs.append(
                create_associated_token_account(
                    payer=sender,
                    owner=receiver_pubkey,
                    mint=token_pubkey,
                )
            )

        ixs.append(
            transfer(
                TransferParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=sender_ata,
                    dest=receiver_ata,
                    owner=sender,
                    amount=amount,
                )
            )
        )
        return ixs

    async def multi_send_sol(self, recipients: list[dict]) -> str:
        """
        Sends native SOL to multiple recipients in a single transaction.
        All transfers are packed into one set of instructions — saves on fees
        compared to N separate transactions.

        Args:
            recipients (list[dict]): [
                { "to": str, "lamports": int },
                ...
            ]
            Maximum ~20 recipients per transaction (Solana tx size limit).

        Returns:
            str: Transaction signature.

        Raises:
            ValueError: If KEYPAIR is not set.

        Example:
            await sol.multi_send_sol([
                {"to": "ABC...", "lamports": 1_000_000},
                {"to": "DEF...", "lamports": 2_000_000},
            ])
        """
        if not self.KEYPAIR:
            raise ValueError("KEYPAIR is not set.")

        ixs = []
        for r in recipients:
            ixs.extend(self.build_sol_transfer_ix(to=r["to"], lamports=r["lamports"]))

        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message(ixs, self.get_pubkey())
        tx  = Transaction([self.KEYPAIR], msg, blockhash)
        resp = await self.client.send_transaction(tx)
        return {"tx": str(resp.value)}

    async def multi_send_token(
        self,
        recipients: list[dict],
        mint: str = None,
    ) -> str:
        """
        Sends SPL tokens to multiple recipients in a single transaction.
        ATA creation instructions are automatically included for recipients
        that don't have an account yet.

        Args:
            recipients (list[dict]): [
                { "to": str, "amount": int },   # amount in raw units
                ...
            ]
            mint (str): Token mint address. Falls back to self.TOKEN_MINT.
            Maximum ~7-10 recipients per transaction depending on ATA creations.

        Returns:
            str: Transaction signature.

        Raises:
            ValueError: If KEYPAIR is not set or mint is missing.

        Example:
            await sol.multi_send_token(
                recipients=[
                    {"to": "ABC...", "amount": 1_000_000},
                    {"to": "DEF...", "amount": 2_000_000},
                ],
                mint="EPjF..."  # USDC mint
            )
        """
        if not self.KEYPAIR:
            raise ValueError("KEYPAIR is not set.")

        ixs = []
        for r in recipients:
            ixs.extend(
                await self.build_token_transfer_ix(
                    to=r["to"],
                    amount=r["amount"],
                    mint=mint,
                )
            )

        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message(ixs, self.get_pubkey())
        tx  = Transaction([self.KEYPAIR], msg, blockhash)
        resp = await self.client.send_transaction(tx, self.KEYPAIR, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
        return {"tx": str(resp.value)}

    # ------------------------------------------------------------------ #
    #  Multi-wallet (multi-signer) sends                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_keypair(keypair) -> solders.keypair.Keypair:
        """
        Resolves a Keypair object from a base58 private key string or a Keypair instance.

        Args:
            keypair (str | Keypair): Base58-encoded private key string or a Keypair object.

        Returns:
            solders.keypair.Keypair

        Raises:
            ValueError: If the type is unsupported or the string is invalid.
        """
        if isinstance(keypair, solders.keypair.Keypair):
            return keypair
        if isinstance(keypair, str):
            return solders.keypair.Keypair.from_base58_string(keypair)
        raise ValueError("keypair must be a base58 string or a Keypair instance.")

    def _get_signers(
        self,
        fee_payer=None,
        extra: list = None,
    ) -> list:
        """
        Assembles the complete signer list for a transaction.

        Order:
          1. fee_payer (or self.KEYPAIR if fee_payer is None) — always first
          2. self.external_signers — persistent co-signers added via add_signer()
          3. extra — any keypairs passed at call time

        Duplicates are silently skipped (comparison by public key).

        Args:
            fee_payer (str | Keypair): Override the fee-paying keypair.
                                       Defaults to self.KEYPAIR.
            extra     (list):          Additional keypairs (str | Keypair) to include.

        Returns:
            list[Keypair]: Deduplicated signer list, fee payer at index 0.

        Raises:
            ValueError: If no fee payer is available (self.KEYPAIR not set and
                        fee_payer not provided).
        """
        payer_kp = self._resolve_keypair(fee_payer) if fee_payer else self.KEYPAIR
        if not payer_kp:
            raise ValueError("KEYPAIR is not set and no fee_payer provided.")

        seen = {str(payer_kp.pubkey())}
        result = [payer_kp]

        for kp in self.external_signers:
            pk = str(kp.pubkey())
            if pk not in seen:
                seen.add(pk)
                result.append(kp)

        for item in (extra or []):
            kp = self._resolve_keypair(item)
            pk = str(kp.pubkey())
            if pk not in seen:
                seen.add(pk)
                result.append(kp)

        return result

    @staticmethod
    def _filter_signers(signers: list, msg: Message) -> list:
        """
        Returns only the keypairs whose public keys appear in the Message's
        required-signer slots (first ``num_required_signatures`` account keys).

        Solana's Transaction::sign panics if a supplied keypair's pubkey is not
        listed as a required signer in the message, so this guard must be applied
        before constructing every Transaction object.

        Args:
            signers (list[Keypair]): Candidate keypair list (fee payer first).
            msg     (Message):       Compiled transaction message.

        Returns:
            list[Keypair]: Filtered list, preserving original order.
        """
        n = msg.header.num_required_signatures
        required = {str(k) for k in msg.account_keys[:n]}
        return [kp for kp in signers if str(kp.pubkey()) in required]

    async def multi_send_sol_from_many(
        self,
        transfers: list[dict],
        fee_payer=None,
    ) -> str:
        """
        Sends native SOL from multiple different wallets in a single transaction.
        Each unique sender keypair is included as a signer so the network
        can verify all debit authorisations.

        Args:
            transfers (list[dict]): [
                {
                    "keypair": str | Keypair,  # sender's private key or Keypair
                    "to":      str,            # Base58 recipient address
                    "lamports": int,           # amount in lamports
                },
                ...
            ]
            fee_payer (str | Keypair): Keypair that pays the transaction fee.
                                       Defaults to the first sender in the list.

        Returns:
            str: Transaction signature.

        Example:
            await sol.multi_send_sol_from_many([
                {"keypair": "4xPr...", "to": "ABC...", "lamports": 1_000_000},
                {"keypair": kp2,       "to": "DEF...", "lamports": 2_000_000},
            ])
        """
        transfer_kps: list = []
        seen_pubkeys: set = set()
        ixs = []

        for t in transfers:
            kp = self._resolve_keypair(t["keypair"])
            pk = str(kp.pubkey())
            if pk not in seen_pubkeys:
                seen_pubkeys.add(pk)
                transfer_kps.append(kp)
            ixs.extend(
                self.build_sol_transfer_ix(
                    to=t["to"],
                    lamports=t["lamports"],
                    from_pubkey=kp.pubkey(),
                )
            )

        default_payer = self._resolve_keypair(fee_payer) if fee_payer else transfer_kps[0]
        all_signers = self._get_signers(fee_payer=default_payer, extra=transfer_kps)

        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message(ixs, all_signers[0].pubkey())
        tx  = Transaction(self._filter_signers(all_signers, msg), msg, blockhash)
        resp = await self.client.send_transaction(tx)
        return {"tx": str(resp.value)}

    async def multi_send_token_from_many(
        self,
        transfers: list[dict],
        mint: str = None,
        fee_payer=None,
    ) -> str:
        """
        Sends SPL tokens from multiple different wallets in a single transaction.
        ATA creation instructions are prepended automatically for recipients
        that don't have an account yet (paid by the fee payer).

        Args:
            transfers (list[dict]): [
                {
                    "keypair": str | Keypair,  # sender's private key or Keypair
                    "to":      str,            # Base58 recipient owner address
                    "amount":  int,            # raw token amount (decimals applied)
                },
                ...
            ]
            mint      (str):           Token mint address. Falls back to self.TOKEN_MINT.
            fee_payer (str | Keypair): Keypair that pays the transaction fee and ATA creations.
                                       Defaults to the first sender.

        Returns:
            str: Transaction signature.

        Example:
            await sol.multi_send_token_from_many(
                transfers=[
                    {"keypair": "4xPr...", "to": "ABC...", "amount": 1_000_000},
                    {"keypair": kp2,       "to": "DEF...", "amount": 2_000_000},
                ],
                mint="EPjF..."  # USDC
            )
        """
        transfer_kps: list = []
        seen_pubkeys: set = set()
        ixs = []

        for t in transfers:
            kp = self._resolve_keypair(t["keypair"])
            pk = str(kp.pubkey())
            if pk not in seen_pubkeys:
                seen_pubkeys.add(pk)
                transfer_kps.append(kp)
            ixs.extend(
                await self.build_token_transfer_ix(
                    to=t["to"],
                    amount=t["amount"],
                    mint=mint,
                    from_pubkey=kp.pubkey(),
                )
            )

        default_payer = self._resolve_keypair(fee_payer) if fee_payer else transfer_kps[0]
        all_signers = self._get_signers(fee_payer=default_payer, extra=transfer_kps)

        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message(ixs, all_signers[0].pubkey())
        tx  = Transaction(self._filter_signers(all_signers, msg), msg, blockhash)
        resp = await self.client.send_transaction(tx, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
        return {"tx": str(resp.value)}

    async def build_transaction(self, data: dict):
        """
        Builds an unsigned transaction for a native SOL transfer.

        Args:
            data (dict): {
                "_from":   str,   # Base58 sender address
                "_to":     str,   # Base58 recipient address
                "_amount": float, # Amount in SOL
                "_token":  str,   # Mint address or __SOL__NATIVE__ for native SOL
            }

        Returns:
            dict: {
                "tx":               str,  # HEX-encoded serialised transaction
                "recent_blockhash": str,  # blockhash string used in the transaction
            }
        """
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
    async def send_instructions(
        self,
        ixs: list,
        signers: list = None,
        fee_payer=None,
    ) -> str:
        """
        Builds and sends a transaction from a list of instructions.
        Accepts both flat lists and nested lists (auto-flattened), so you can
        safely use either append or extend when collecting instructions.

        Transaction size limit: ~1232 bytes per transaction.
          - SOL transfer instruction:   ~50 bytes  → up to ~20 per tx
          - Token transfer instruction: ~100 bytes → up to ~10 per tx
          - ATA creation instruction:   ~150 bytes → counts against the same budget
          Mixed batches: sum all instruction sizes and stay under 1232 bytes.

        Args:
            ixs       (list):          Instruction list — flat [ix, ix] or nested [[ix], [ix]].
            signers   (list):          Extra keypairs that must co-sign the transaction
                                       (str base58 or Keypair). self.KEYPAIR is always
                                       included automatically as fee payer.
            fee_payer (str|Keypair):   Override the fee-paying keypair. Defaults to self.KEYPAIR.

        Returns:
            str: Transaction signature.

        Raises:
            ValueError: If KEYPAIR is not set, no fee_payer is provided,
                        and external_signers is empty.

        Example:
            ixs = []
            for r in recipients:
                ixs.append(await sol.build_sol_transfer_ix(r["to"], r["lamports"]))
            sig = await sol.send_instructions(ixs)

            # multi-wallet
            sig = await sol.send_instructions(ixs, signers=[kp2, kp3])
        """
        all_signers = self._get_signers(fee_payer=fee_payer, extra=signers)
        payer_kp = all_signers[0]

        # flatten [[ix, ix], [ix]] → [ix, ix, ix]
        flat_ixs = []
        for item in ixs:
            if isinstance(item, list):
                flat_ixs.extend(item)
            else:
                flat_ixs.append(item)

        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash

        msg = Message(flat_ixs, payer_kp.pubkey())
        tx  = Transaction(self._filter_signers(all_signers, msg), msg, blockhash)
        resp = await self.client.send_transaction(
            tx,
            opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed),
        )
        return {"tx": str(resp.value)}

    async def _send_tx(self, tx, key: str = None):
        """
        Signs and broadcasts a transaction. Accepts:
          - Transaction object (legacy, with .message/.recent_blockhash)
          - VersionedTransaction object (with .message but no .recent_blockhash)
          - bytes / list[int] — raw serialized transaction
          - str — base64-encoded raw transaction
        """
        import base64 as _b64
        from solana.rpc.types import TxOpts
        from solana.rpc.commitment import Confirmed
        tx_hash = None
        try:

            if key:
                from solders.keypair import Keypair
                signer = Keypair.from_base58_string(key)
            else:
                signer = self.KEYPAIR

            if not signer:
                raise ValueError("No keypair provided for signing")

            # ── raw bytes / base64 / list → sign as VersionedTransaction ──
            if isinstance(tx, (bytes, list, tuple, str)):
                from solders.transaction import VersionedTransaction
                if isinstance(tx, str):
                    s = tx.strip()
                    if re.fullmatch(r'[0-9a-fA-F]+', s):
                        raw = bytes.fromhex(s)
                    else:
                        try:
                            raw = _b64.b64decode(s, validate=True)
                        except Exception:
                            raise ValueError(
                                f"tx string is neither valid hex nor base64. "
                                f"Serialize with bytes(tx).hex() or base64.b64encode(bytes(tx)). "
                                f"Preview: {s[:80]!r}"
                            )
                elif isinstance(tx, (list, tuple)):
                    raw = bytes(tx)
                else:
                    raw = tx
                vtx = VersionedTransaction.from_bytes(raw)
                signed = VersionedTransaction(vtx.message, [signer])
                opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
                resp = await self.client.send_raw_transaction(bytes(signed), opts=opts)
                tx_hash = str(resp.value)

            # ── legacy Transaction object ──
            elif hasattr(tx, 'message') and hasattr(tx, 'recent_blockhash'):
                from solders.transaction import Transaction
                final_tx = Transaction([signer], tx.message, tx.recent_blockhash)
                resp = await self.client.send_transaction(final_tx)
                tx_hash = str(resp.value)

            # ── VersionedTransaction object ──
            elif hasattr(tx, 'message'):
                from solders.transaction import VersionedTransaction
                signed = VersionedTransaction(tx.message, [signer])
                opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
                resp = await self.client.send_raw_transaction(bytes(signed), opts=opts)
                tx_hash = str(resp.value)

            else:
                raise ValueError(f"Unsupported tx type: {type(tx)}")

            confirm = await self.confirm_tx(signature=tx_hash)
            if not confirm["confirmed"]:
                return {"error": confirm["error"], "status": confirm["status"]}
            return {"tx":tx_hash, "fee_info": await self._parse_receipt_gas(tx_hash)}

        except Exception as e:
            return e
    async def confirm_tx(
        self,
        signature: str,
        commitment: str = "confirmed",
        timeout: float = 60.0,
        poll_interval: float = 2.0,
    ) -> dict:
        """
        Polls getSignatureStatuses until the transaction reaches the requested
        commitment level, fails on-chain, or the timeout expires.

        Args:
            signature     (str):   Base58 transaction signature.
            commitment    (str):   Target commitment: "processed" | "confirmed" | "finalized".
            timeout       (float): Max seconds to wait before giving up.
            poll_interval (float): Seconds between RPC polls.

        Returns:
            dict: {
                "signature":   str,
                "confirmed":   bool,          # True if reached target commitment without error
                "status":      str,           # "confirmed" | "finalized" | "processed"
                                              # | "failed" | "timeout" | "not_found"
                "error":       dict | None,   # on-chain error object, or None
                "slot":        int | None,
                "confirmations": int | None,  # None once finalized
            }
        """
        COMMITMENT_ORDER = {"processed": 0, "confirmed": 1, "finalized": 2}
        target_level = COMMITMENT_ORDER.get(commitment, 1)

        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[signature], {"searchTransactionHistory": True}],
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(self.rpc_url, json=payload, timeout=15)
                data = r.json()

            statuses = (data.get("result") or {}).get("value") or []
            st = statuses[0] if statuses else None

            if st is None:
                await asyncio.sleep(poll_interval)
                continue

            err = st.get("err")
            conf_status = st.get("confirmationStatus") or ""  # processed/confirmed/finalized
            current_level = COMMITMENT_ORDER.get(conf_status, -1)

            base = {
                "signature":     signature,
                "error":         err,
                "slot":          st.get("slot"),
                "confirmations": st.get("confirmations"),
            }

            if err:
                return {**base, "confirmed": False, "status": "failed"}

            if current_level >= target_level:
                return {**base, "confirmed": True, "status": conf_status}

            await asyncio.sleep(poll_interval)

        return {
            "signature":     signature,
            "confirmed":     False,
            "status":        "timeout",
            "error":         None,
            "slot":          None,
            "confirmations": None,
        }

    async def _parse_receipt_gas(self, signature: str) -> dict:
        """
        Fetches fee and compute unit usage for a confirmed transaction.

        Args:
            signature (str): Base58 transaction signature.

        Returns:
            dict: {
                "fee_lamports":           int,
                "fee_sol":                float,
                "compute_units_consumed": int | None,   # None on very old transactions
                "slot":                   int | None,
                "status":                 "success" | "failed" | "not_found",
            }
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "json",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(self.rpc_url, json=payload, timeout=15)
            data = r.json()

        tx = data.get("result")
        if not tx:
            return {"status": "not_found", "signature": signature}

        meta = tx.get("meta") or {}
        fee  = meta.get("fee", 0)
        err  = meta.get("err")

        return {
            "fee":           fee,
            "fee_ui":                fee / LAMPORTS_PER_SOL,
            "compute_units_consumed": meta.get("computeUnitsConsumed"),
            "slot":                   tx.get("slot"),
            "status":                 "failed" if err else "success",
        }

    async def tx_to_human_view(self, signature: str) -> dict:
        """
        Converts a transaction signature into a human-readable summary dict.

        Args:
            signature (str): Base58 transaction signature.

        Returns:
            dict: {
                "action":   str,         # "SOL Transfer" | "Token Transfer" | "Swap" | "Unknown"
                "from":     str | None,  # sender address
                "to":       str | None,  # recipient (None for swaps / multi-party)
                "amount":   float,       # primary amount in human units
                "symbol":   str,         # "SOL" or token mint abbreviated
                "fee_sol":  float,
                "slot":     int | None,
                "status":   str,         # "success" | "failed"
                "program":  str | None,  # first non-system program invoked
                "summary":  str,         # one-line human description
            }
        """
        parsed = await self._parse_transaction(signature)

        if "error" in parsed:
            return {"status": "not_found", "signature": signature}

        tx_type = parsed.get("tx_type", "unknown")

        result = {
            "action":  "Unknown",
            "from":    None,
            "to":      None,
            "amount":  0,
            "symbol":  "SOL",
            "fee_sol": float(parsed.get("fee_sol", 0)),
            "slot":    parsed.get("slot"),
            "status":  parsed.get("status", "unknown"),
            "program": None,
            "summary": parsed.get("summary", ""),
        }

        _skip = {"system", "spl-token", "spl-associated-token-account", "compute_budget"}
        for p in parsed.get("programs", []):
            prog = (p.get("program") or "").lower()
            if prog and prog not in _skip:
                result["program"] = p["program"]
                break
        if result["program"] is None and parsed.get("programs"):
            result["program"] = parsed["programs"][0].get("program")

        if tx_type == "sol_transfer":
            out = [t for t in parsed["transfers"] if t["direction"] == "out"]
            inn = [t for t in parsed["transfers"] if t["direction"] == "in"]
            result["action"] = "SOL Transfer"
            result["from"]   = out[0]["account"] if out else None
            result["to"]     = inn[0]["account"] if inn else None
            result["amount"] = abs(out[0]["change_sol"]) if out else 0
            result["symbol"] = "SOL"

        elif tx_type == "token_transfer":
            out = [t for t in parsed["token_transfers"] if t["direction"] == "out"]
            inn = [t for t in parsed["token_transfers"] if t["direction"] == "in"]
            result["action"] = "Token Transfer"
            result["from"]   = out[0]["owner"] if out else None
            result["to"]     = inn[0]["owner"] if inn else None
            result["amount"] = abs(out[0]["change"]) if out else 0
            result["symbol"] = (out[0]["mint"] or "")[:8] + "…" if out else "?"

        elif tx_type == "swap":
            out_t = [t for t in parsed["token_transfers"] if t["direction"] == "out"]
            inn_t = [t for t in parsed["token_transfers"] if t["direction"] == "in"]
            result["action"] = "Swap"
            result["from"]   = out_t[0]["owner"] if out_t else None
            result["to"]     = None
            result["amount"] = abs(out_t[0]["change"]) if out_t else 0
            result["symbol"] = (
                (out_t[0]["mint"] or "")[:8] + "… → " + (inn_t[0]["mint"] or "")[:8] + "…"
                if out_t and inn_t else "?"
            )

        return result

    def parse_raw_tx(self, tx) -> dict:
        """
        Parses a raw serialized transaction without sending it to the network.
        Accepts the same formats as _send_tx:
          - str  — hex string or base64 string
          - bytes
          - list[int] / tuple[int]
          - Transaction / VersionedTransaction object

        Returns:
            dict: {
                "tx_type":          str,         # "SOL Transfer" | "Token Operation" | "Jupiter Swap" | ...
                "fee_payer":        str | None,
                "signers":          list[str],   # required signers (first N account keys)
                "num_accounts":     int,
                "accounts":         list[str],   # all static account keys in the message
                "alt_accounts":     list[str],   # address lookup table accounts (v0 only)
                "num_instructions": int,
                "instructions": list[{
                    "program_id":   str,
                    "program_name": str,         # known name or first 8 chars of ID
                    "accounts":     list[str],   # accounts referenced by this ix
                    "type":         str | None,  # decoded ix type if recognizable
                    "data_hex":     str,         # raw ix data as hex
                }],
            }
        """
        import base64 as _b64
        from solders.transaction import VersionedTransaction

        KNOWN_PROGRAMS = {
            "11111111111111111111111111111111":             "System Program",
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "Token Program",
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJe1brs": "Associated Token Program",
            "ComputeBudget111111111111111111111111111111":  "Compute Budget",
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM v4",
            "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "Raydium (legacy)",
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc":  "Orca Whirlpool",
        }
        SYSTEM_IX  = {0: "CreateAccount", 2: "Transfer", 3: "CreateAccountWithSeed", 9: "Assign"}
        TOKEN_IX   = {3: "Transfer", 4: "Approve", 7: "MintTo", 8: "Burn",
                      9: "CloseAccount", 12: "TransferChecked", 14: "ApproveChecked"}
        COMPUTE_IX = {0: "SetComputeUnitLimit", 3: "SetComputeUnitPrice"}

        # ── normalise input to bytes ──────────────────────────────────────────
        if isinstance(tx, str):
            s = tx.strip()
            if re.fullmatch(r'[0-9a-fA-F]+', s):
                raw = bytes.fromhex(s)
            else:
                try:
                    raw = _b64.b64decode(s, validate=True)
                except Exception:
                    raise ValueError("tx string is neither valid hex nor base64")
        elif isinstance(tx, (list, tuple)):
            raw = bytes(tx)
        elif isinstance(tx, bytes):
            raw = tx
        elif hasattr(tx, 'message'):
            raw = bytes(tx)
        else:
            raise ValueError(f"Unsupported tx type: {type(tx)}")

        vtx = VersionedTransaction.from_bytes(raw)
        msg = vtx.message
        account_keys = [str(k) for k in msg.account_keys]
        num_sigs = msg.header.num_required_signatures

        # v0 address lookup tables
        alt_accounts = []
        for alt in getattr(msg, 'address_table_lookups', None) or []:
            alt_accounts.append(str(alt.account_key))

        # ── decode each instruction ───────────────────────────────────────────
        parsed_ixs = []
        for ix in msg.instructions:
            prog_idx = ix.program_id_index
            prog_id  = account_keys[prog_idx] if prog_idx < len(account_keys) else "unknown"
            prog_name = KNOWN_PROGRAMS.get(prog_id, prog_id[:8] + "…")

            ix_accounts = [
                account_keys[i] for i in ix.accounts if i < len(account_keys)
            ]
            data     = bytes(ix.data)
            data_hex = data.hex()
            ix_type  = None

            if prog_id == "11111111111111111111111111111111" and len(data) >= 4:
                code = int.from_bytes(data[:4], "little")
                ix_type = SYSTEM_IX.get(code, f"unknown({code})")
                if code == 2 and len(data) == 12:
                    lamports = int.from_bytes(data[4:12], "little")
                    ix_type  = f"Transfer {lamports / LAMPORTS_PER_SOL:.9f} SOL"

            elif prog_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" and data:
                code = data[0]
                ix_type = TOKEN_IX.get(code, f"unknown({code})")

            elif prog_id == "ComputeBudget111111111111111111111111111111" and data:
                code = data[0]
                ix_type = COMPUTE_IX.get(code, f"unknown({code})")
                if code == 0 and len(data) == 5:
                    units   = int.from_bytes(data[1:5], "little")
                    ix_type = f"SetComputeUnitLimit {units:,}"
                elif code == 3 and len(data) == 9:
                    price   = int.from_bytes(data[1:9], "little")
                    ix_type = f"SetComputeUnitPrice {price} µ-lamports"

            parsed_ixs.append({
                "program_id":   prog_id,
                "program_name": prog_name,
                "accounts":     ix_accounts,
                "type":         ix_type,
                "data_hex":     data_hex,
            })

        # ── detect overall tx type from programs used ─────────────────────────
        prog_ids = {ix["program_id"] for ix in parsed_ixs}
        if "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4" in prog_ids:
            tx_type = "Jupiter Swap"
        elif "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8" in prog_ids:
            tx_type = "Raydium Swap"
        elif "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc" in prog_ids:
            tx_type = "Orca Swap"
        elif prog_ids <= {"11111111111111111111111111111111",
                          "ComputeBudget111111111111111111111111111111"}:
            tx_type = "SOL Transfer"
        elif "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" in prog_ids:
            tx_type = "Token Operation"
        else:
            tx_type = "Unknown"

        return {
            "tx_type":          tx_type,
            "fee_payer":        account_keys[0] if account_keys else None,
            "signers":          account_keys[:num_sigs],
            "num_accounts":     len(account_keys),
            "accounts":         account_keys,
            "alt_accounts":     alt_accounts,
            "num_instructions": len(parsed_ixs),
            "instructions":     parsed_ixs,
        }

    async def _parse_transaction(self, signature: str, retries: int = 5, retry_delay: float = 2.0, commitment: str = "finalized") -> dict:
        """
        Fetches and parses a transaction by signature using RPC getTransaction.

        Args:
            signature   (str):   Base58 transaction signature.
            retries     (int):   Number of RPC polling attempts (transaction may not be finalised yet).
            retry_delay (float): Delay in seconds between attempts.

        Returns:
            dict: {
                "signature":       str,
                "status":          "success" | "failed",
                "error":           dict | None,       # error object from meta.err
                "slot":            int,
                "timestamp":       int | None,        # block unix timestamp
                "fee_lamports":    int,
                "fee_sol":         float,
                "transfers": list[{                   # SOL balance changes per account
                    "account":         str,
                    "change_lamports": int,
                    "change_sol":      float,
                    "direction":       "in" | "out",
                }],
                "token_transfers": list[{             # SPL token balance changes
                    "account":   str,
                    "mint":      str,
                    "owner":     str,
                    "change":    float,
                    "direction": "in" | "out",
                    "decimals":  int,
                }],
                "programs": list[{                    # programs invoked in the transaction
                    "program": str,
                    "type":    str | None,
                    "info":    dict | None,
                }],
                "tx_type": "sol_transfer" | "token_transfer" | "swap" | "unknown",
                "summary": str,                       # human-readable transaction description
            }
            On error: {"error": "Transaction not found", "signature": str}
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": commitment,
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

        account_keys = [
            acc.get("pubkey") if isinstance(acc, dict) else acc
            for acc in message.get("accountKeys", [])
        ]
        from decimal import Decimal
        result = {
            "signature":   signature,
            "status":      "failed" if err else "success",
            "error":       err,
            "slot":        tx.get("slot"),
            "timestamp":   block_time,
            "fee_lamports": fee,
            "fee_sol":     str(Decimal(fee) / Decimal(LAMPORTS_PER_SOL)),
            "transfers":   [],
            "token_transfers": [],
            "programs":    [],
            "tx_type":     "unknown",
        }

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

        tx_type = result["tx_type"]
        status  = result["status"]
        fee_sol = result["fee_sol"]  # str like "0.000005"

        if tx_type == "sol_transfer":
            out = [t for t in result["transfers"] if t["direction"] == "out"]
            inn = [t for t in result["transfers"] if t["direction"] == "in"]
            sender   = out[0]["account"][:8] + "…" if out else "?"
            receiver = inn[0]["account"][:8] + "…" if inn else "?"
            amount   = abs(out[0]["change_sol"]) if out else 0
            summary  = (
                f"SOL transfer {amount:.6f} SOL "
                f"from {sender} → {receiver} | "
                f"status: {status} | fee: {fee_sol} SOL"
            )
        elif tx_type == "token_transfer":
            out = [t for t in result["token_transfers"] if t["direction"] == "out"]
            inn = [t for t in result["token_transfers"] if t["direction"] == "in"]
            sender   = out[0]["owner"][:8] + "…" if out else "?"
            receiver = inn[0]["owner"][:8] + "…" if inn else "?"
            amount   = abs(out[0]["change"]) if out else 0
            mint     = (out[0]["mint"] or "")[:8] + "…" if out else "?"
            summary  = (
                f"Token transfer {amount} [{mint}] "
                f"from {sender} → {receiver} | "
                f"status: {status} | fee: {fee_sol} SOL"
            )
        elif tx_type == "swap":
            mints = list({t["mint"] for t in result["token_transfers"] if t.get("mint")})
            mints_str = " ↔ ".join(m[:8] + "…" for m in mints[:2]) if mints else "unknown tokens"
            summary = (
                f"Swap ({mints_str}) | "
                f"status: {status} | fee: {fee_sol} SOL"
            )
        else:
            prog_names = ", ".join(filter(None, programs[:3])) or "unknown"
            summary = (
                f"Transaction via [{prog_names}] | "
                f"status: {status} | fee: {fee_sol} SOL"
            )

        result["summary"] = summary
        return result

    async def monitor(
        self,
        callback,
        addresses: list ["all"],
        ws_url: str = __SOL__WS__,
        commitment: str = "finalized",
        reconnect_delay: float = 3.0,
        parsed: bool = False,
        batch_size: int = 10,
    ):
        """
        Monitors the Solana blockchain via WebSocket for incoming transactions.

        Args:
            callback        (async callable): Always called with the raw logs value dict.
                                              If parsed=True, also called with {"parsed": {sig: tx_dict}}
                                              once batch_size signatures have accumulated.
            addresses       (list[str]):      Addresses to filter by. Empty list = subscribe to all.
            ws_url          (str):            WebSocket endpoint or alias "mainnet" / "devnet".
            commitment      (str):            "finalized" | "confirmed" | "processed".
            reconnect_delay (float):          Seconds to wait before reconnecting after a drop.
            parsed          (bool):           If True, signatures are batched and parsed via _parse_transaction.
            batch_size      (int):            Number of signatures to accumulate before parsing the batch.
        """
        import websockets
        import json as _json
        if ws_url == "mainnet":
            ws_url = __SOL__WS__
        elif ws_url == "devnet":
            ws_url = __SOL__WS__DEVNET__


        queue: list[str] = []
        sub_map: dict[int, str] = {}  # subscription id → address

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
                except Exception:
                    pass

        while True:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=30,
                ) as ws:
                    if addresses:
                        for i, addr in enumerate(addresses, start=1):
                            msg = {
                                "jsonrpc": "2.0",
                                "id": i,
                                "method": "logsSubscribe",
                                "params": [
                                    {"mentions": [addr]},
                                    {"commitment": commitment},
                                ],
                            }
                            await ws.send(_json.dumps(msg))
                        # read subscription confirmations and map sub_id → address
                        for addr in addresses:
                            resp = _json.loads(await ws.recv())
                            sub_id = resp.get("result")
                            req_id = resp.get("id")
                            if sub_id and req_id:
                                sub_map[sub_id] = addresses[req_id - 1]
                    else:
                        await ws.send(_json.dumps({
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "logsSubscribe",
                            "params": ["all", {"commitment": commitment}],
                        }))
                        await ws.recv()  # skip confirmation

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

                        # attach triggering address if known
                        sub_id = params.get("subscription")
                        if sub_id and sub_id in sub_map:
                            value["address"] = sub_map[sub_id]

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

    async def get_transactions(self, limit: int = 10, before: str = None) -> list[dict]:
        """
        Returns the most recent transactions for the wallet as parsed dicts.

        Args:
            limit  (int): Number of transactions to fetch (max 1000, default 10).
            before (str): Signature to paginate from — returns only transactions before it.

        Returns:
            list[dict]: List of _parse_transaction results for each signature.
                        Failed individual parses are represented as {"error": str}.
        """
        # fetch signatures
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

        import asyncio
        tasks = [self._parse_transaction(sig) for sig in signatures]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]

