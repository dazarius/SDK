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
from OrbisPaySDK.const import __SOL__NATIVE__, WRAPED_SOL, __SOL__WS__, __SOL__WS__DEVNET__, __SOL__EXPLORERS__
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

    def get_pubkey(self, returnString: Optional[bool] = None):
        """
        Returns the public key derived from the current keypair.

        Args:
            returnString (bool): If True, returns a Base58 string; otherwise returns a Pubkey object.

        Returns:
            str | Pubkey: The public key.

        Raises:
            ValueError: If no keypair has been set.
        """
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
        (Not implemented) Fetch balances for specific tokens across multiple wallets.

        Args:
            data (dict): {
                "owner_pubkeys": list[str],  # list of owner addresses
                "tokens":        list[str],  # list of token mint addresses
            }
        """
        owner_pubkey:list = data.get("owner_pubkeys")
        tokens:list = data.get("tokens")
        if not owner_pubkey or not tokens:
            print("No owner pubkey or token list provided, using the wallet's pubkey.")
        for owner in owner_pubkey:
            pass
        pass
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
    async def transfer_token(self, to: str, amount: float):
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

        params = TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            dest=receiver_ata,
            owner=sender_pubkey,
            amount=amount
        )

        tx.add(transfer(params))
        if self.build_tx:
            return tx

        resp = await self.client.send_transaction(tx, self.KEYPAIR, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
        return resp.value


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
            return tx
        resp =  await self.client.send_transaction(tx)
        return resp.value

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
        return str(resp.value)

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
        return str(resp.value)

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
        return str(resp.value)

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
        return str(resp.value)

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
        return str(resp.value)

    async def _send_tx(self, tx, key: str = None):
        """
        Signs and broadcasts a pre-built transaction. Equivalent of EVM sign_and_send.

        Args:
            tx  (Transaction): Transaction object with .message and .recent_blockhash fields.
            key (str):         Base58 private key for signing. Falls back to self.KEYPAIR if omitted.

        Returns:
            dict | False: On success — { "tx": str (signature), "meta": { "symbol", "status", "signature" } }.
                          On error or unconfirmed transaction — False.
        """
        try:
            # resolve signer keypair
            if key:
                from solders.keypair import Keypair
                signer = Keypair.from_base58_string(key)
            else:
                signer = self.KEYPAIR

            if not signer:
                raise ValueError("No keypair provided for signing")

            # re-sign the transaction with the resolved keypair
            if hasattr(tx, 'message'):
                from solders.transaction import Transaction
                final_tx = Transaction([signer], tx.message, tx.recent_blockhash)
            else:
                raise ValueError("tx must be a Transaction object with message and blockhash")

            resp = await self.client.send_transaction(final_tx)
            tx_hash = str(resp.value)

            confirm = await self.client.confirm_transaction(resp.value)

            if not confirm.value:
                return False

            return {
                "tx": tx_hash,
                "meta": {
                    "symbol": "SOL",
                    "status": "Success",
                    "signature": tx_hash
                }
            }

        except Exception:
            return False
    async def _parse_transaction(self, signature: str, retries: int = 5, retry_delay: float = 2.0) -> dict:
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
        fee_sol = result["fee_sol"]

        if tx_type == "sol_transfer":
            out = [t for t in result["transfers"] if t["direction"] == "out"]
            inn = [t for t in result["transfers"] if t["direction"] == "in"]
            sender   = out[0]["account"][:8] + "…" if out else "?"
            receiver = inn[0]["account"][:8] + "…" if inn else "?"
            amount   = abs(out[0]["change_sol"]) if out else 0
            summary  = (
                f"SOL transfer {amount:.6f} SOL "
                f"from {sender} → {receiver} | "
                f"status: {status} | fee: {fee_sol:.6f} SOL"
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
                f"status: {status} | fee: {fee_sol:.6f} SOL"
            )
        elif tx_type == "swap":
            mints = list({t["mint"] for t in result["token_transfers"] if t.get("mint")})
            mints_str = " ↔ ".join(m[:8] + "…" for m in mints[:2]) if mints else "unknown tokens"
            summary = (
                f"Swap ({mints_str}) | "
                f"status: {status} | fee: {fee_sol:.6f} SOL"
            )
        else:
            prog_names = ", ".join(filter(None, programs[:3])) or "unknown"
            summary = (
                f"Transaction via [{prog_names}] | "
                f"status: {status} | fee: {fee_sol:.6f} SOL"
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
async def test():
    s = SOL(
        rpc_url="https://api.devnet.solana.com",
        KEYPAIR="t14ypHnjBg6cJsJt1cCYiSBsnijVwrUToGFz5bGSDp6mWrME4FGNgdWV8qTZi5NbvsMPJRZUwzAPJsiBTeHmJq1"
    )
    s.add_signer("58UYMN6bth7C6NkZp97jPVStv4XEDovnk6BF2bYQynSL5LoFRDQENByhNBs3yMNCUPv1QHxEb68UMpuUMRFYLsUB")

    address_list = ["2U4MLeazpNbvTjrBz9rRgpbFcGn3HN37GuoijKnqc9G2", "BjxJeFZJ1HApM894w4zAdLJKhFUdAQSPKwSZFLEpdJuR", "EMkhZaTAYuDvaXeKpdMAX9qM3b4Y3AZn9QcLqULmohUM"]
    _instructions = []
    for address in address_list:
        inxt_transfer_sol = s.build_sol_transfer_ix(
            to=address,
            lamports=int(0.1 * LAMPORTS_PER_SOL),
            from_pubkey="25jrwTsXY94FtJvsnDpfH8vTnDHHvNzwRGJqX6wKnEJ3"
        )
        _instructions.append(inxt_transfer_sol)
        inxt_transfer_token = await s.build_token_transfer_ix(
            to=address,
            amount=int(10 * (10 ** 6)),  # 10 USDC with 6 decimals
            mint="Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr",  # USDC mint
        )
        _instructions.append(inxt_transfer_token)
    tx = await s.send_instructions(_instructions)
    print(tx)
if __name__ == "__main__":
    asyncio.run(test())