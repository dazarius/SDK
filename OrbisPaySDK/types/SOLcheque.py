
import hashlib
import struct
import solders
import solders.keypair
import solders.pubkey
import spl.token.constants as spl_constants
from solders.instruction import Instruction, AccountMeta
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from spl.token.instructions import get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from OrbisPaySDK.const import PROGRAM_ID

SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _disc(name: str) -> bytes:
    """Anchor instruction discriminator: sha256('global:<name>')[:8]."""
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]


def _cid(cheque_id) -> bytes:
    """Normalise cheque_id to exactly 32 bytes (zero-padded)."""
    if isinstance(cheque_id, bytes):
        return cheque_id[:32].ljust(32, b"\x00")
    if isinstance(cheque_id, str):
        b = cheque_id.encode()
        return b[:32].ljust(32, b"\x00")
    raise ValueError("cheque_id must be bytes or str")


# ── Main class ────────────────────────────────────────────────────────────────

class SOLCheque:
    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        key:str=None,
        program_id = PROGRAM_ID,
    ):
        """
        Client for the OrbisCheques on-chain program (Anchor).

        Args:
            rpc_url    (str): Solana RPC endpoint.
            key        (str): Base58-encoded private key for signing.
            program_id (str): Override the default program ID.
        """
        self.rpc_url      = rpc_url
        self.provider     = Client(rpc_url)
        self.async_client = AsyncClient(rpc_url)
        self.key          = key
        self.PROGRAM_ID   = program_id 
        if key:
            self.set_key(key)

    def set_key(self, key) -> None:
        """
        Set the signing keypair.

        Args:
            key (str | Keypair): Base58 private key string or Keypair object.
        """
        if isinstance(key, str):
            self.key = solders.keypair.Keypair.from_base58_string(key)
        elif isinstance(key, solders.keypair.Keypair):
            self.key = key
        else:
            raise ValueError("key must be a base58 string or Keypair")

    def set_params(self, rpc_url: str = None, key=None) -> None:
        """
        Update RPC endpoint and/or keypair at runtime.

        Args:
            rpc_url (str): New RPC endpoint.
            key     (str | Keypair): New signing keypair.
        """
        if rpc_url:
            self.rpc_url      = rpc_url
            self.provider     = Client(rpc_url)
            self.async_client = AsyncClient(rpc_url)
        if key:
            self.set_key(key)

    # ── PDA derivation ────────────────────────────────────────────────────────

    def config_pda(self):
        """Returns (Pubkey, bump) for the global Config PDA (seeds: ['config'])."""
        return Pubkey.find_program_address([b"config"], self.PROGRAM_ID)

    def native_cheque_pda(self, cheque_id):
        """Returns (Pubkey, bump) for a NativeCheque PDA (seeds: ['native_cheque', cheque_id])."""
        return Pubkey.find_program_address([b"native_cheque", _cid(cheque_id)], self.PROGRAM_ID)

    def token_cheque_pda(self, cheque_id):
        """Returns (Pubkey, bump) for a TokenCheque PDA (seeds: ['token_cheque', cheque_id])."""
        return Pubkey.find_program_address([b"token_cheque", _cid(cheque_id)], self.PROGRAM_ID)

    def swap_cheque_pda(self, cheque_id):
        """Returns (Pubkey, bump) for a SwapCheque PDA (seeds: ['swap_cheque', cheque_id])."""
        return Pubkey.find_program_address([b"swap_cheque", _cid(cheque_id)], self.PROGRAM_ID)

    # ── On-chain data parsing ─────────────────────────────────────────────────

    def get_config(self) -> dict:
        """
        Read and decode the global Config PDA.

        Returns:
            dict: {
                "pda":            str,
                "owner":          str,
                "treasury":       str,
                "bps":            int,   # default fee in basis points
                "collected_fees": int,   # accumulated SOL fees in lamports
                "is_active":      bool,
                "bump":           int,
            }
        """
        config_pda, _ = self.config_pda()
        resp = self.provider.get_account_info(config_pda)
        if resp.value is None:
            return None
        raw = bytes(resp.value.data)[8:]  # skip 8-byte Anchor discriminator
        return {
            "pda":            str(config_pda),
            "owner":          str(Pubkey.from_bytes(raw[0:32])),
            "treasury":       str(Pubkey.from_bytes(raw[32:64])),
            "bps":            struct.unpack_from("<Q", raw, 64)[0],
            "collected_fees": struct.unpack_from("<Q", raw, 72)[0],
            "is_active":      bool(raw[80]),
            "bump":           raw[81],
        }

    def parse_native_cheque(self, cheque_id) -> dict:
        """
        Read and decode a NativeCheque PDA.

        NativeCheque layout (after 8-byte discriminator):
          creator (32) | cheque_id (32) | amount_per_user (u64) |
          recipients (Vec<Pubkey>) | claimed (Vec<bool>) | bump (u8)

        Returns:
            dict: {
                "pda":             str,
                "creator":         str,
                "cheque_id":       str (hex),
                "amount_per_user": int,      # lamports per recipient
                "recipients":      list[str],
                "claimed":         list[bool],
                "bump":            int,
            }
        """
        cid = _cid(cheque_id)
        pda, _ = self.native_cheque_pda(cid)
        resp = self.provider.get_account_info(pda)
        if resp.value is None:
            return None
        raw = bytes(resp.value.data)[8:]

        creator         = Pubkey.from_bytes(raw[0:32])
        stored_id       = raw[32:64]
        amount_per_user = struct.unpack_from("<Q", raw, 64)[0]

        off = 72
        n_r = struct.unpack_from("<I", raw, off)[0]; off += 4
        recipients = [str(Pubkey.from_bytes(raw[off + i*32: off + i*32 + 32])) for i in range(n_r)]
        off += n_r * 32

        n_c = struct.unpack_from("<I", raw, off)[0]; off += 4
        claimed = [bool(raw[off + i]) for i in range(n_c)]
        off += n_c

        return {
            "pda":             str(pda),
            "creator":         str(creator),
            "cheque_id":       stored_id.hex(),
            "amount_per_user": amount_per_user,
            "recipients":      recipients,
            "claimed":         claimed,
            "bump":            raw[off],
        }

    def parse_token_cheque(self, cheque_id) -> dict:
        """
        Read and decode a TokenCheque PDA.

        TokenCheque layout (after discriminator):
          creator (32) | cheque_id (32) | recipient (32) | mint (32) |
          amount (u64) | is_redeemed (bool) | bump (u8)

        Returns:
            dict: {
                "pda":         str,
                "creator":     str,
                "cheque_id":   str (hex),
                "recipient":   str,
                "mint":        str,
                "amount":      int,
                "is_redeemed": bool,
                "bump":        int,
            }
        """
        cid = _cid(cheque_id)
        pda, _ = self.token_cheque_pda(cid)
        resp = self.provider.get_account_info(pda)
        if resp.value is None:
            return None
        raw = bytes(resp.value.data)[8:]
        return {
            "pda":         str(pda),
            "creator":     str(Pubkey.from_bytes(raw[0:32])),
            "cheque_id":   raw[32:64].hex(),
            "recipient":   str(Pubkey.from_bytes(raw[64:96])),
            "mint":        str(Pubkey.from_bytes(raw[96:128])),
            "amount":      struct.unpack_from("<Q", raw, 128)[0],
            "is_redeemed": bool(raw[136]),
            "bump":        raw[137],
        }

    def parse_swap_cheque(self, cheque_id) -> dict:
        """
        Read and decode a SwapCheque PDA.

        SwapCheque layout (after discriminator):
          cheque_id (32) | spender (32) | receiver (32) |
          token_in (32) | amount_in (u64) | token_out (32) |
          amount_out (u64) | claimed (bool) | bump (u8)

        Returns:
            dict: {
                "pda":        str,
                "cheque_id":  str (hex),
                "spender":    str,
                "receiver":   str,
                "token_in":   str,
                "amount_in":  int,
                "token_out":  str,
                "amount_out": int,
                "claimed":    bool,
                "bump":       int,
            }
        """
        cid = _cid(cheque_id)
        pda, _ = self.swap_cheque_pda(cid)
        resp = self.provider.get_account_info(pda)
        if resp.value is None:
            return None
        raw = bytes(resp.value.data)[8:]
        return {
            "pda":        str(pda),
            "cheque_id":  raw[0:32].hex(),
            "spender":    str(Pubkey.from_bytes(raw[32:64])),
            "receiver":   str(Pubkey.from_bytes(raw[64:96])),
            "token_in":   str(Pubkey.from_bytes(raw[96:128])),
            "amount_in":  struct.unpack_from("<Q", raw, 128)[0],
            "token_out":  str(Pubkey.from_bytes(raw[136:168])),
            "amount_out": struct.unpack_from("<Q", raw, 168)[0],
            "claimed":    bool(raw[176]),
            "bump":       raw[177],
        }

    # ── Internal tx helpers ───────────────────────────────────────────────────

    def _send(self, ixs: list, extra_signers: list = None) -> str:
        """Build, sign, and broadcast synchronously. Returns signature string."""
        payer = self.key
        blockhash = self.provider.get_latest_blockhash().value.blockhash
        seen = {str(payer.pubkey())}
        signers = [payer]
        for s in (extra_signers or []):
            pk = str(s.pubkey())
            if pk not in seen:
                seen.add(pk)
                signers.append(s)
        msg = Message(instructions=ixs, payer=payer.pubkey())
        tx  = Transaction(message=msg, from_keypairs=signers, recent_blockhash=blockhash)
        return str(self.provider.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value)

    async def _send_async(self, ixs: list, extra_signers: list = None) -> str:
        """Async version of _send."""
        payer = self.key
        blockhash = (await self.async_client.get_latest_blockhash()).value.blockhash
        seen = {str(payer.pubkey())}
        signers = [payer]
        for s in (extra_signers or []):
            pk = str(s.pubkey())
            if pk not in seen:
                seen.add(pk)
                signers.append(s)
        msg = Message(instructions=ixs, payer=payer.pubkey())
        tx  = Transaction(message=msg, from_keypairs=signers, recent_blockhash=blockhash)
        return str((await self.async_client.send_transaction(tx, opts=TxOpts(skip_preflight=True))).value)

    # ── Native SOL group cheque ───────────────────────────────────────────────

    async def init_native_cheque(
        self,
        cheque_id,
        recipients: list,
        lamports: int,
        user_bps: int = 0,
        build_instruction: bool = False,
    ) -> dict:
        """
        Create a SOL group cheque. Up to 20 recipients each claim an equal share.
        The fee is deducted by the contract before dividing (user_bps or contract default).

        Args:
            cheque_id  (str|bytes): 32-byte unique cheque identifier (string auto-padded).
            recipients (list[str]): Up to 20 Base58 recipient addresses.
            lamports   (int):       Total lamports to lock (fee deducted on-chain).
            user_bps   (int):       Custom fee in bps; 0 = use contract default.

        Returns:
            dict: { "cheque_pda": str, "cheque_id": str (hex), "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _ = self.config_pda()
        cheque_pda, _ = self.native_cheque_pda(cid)
        payer_pk = self.key.pubkey()

        # Borsh: [u8;32] | Vec<Pubkey>(len u32 + 32*n) | u64 user_bps | u64 lamports
        recipient_pks = [Pubkey.from_string(r) for r in recipients]
        data = (
            _disc("init_native_cheque")
            + cid
            + struct.pack("<I", len(recipient_pks))
            + b"".join(bytes(r) for r in recipient_pks)
            + struct.pack("<Q", user_bps)
            + struct.pack("<Q", lamports)
        )
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=cheque_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,       is_signer=True,  is_writable=True),
                AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return [ix]
        sig = await self._send_async([ix])
        return {"cheque_pda": str(cheque_pda), "cheque_id": cid.hex(), "signature": sig}

    async def cash_out_native_cheque(self, cheque_id, build_instruction: bool = False) -> dict:
        """
        Claim your SOL share from a group cheque. Caller must be in the recipients list.

        Args:
            cheque_id (str|bytes): Cheque identifier.

        Returns:
            dict: { "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        cheque_pda, _ = self.native_cheque_pda(cid)
        payer_pk = self.key.pubkey()

        data = _disc("cash_out_native_cheque") + cid
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=cheque_pda, is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,   is_signer=True,  is_writable=True),
            ],
        )
        if build_instruction:
            return ix
        return {"signature": await self._send_async([ix])}

    async def close_native_cheque(self, cheque_id, build_instruction: bool = False) -> dict:
        """
        Close a NativeCheque PDA and recover rent. Creator only.
        If not all recipients have claimed: unclaimed funds + early-close penalty go to treasury.

        Args:
            cheque_id (str|bytes): Cheque identifier.

        Returns:
            dict: { "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _ = self.config_pda()
        cheque_pda, _ = self.native_cheque_pda(cid)
        payer_pk = self.key.pubkey()

        cfg = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        data = _disc("close_native_cheque") + cid
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=cheque_pda,   is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,     is_signer=False, is_writable=True),  # creator (close = creator)
                AccountMeta(pubkey=treasury_pk,  is_signer=False, is_writable=True),
                AccountMeta(pubkey=config_pda,   is_signer=False, is_writable=False),
                AccountMeta(pubkey=payer_pk,     is_signer=True,  is_writable=True),  # signer
            ],
        )
        if build_instruction:
            return ix
        return {"signature": await self._send_async([ix])}

    # ── SPL Token cheque ──────────────────────────────────────────────────────

    async def init_token_cheque(
        self,
        cheque_id,
        mint: str,
        amount: int,
        recipient: str,
        user_bps: int = 0,
        build_instruction: bool = False,
    ) -> dict:
        """
        Escrow SPL tokens in a vault ATA. Fee portion sent to treasury ATA.
        Vault ATA is owned by the TokenCheque PDA and created automatically.

        Args:
            cheque_id    (str|bytes): 32-byte cheque identifier.
            mint         (str):       Token mint address.
            amount       (int):       Raw token amount (decimals already applied).
            recipient    (str):       Recipient wallet address (stored on-chain).
            user_bps     (int):       Custom fee bps; 0 = contract default.
            treasury_ata (str):       Treasury ATA for this mint. Derived if omitted.

        Returns:
            dict: { "cheque_pda": str, "cheque_id": str (hex), "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _      = self.config_pda()
        token_cheque_pda, _ = self.token_cheque_pda(cid)
        payer_pk           = self.key.pubkey()
        mint_pk            = Pubkey.from_string(mint)
        recipient_pk       = Pubkey.from_string(recipient)

        cfg = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])
        treas_ata   = get_associated_token_address(treasury_pk, mint_pk)
        signer_ata  = get_associated_token_address(payer_pk, mint_pk)
        vault_ata   = get_associated_token_address(token_cheque_pda, mint_pk)

        # Borsh: [u8;32] | u64 amount | u64 user_bps
        data = _disc("init_token_cheque") + cid + struct.pack("<Q", amount) + struct.pack("<Q", user_bps)
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,               is_signer=False, is_writable=True),
                AccountMeta(pubkey=token_cheque_pda,         is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_pk,                  is_signer=False, is_writable=False),
                AccountMeta(pubkey=signer_ata,               is_signer=False, is_writable=True),
                AccountMeta(pubkey=treas_ata,                is_signer=False, is_writable=True),
                AccountMeta(pubkey=vault_ata,                is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury_pk,              is_signer=False, is_writable=False),
                AccountMeta(pubkey=recipient_pk,             is_signer=False, is_writable=False),
                AccountMeta(pubkey=payer_pk,                 is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID,         is_signer=False, is_writable=False),
                AccountMeta(pubkey=ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSTEM_PROGRAM,           is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        sig = await self._send_async([ix])
        return {"cheque_pda": str(token_cheque_pda), "cheque_id": cid.hex(), "signature": sig}

    async def cash_out_token_cheque(
        self,
        cheque_id,
        mint: str,
        recipient_ata: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Redeem a token cheque — tokens released from vault to recipient ATA.
        Caller must be the designated recipient stored on-chain.

        Args:
            cheque_id     (str|bytes): Cheque identifier.
            mint          (str):       Token mint address.
            recipient_ata (str):       Recipient's ATA. Derived from self.key if omitted.

        Returns:
            dict: { "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        token_cheque_pda, _ = self.token_cheque_pda(cid)
        payer_pk  = self.key.pubkey()
        mint_pk   = Pubkey.from_string(mint)

        vault_ata  = get_associated_token_address(token_cheque_pda, mint_pk)
        recip_ata  = Pubkey.from_string(recipient_ata) if recipient_ata else get_associated_token_address(payer_pk, mint_pk)

        # creator needed for 50/50 rent split — read from on-chain state
        cheque_data = self.parse_token_cheque(cheque_id)
        creator_pk  = Pubkey.from_string(cheque_data["creator"])

        data = _disc("cash_out_token_cheque") + cid
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=token_cheque_pda, is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_pk,          is_signer=False, is_writable=False),
                AccountMeta(pubkey=vault_ata,        is_signer=False, is_writable=True),
                AccountMeta(pubkey=recip_ata,        is_signer=False, is_writable=True),
                AccountMeta(pubkey=creator_pk,       is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,         is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        return {"signature": await self._send_async([ix])}

    # ── Swap cheque ───────────────────────────────────────────────────────────

    async def init_swap_cheque(
        self,
        cheque_id,
        mint_in: str,
        mint_out: str,
        amount_in: int,
        amount_out: int,
        receiver: str,
        user_bps: int = 0,
        treasury_ata_in: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Lock token_in in a vault ATA. Receiver must deliver token_out to unlock it.
        Fee on token_in is sent to treasury ATA at init time.

        Args:
            cheque_id       (str|bytes): 32-byte cheque identifier.
            mint_in         (str):       Mint of the token the spender locks.
            mint_out        (str):       Mint of the token the receiver must supply.
            amount_in       (int):       Raw amount of token_in to lock (fee deducted by contract).
            amount_out      (int):       Raw amount of token_out the receiver must deliver.
            receiver        (str):       Wallet address allowed to cash out.
            user_bps        (int):       Custom fee bps; 0 = contract default.
            treasury_ata_in (str):       Treasury ATA for mint_in. Derived if omitted.

        Returns:
            dict: { "cheque_pda": str, "cheque_id": str (hex), "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _       = self.config_pda()
        swap_cheque_pda, _  = self.swap_cheque_pda(cid)
        payer_pk    = self.key.pubkey()
        mint_in_pk  = Pubkey.from_string(mint_in)
        mint_out_pk = Pubkey.from_string(mint_out)
        receiver_pk = Pubkey.from_string(receiver)

        cfg = self.get_config()
        treasury_pk  = Pubkey.from_string(cfg["treasury"])
        treas_ata_in = Pubkey.from_string(treasury_ata_in) if treasury_ata_in else get_associated_token_address(treasury_pk, mint_in_pk)
        signer_ata   = get_associated_token_address(payer_pk, mint_in_pk)
        vault_ata    = get_associated_token_address(swap_cheque_pda, mint_in_pk)

        # Borsh: [u8;32] | Pubkey receiver | u64 amount_in | u64 amount_out | u64 user_bps
        data = (
            _disc("init_swap_cheque")
            + cid
            + bytes(receiver_pk)
            + struct.pack("<Q", amount_in)
            + struct.pack("<Q", amount_out)
            + struct.pack("<Q", user_bps)
        )
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,               is_signer=False, is_writable=True),
                AccountMeta(pubkey=swap_cheque_pda,          is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_in_pk,               is_signer=False, is_writable=False),
                AccountMeta(pubkey=mint_out_pk,              is_signer=False, is_writable=False),
                AccountMeta(pubkey=signer_ata,               is_signer=False, is_writable=True),
                AccountMeta(pubkey=treas_ata_in,             is_signer=False, is_writable=True),
                AccountMeta(pubkey=vault_ata,                is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury_pk,              is_signer=False, is_writable=False),
                AccountMeta(pubkey=payer_pk,                 is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID,         is_signer=False, is_writable=False),
                AccountMeta(pubkey=ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSTEM_PROGRAM,           is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        sig = await self._send_async([ix])
        return {"cheque_pda": str(swap_cheque_pda), "cheque_id": cid.hex(), "signature": sig}

    async def cash_out_swap_cheque(
        self,
        cheque_id,
        mint_in: str,
        mint_out: str,
        spender: str,
        treasury_ata_in: str = None,
        treasury_ata_out: str = None,
        receiver_ata_in: str = None,
        receiver_ata_out: str = None,
        spender_ata_out: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Deliver token_out to receive token_in from the vault.
        Fees on both legs are charged by the contract.
        Caller must be the designated receiver.

        Args:
            cheque_id        (str|bytes): Cheque identifier.
            mint_in          (str):       Mint of the locked token_in.
            mint_out         (str):       Mint of the token_out to deliver.
            spender          (str):       Spender's wallet (receives token_out).
            treasury_ata_in  (str):       Treasury ATA for mint_in.  Derived if omitted.
            treasury_ata_out (str):       Treasury ATA for mint_out. Derived if omitted.
            receiver_ata_in  (str):       Receiver ATA for mint_in.  Derived if omitted.
            receiver_ata_out (str):       Receiver ATA for mint_out. Derived if omitted.
            spender_ata_out  (str):       Spender ATA for mint_out.  Derived if omitted.

        Returns:
            dict: { "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _      = self.config_pda()
        swap_cheque_pda, _ = self.swap_cheque_pda(cid)
        signer_pk   = self.key.pubkey()
        mint_in_pk  = Pubkey.from_string(mint_in)
        mint_out_pk = Pubkey.from_string(mint_out)
        spender_pk  = Pubkey.from_string(spender)

        cfg = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        def _ata(owner_pk, mint_pk, override=None):
            return Pubkey.from_string(override) if override else get_associated_token_address(owner_pk, mint_pk)

        vault_ata_pk        = get_associated_token_address(swap_cheque_pda, mint_in_pk)
        receiver_ata_in_pk  = _ata(signer_pk,   mint_in_pk,  receiver_ata_in)
        receiver_ata_out_pk = _ata(signer_pk,   mint_out_pk, receiver_ata_out)
        spender_ata_out_pk  = _ata(spender_pk,  mint_out_pk, spender_ata_out)
        treas_ata_in_pk     = _ata(treasury_pk, mint_in_pk,  treasury_ata_in)
        treas_ata_out_pk    = _ata(treasury_pk, mint_out_pk, treasury_ata_out)

        data = _disc("cash_out_swap_cheque") + cid
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,          is_signer=False, is_writable=True),
                AccountMeta(pubkey=swap_cheque_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_in_pk,          is_signer=False, is_writable=False),
                AccountMeta(pubkey=mint_out_pk,         is_signer=False, is_writable=False),
                AccountMeta(pubkey=vault_ata_pk,        is_signer=False, is_writable=True),
                AccountMeta(pubkey=receiver_ata_in_pk,  is_signer=False, is_writable=True),
                AccountMeta(pubkey=receiver_ata_out_pk, is_signer=False, is_writable=True),
                AccountMeta(pubkey=spender_ata_out_pk,  is_signer=False, is_writable=True),
                AccountMeta(pubkey=treas_ata_in_pk,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=treas_ata_out_pk,    is_signer=False, is_writable=True),
                AccountMeta(pubkey=spender_pk,          is_signer=False, is_writable=True),  # rent split
                AccountMeta(pubkey=signer_pk,           is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID,    is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        return {"signature": await self._send_async([ix])}
