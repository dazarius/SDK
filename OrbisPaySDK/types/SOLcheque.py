
import base64
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
        key: str = None,
        address: str = None,
        program_id = PROGRAM_ID,
        build_tx: bool = False,
    ):
        """
        Client for the OrbisCheques on-chain program (Anchor).

        Args:
            rpc_url    (str):  Solana RPC endpoint.
            key        (str):  Base58-encoded private key for signing.
            address    (str):  Base58 public key. Used as fee-payer when build_tx=True
                               and no private key is available (DApp / external wallet flow).
            program_id (str):  Override the default program ID.
            build_tx   (bool): If True, return base64-serialized transaction instead of
                               broadcasting. Signed if key is set, unsigned if address only.
        """
        self.rpc_url      = rpc_url
        self.provider     = Client(rpc_url)
        self.async_client = AsyncClient(rpc_url)
        self.key          = None
        self.address      = None
        self.PROGRAM_ID   = program_id
        self.build_tx     = build_tx
        if key:
            self.set_key(key)
        if address:
            self.set_address(address)

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

    def set_address(self, address: str) -> None:
        """
        Set the fee-payer address (public key only, no signing capability).
        Used in build_tx=True mode when signing is done by an external wallet.

        Args:
            address (str | Pubkey): Base58 public key string or Pubkey object.
        """
        if isinstance(address, str):
            self.address = Pubkey.from_string(address)
        elif isinstance(address, Pubkey):
            self.address = address
        else:
            raise ValueError("address must be a base58 string or Pubkey")

    def set_params(self, rpc_url: str = None, key=None, address: str = None) -> None:
        """
        Update RPC endpoint, keypair, and/or address at runtime.

        Args:
            rpc_url (str):          New RPC endpoint.
            key     (str|Keypair):  New signing keypair.
            address (str):          New fee-payer address (public key).
        """
        if rpc_url:
            self.rpc_url      = rpc_url
            self.provider     = Client(rpc_url)
            self.async_client = AsyncClient(rpc_url)
        if key:
            self.set_key(key)
        if address:
            self.set_address(address)

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

    def multi_cheque_pda(self, cheque_id):
        """Returns (Pubkey, bump) for a MultiCheque PDA (seeds: ['multi_cheque', cheque_id])."""
        return Pubkey.find_program_address([b"multi_cheque", _cid(cheque_id)], self.PROGRAM_ID)

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
        # Config layout (after discriminator): owner(32) | treasury(32) | collected_fees(u64) | is_active(bool) | bump(u8)
        return {
            "pda":            str(config_pda),
            "owner":          str(Pubkey.from_bytes(raw[0:32])),
            "treasury":       str(Pubkey.from_bytes(raw[32:64])),
            "collected_fees": struct.unpack_from("<Q", raw, 64)[0],
            "is_active":      bool(raw[72]),
            "bump":           raw[73],
        }

    def parse_native_cheque(self, cheque_id_or_pda) -> dict:
        """
        Read and decode a NativeCheque PDA.
        Accepts either a cheque_id (str/bytes) or a base58 PDA address.

        Returns:
            dict: { "pda", "creator", "cheque_id", "recipient", "amount", "claimed", "bump" }
        """
        if isinstance(cheque_id_or_pda, str):
            try:
                pda = Pubkey.from_string(cheque_id_or_pda)
            except Exception:
                pda, _ = self.native_cheque_pda(_cid(cheque_id_or_pda))
        else:
            pda, _ = self.native_cheque_pda(_cid(cheque_id_or_pda))
        resp = self.provider.get_account_info(pda)
        if resp.value is None:
            return None
        raw = bytes(resp.value.data)[8:]
        return {
            "pda":       str(pda),
            "creator":   str(Pubkey.from_bytes(raw[0:32])),
            "cheque_id": raw[32:64].hex(),
            "recipient": str(Pubkey.from_bytes(raw[64:96])),
            "amount":    struct.unpack_from("<Q", raw, 96)[0],
            "claimed":   bool(raw[104]),
            "bump":      raw[105],
        }

    def parse_multi_cheque(self, cheque_id_or_pda) -> dict:
        """
        Read and decode a MultiCheque PDA.
        Accepts either a cheque_id (str/bytes) or a base58 PDA address.

        Returns:
            dict: { "pda", "creator", "cheque_id", "amount_per_user", "recipients", "claimed", "bump" }
        """
        if isinstance(cheque_id_or_pda, str):
            try:
                pda = Pubkey.from_string(cheque_id_or_pda)
            except Exception:
                pda, _ = self.multi_cheque_pda(_cid(cheque_id_or_pda))
        else:
            pda, _ = self.multi_cheque_pda(_cid(cheque_id_or_pda))
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

    def parse_token_cheque(self, cheque_id_or_pda) -> dict:
        """
        Read and decode a TokenCheque PDA.
        Accepts either a cheque_id (str/bytes) or a base58 PDA address.

        Returns:
            dict: { "pda", "creator", "cheque_id", "recipient", "mint", "amount", "is_redeemed", "bump" }
        """
        if isinstance(cheque_id_or_pda, str):
            try:
                pda = Pubkey.from_string(cheque_id_or_pda)
            except Exception:
                pda, _ = self.token_cheque_pda(_cid(cheque_id_or_pda))
        else:
            pda, _ = self.token_cheque_pda(_cid(cheque_id_or_pda))
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

    def parse_swap_cheque(self, cheque_id_or_pda) -> dict:
        """
        Read and decode a SwapCheque PDA.
        Accepts either a cheque_id (str/bytes) or a base58 PDA address.

        Returns:
            dict: { "pda", "cheque_id", "spender", "receiver", "token_in", "amount_in", "token_out", "amount_out", "claimed", "bump" }
        """
        if isinstance(cheque_id_or_pda, str):
            try:
                pda = Pubkey.from_string(cheque_id_or_pda)
            except Exception:
                pda, _ = self.swap_cheque_pda(_cid(cheque_id_or_pda))
        else:
            pda, _ = self.swap_cheque_pda(_cid(cheque_id_or_pda))
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

    def _payer_pubkey(self):
        if self.key:
            return self.key.pubkey()
        if self.address:
            return self.address
        raise ValueError("Neither key nor address is set")

    def _build_tx_base64(self, ixs: list, blockhash, extra_signers: list = None) -> str:
        payer_pk = self._payer_pubkey()
        msg = Message.new_with_blockhash(ixs, payer_pk, blockhash)
        if self.key:
            seen = {str(payer_pk)}
            signers = [self.key]
            for s in (extra_signers or []):
                pk = str(s.pubkey())
                if pk not in seen:
                    seen.add(pk)
                    signers.append(s)
            tx = Transaction(message=msg, from_keypairs=signers, recent_blockhash=blockhash)
        else:
            # address-only: unsigned transaction for external wallet signing
            from solders.signature import Signature
            tx = Transaction.populate(msg, [Signature.default()])
        return base64.b64encode(bytes(tx)).decode()

    def _send(self, ixs: list, extra_signers: list = None) -> str:
        blockhash = self.provider.get_latest_blockhash().value.blockhash
        if self.build_tx:
            return self._build_tx_base64(ixs, blockhash, extra_signers)
        if not self.key:
            raise ValueError("key is required to send transactions")
        payer = self.key
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
        blockhash = (await self.async_client.get_latest_blockhash()).value.blockhash
        if self.build_tx:
            return self._build_tx_base64(ixs, blockhash, extra_signers)
        if not self.key:
            raise ValueError("key is required to send transactions")
        payer = self.key
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

    # ── Native SOL cheque — single recipient ─────────────────────────────────

    async def init_native_cheque(
        self,
        cheque_id,
        recipient: str,
        lamports: int,
        build_instruction: bool = False,
    ) -> dict:
        """
        Create a single-recipient SOL cheque (NativeCheque PDA).

        Args:
            cheque_id (str|bytes): 32-byte unique cheque identifier.
            recipient (str):       Base58 recipient address.
            lamports  (int):       Total lamports to lock (fee deducted on-chain at NATIVE_BPS=0.15%).

        Returns:
            dict: { "tx": str, "id": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _ = self.config_pda()
        cheque_pda, _ = self.native_cheque_pda(cid)
        payer_pk      = self.key.pubkey()
        recipient_pk  = Pubkey.from_string(recipient)

        cfg         = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        # Borsh: [u8;32] cheque_id | Pubkey(32) recipient | u64 lamports
        data = (
            _disc("init_native_cheque")
            + cid
            + bytes(recipient_pk)
            + struct.pack("<Q", lamports)
        )
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=cheque_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury_pk,    is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,       is_signer=True,  is_writable=True),
                AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return [ix]
        sig = await self._send_async([ix])
        return {"tx": sig, "id": str(cheque_pda)}

    # ── Native SOL cheque — multi recipient ──────────────────────────────────

    async def init_multi_cheque(
        self,
        cheque_id,
        recipients: list,
        lamports: int,
        build_instruction: bool = False,
    ) -> dict:
        """
        Create a multi-recipient SOL cheque (MultiCheque PDA). Up to 20 recipients.

        Args:
            cheque_id  (str|bytes): 32-byte unique cheque identifier.
            recipients (list[str]): Up to 20 Base58 recipient addresses.
            lamports   (int):       Total lamports to lock (fee deducted on-chain at MULTI_BPS=0.30%).

        Returns:
            dict: { "tx": str, "id": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _ = self.config_pda()
        cheque_pda, _ = self.multi_cheque_pda(cid)
        payer_pk      = self.key.pubkey()

        cfg         = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        recipient_pks = [Pubkey.from_string(r) for r in recipients]
        # Borsh: [u8;32] cheque_id | Vec<Pubkey>(u32 len + 32*n) recipients | u64 lamports
        data = (
            _disc("init_multi_cheque")
            + cid
            + struct.pack("<I", len(recipient_pks))
            + b"".join(bytes(r) for r in recipient_pks)
            + struct.pack("<Q", lamports)
        )
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=config_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=cheque_pda,     is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury_pk,    is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,       is_signer=True,  is_writable=True),
                AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return [ix]
        sig = await self._send_async([ix])
        return {"tx": sig, "id": str(cheque_pda)}

    async def cash_out_native_cheque(self, cheque_id, build_instruction: bool = False) -> dict:
        """
        Claim your SOL share from a group cheque. Caller must be in the recipients list.

        Args:
            cheque_id (str|bytes): Cheque identifier OR base58 PDA address.

        Returns:
            dict: { "tx": str, "id": str, "pda": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        if isinstance(cheque_id, str):
            try:
                cheque_pda = Pubkey.from_string(cheque_id)
                on_chain = self.parse_native_cheque(cheque_pda)
                if on_chain is None:
                    raise ValueError("Cheque not found on-chain")
                cid = bytes.fromhex(on_chain["cheque_id"])
            except (ValueError, RuntimeError):
                raise
            except Exception:
                cid = _cid(cheque_id)
                cheque_pda, _ = self.native_cheque_pda(cid)
        else:
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
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(cheque_pda)}

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
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(cheque_pda)}

    async def cash_out_multi_cheque(self, cheque_id, build_instruction: bool = False) -> dict:
        """
        Claim your SOL share from a multi-recipient cheque (MultiCheque PDA).
        Caller must be in the recipients list.

        Args:
            cheque_id (str|bytes): Cheque identifier OR base58 PDA address.

        Returns:
            dict: { "tx": str, "id": str, "pda": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        if isinstance(cheque_id, str):
            try:
                cheque_pda = Pubkey.from_string(cheque_id)
                on_chain = self.parse_multi_cheque(cheque_pda)
                if on_chain is None:
                    raise ValueError("Cheque not found on-chain")
                cid = bytes.fromhex(on_chain["cheque_id"])
            except (ValueError, RuntimeError):
                raise
            except Exception:
                cid = _cid(cheque_id)
                cheque_pda, _ = self.multi_cheque_pda(cid)
        else:
            cid = _cid(cheque_id)
            cheque_pda, _ = self.multi_cheque_pda(cid)
        payer_pk = self.key.pubkey()

        data = _disc("cash_out_multi_cheque") + cid
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
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(cheque_pda)}

    async def close_multi_cheque(self, cheque_id, build_instruction: bool = False) -> dict:
        """
        Close a MultiCheque PDA and recover rent. Creator only.
        Unclaimed funds + early-close penalty (10%) go to treasury if not all claimed.

        Args:
            cheque_id (str|bytes): Cheque identifier.

        Returns:
            dict: { "signature": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        cid = _cid(cheque_id)
        config_pda, _ = self.config_pda()
        cheque_pda, _ = self.multi_cheque_pda(cid)
        payer_pk = self.key.pubkey()

        cfg = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        data = _disc("close_multi_cheque") + cid
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
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(cheque_pda)}

    # ── SPL Token cheque ──────────────────────────────────────────────────────

    async def init_token_cheque(
        self,
        cheque_id,
        mint: str,
        amount: int,
        recipient: str,
        build_instruction: bool = False,
    ) -> dict:
        """
        Escrow SPL tokens in a vault ATA. Fee portion sent to treasury ATA.
        Vault ATA is owned by the TokenCheque PDA and created automatically.

        Args:
            cheque_id (str|bytes): 32-byte cheque identifier.
            mint      (str):       Token mint address.
            amount    (int):       Raw token amount (decimals already applied).
            recipient (str):       Recipient wallet address (stored on-chain).

        Returns:
            dict: { "tx": str, "id": str }
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

        # Borsh: [u8;32] cheque_id | u64 amount
        data = _disc("init_token_cheque") + cid + struct.pack("<Q", amount)
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
        return {"tx": sig, "id": str(token_cheque_pda)}

    async def cash_out_token_cheque(
        self,
        cheque_id,
        recipient_ata: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Redeem a token cheque — tokens released from vault to recipient ATA.
        Mint and amount are read from the on-chain TokenCheque PDA automatically.
        Caller must be the designated recipient stored on-chain.

        Args:
            cheque_id     (str|bytes): Cheque identifier OR base58 PDA address.
            recipient_ata (str):       Recipient's ATA. Derived from self.key if omitted.

        Returns:
            dict: { "tx": str, "id": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        payer_pk = self.key.pubkey()

        on_chain = self.parse_token_cheque(cheque_id)
        if on_chain is None:
            raise ValueError("Token cheque not found on-chain")
        cid              = bytes.fromhex(on_chain["cheque_id"])
        token_cheque_pda = Pubkey.from_string(on_chain["pda"])
        mint_pk          = Pubkey.from_string(on_chain["mint"])

        vault_ata  = get_associated_token_address(token_cheque_pda, mint_pk)
        recip_ata  = Pubkey.from_string(recipient_ata) if recipient_ata else get_associated_token_address(payer_pk, mint_pk)

        data = _disc("cash_out_token_cheque") + cid
        ix = Instruction(
            program_id=self.PROGRAM_ID,
            data=data,
            accounts=[
                AccountMeta(pubkey=token_cheque_pda, is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_pk,          is_signer=False, is_writable=False),
                AccountMeta(pubkey=vault_ata,        is_signer=False, is_writable=True),
                AccountMeta(pubkey=recip_ata,        is_signer=False, is_writable=True),
                AccountMeta(pubkey=payer_pk,         is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(token_cheque_pda)}

    # ── Swap cheque ───────────────────────────────────────────────────────────

    async def init_swap_cheque(
        self,
        cheque_id,
        mint_in: str,
        mint_out: str,
        amount_in: int,
        amount_out: int,
        receiver: str,
        treasury_ata_in: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Lock token_in in a vault ATA. Receiver must deliver token_out to unlock it.
        Fee on token_in is sent to treasury ATA at init time (SWAP_BPS=0.50%).

        Args:
            cheque_id       (str|bytes): 32-byte cheque identifier.
            mint_in         (str):       Mint of the token the spender locks.
            mint_out        (str):       Mint of the token the receiver must supply.
            amount_in       (int):       Raw amount of token_in to lock (fee deducted by contract).
            amount_out      (int):       Raw amount of token_out the receiver must deliver.
            receiver        (str):       Wallet address allowed to cash out.
            treasury_ata_in (str):       Treasury ATA for mint_in. Derived if omitted.

        Returns:
            dict: { "tx": str, "id": str }
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

        # Borsh: [u8;32] cheque_id | Pubkey(32) receiver | u64 amount_in | u64 amount_out
        data = (
            _disc("init_swap_cheque")
            + cid
            + bytes(receiver_pk)
            + struct.pack("<Q", amount_in)
            + struct.pack("<Q", amount_out)
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
        return {"tx": sig, "id": str(swap_cheque_pda)}

    async def cash_out_swap_cheque(
        self,
        cheque_id,
        treasury_ata_out: str = None,
        receiver_ata_in: str = None,
        receiver_ata_out: str = None,
        spender_ata_out: str = None,
        build_instruction: bool = False,
    ) -> dict:
        """
        Deliver token_out to receive token_in from the vault.
        mint_in, mint_out and spender are read from the on-chain SwapCheque PDA automatically.
        Caller must be the designated receiver.

        Args:
            cheque_id        (str|bytes): Cheque identifier OR base58 PDA address.
            treasury_ata_out (str):       Treasury ATA for mint_out. Derived if omitted.
            receiver_ata_in  (str):       Receiver ATA for mint_in.  Derived if omitted.
            receiver_ata_out (str):       Receiver ATA for mint_out. Derived if omitted.
            spender_ata_out  (str):       Spender ATA for mint_out.  Derived if omitted.

        Returns:
            dict: { "tx": str, "id": str }
        """
        if not self.key:
            raise ValueError("Keypair not set")
        signer_pk     = self.key.pubkey()
        config_pda, _ = self.config_pda()

        on_chain = self.parse_swap_cheque(cheque_id)
        if on_chain is None:
            raise ValueError("Swap cheque not found on-chain")
        cid             = bytes.fromhex(on_chain["cheque_id"])
        swap_cheque_pda = Pubkey.from_string(on_chain["pda"])
        mint_in_pk      = Pubkey.from_string(on_chain["token_in"])
        mint_out_pk     = Pubkey.from_string(on_chain["token_out"])
        spender_pk      = Pubkey.from_string(on_chain["spender"])

        cfg = self.get_config()
        treasury_pk = Pubkey.from_string(cfg["treasury"])

        def _ata(owner_pk, mint_pk, override=None):
            return Pubkey.from_string(override) if override else get_associated_token_address(owner_pk, mint_pk)

        vault_ata_pk        = get_associated_token_address(swap_cheque_pda, mint_in_pk)
        receiver_ata_in_pk  = _ata(signer_pk,   mint_in_pk,  receiver_ata_in)
        receiver_ata_out_pk = _ata(signer_pk,   mint_out_pk, receiver_ata_out)
        spender_ata_out_pk  = _ata(spender_pk,  mint_out_pk, spender_ata_out)
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
                AccountMeta(pubkey=treas_ata_out_pk,    is_signer=False, is_writable=True),
                AccountMeta(pubkey=signer_pk,           is_signer=True,  is_writable=True),
                AccountMeta(pubkey=TOKEN_PROGRAM_ID,    is_signer=False, is_writable=False),
            ],
        )
        if build_instruction:
            return ix
        return {"tx": await self._send_async([ix]), "id": cid.hex(), "pda": str(swap_cheque_pda)}
