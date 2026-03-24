import asyncio
import httpx
import base64
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any, List

from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.utils import to_nano, from_nano, bytes_to_b64str, Address
from tonsdk.boc import Cell
from tonutils.wallet import WalletV5R1
from tonutils.client import ToncenterV3Client
from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key

from pytoniq_core import begin_cell as pbegin_cell, Address as PAddress
from pytoniq_core import Cell as PCell

NANOTON = 1_000_000_000  # 1 TON = 1,000,000,000 nanotons
DECIMALS = 9
DEFAULT_VERSION = "wr5" 
coigeco_id = "ton"
currency_sym = "$"

class TON:
    """
    TON blockchain interface for OrbisPaySDK.
    Supports native TON transfers, Jetton (TIP-3/TEP-74) token transfers,
    balance queries, and wallet management via TonCenter API.
    Wallet versions: 'v3r1', 'v3r2', 'v4r2', 'wr5' (WalletV5R1).
    """

    WALLET_VERSIONS = {
        "v3r1": WalletVersionEnum.v3r1,
        "v3r2": WalletVersionEnum.v3r2,
        "v4r2": WalletVersionEnum.v4r2,
        "wr5": "wr5",  # handled separately via tonutils WalletV5R1
    }

    def __init__(
        self,
        api_url: str = "https://toncenter.com/api/v2",
        api_key: Optional[str] = None,
        mnemonics: Optional[List[str]] = None,
        wallet_version: str = "v4r2",
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.wallet = None
        self.mnemonics = None
        self.wallet_version = wallet_version
        self._pub_k = None
        self._priv_k = None
        self._v5_wallet: Optional[WalletV5R1] = None
        self._v5_client: Optional[ToncenterV3Client] = None

        if mnemonics:
            self.set_wallet(mnemonics, wallet_version)

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def set_wallet(self, mnemonics: List[str], version: str = "v4r2"):
        """Load wallet from mnemonic phrase (24 words list).
        Supported versions: 'v3r1', 'v3r2', 'v4r2', 'wr5' (WalletV5R1)."""
        self.mnemonics = mnemonics
        self.wallet_version = version

        if version == "wr5":
            self._v5_client = ToncenterV3Client(api_key=self.api_key)
            wallet_v5, pub_k, priv_k, _mnemonics = WalletV5R1.from_mnemonic(
                client=self._v5_client, mnemonic=mnemonics,
            )
            self._v5_wallet = wallet_v5
            self._pub_k = pub_k
            self._priv_k = priv_k
            self.wallet = self._v5_wallet  # for compatibility checks (not None)
        else:
            wv = self.WALLET_VERSIONS.get(version, WalletVersionEnum.v4r2)
            _mnemonics, self._pub_k, self._priv_k, self.wallet = Wallets.from_mnemonics(
                mnemonics=mnemonics, version=wv, workchain=0
            )
            self._v5_wallet = None
            self._v5_client = None

    def set_params(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mnemonics: Optional[List[str]] = None,
        wallet_version: Optional[str] = DEFAULT_VERSION,
    ):
        if api_url:
            self.api_url = api_url.rstrip("/")
        if api_key:
            self.api_key = api_key
        if wallet_version:
            self.wallet_version = wallet_version
        if mnemonics:
            self.set_wallet(mnemonics, self.wallet_version)

    @staticmethod
    def gen_wallet(version: str = "wr5") -> dict:
        """Generate a new TON wallet. Returns mnemonics, address, raw address, and WR5 address.
        Supported versions: 'v3r1', 'v3r2', 'v4r2' (default), 'wr5' (WalletV5R1)."""
        client = ToncenterV3Client()
        version_map = {
            "v3r1": WalletVersionEnum.v3r1,
            "v3r2": WalletVersionEnum.v3r2,
            "v4r2": WalletVersionEnum.v4r2,
        }

        if version == "wr5":
            wallet_v5, pub_k, priv_k, mnemonics = WalletV5R1.create(client=client)
            return {
                "mnemonics": " ".join(mnemonics),
                "address": wallet_v5.address.to_str(True, True, False),
                "raw_address": wallet_v5.address.to_str(is_user_friendly=False),
                "WR5": wallet_v5.address.to_str(True, True, False),
            }

        wv = version_map.get(version, WalletVersionEnum.v4r2)
        mnemonics, pub_k, priv_k, wallet = Wallets.create(version=wv, workchain=0)
        wallet_v5, _pub_k, _priv_k, _mnem = WalletV5R1.from_mnemonic(
            client=client, mnemonic=mnemonics,
        )
        pub_key, priv_key = mnemonic_to_wallet_key(mnemonics)
        return {
            "mnemonics": " ".join(mnemonics),
            "key":priv_key,
            "address": wallet.address.to_string(True, True, False),
            "raw_address": wallet.address.to_string(False),
            "WR5": wallet_v5.address.to_str(True, True, False),
        }

    def get_address(self, bounceable: bool = True) -> str:
        """Get the wallet address in user-friendly format."""
        if not self.wallet:
            raise ValueError("Wallet not set. Use set_wallet() first.")

        if self.wallet_version == "wr5":
            return self._v5_wallet.address.to_str(
                is_user_friendly=True,
                is_url_safe=True,
                is_bounceable=bounceable,
            )
        return self.wallet.address.to_string(
            is_user_friendly=True,
            is_url_safe=True,
            is_bounceable=bounceable,
        )

    async def get_balance(self, address: Optional[str] = None) -> float:
        """Get TON balance in TON (not nanotons)."""
        if not address:
            address = self.get_address()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/getAddressBalance",
                params={"address": address},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                balance = int(data["result"])
                return {
                    "symbol":"TON",
                    "decimals":DECIMALS,
                    "balance":balance / NANOTON,
                    "raw_balance":balance
                    }

            raise ValueError(f"Failed to get balance: {data}")

    async def get_balance_batch(self, address_list: list) -> dict:
        """
        Get TON balances for multiple addresses in parallel.

        Returns:
            dict {address: {"symbol": "TON", "decimals": 9, "balance": float, "raw_balance": int}}
        """
        async def fetch(address):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self.api_url}/getAddressBalance",
                        params={"address": address},
                        headers=self._get_headers(),
                    )
                    data = resp.json()
                    if data.get("ok"):
                        raw = int(data["result"])
                        return address, {"symbol": "TON", "decimals": DECIMALS, "balance": raw / NANOTON, "raw_balance": raw}
            except Exception:
                pass
            return address, {"symbol": "TON", "decimals": DECIMALS, "balance": 0.0, "raw_balance": 0}

        results = await asyncio.gather(*[fetch(addr) for addr in address_list])
        return dict(results)

    async def get_wallet_info(self, address: Optional[str] = None) -> dict:
        """Get detailed wallet information (balance, seqno, state, etc.)."""
        if not address:
            address = self.get_address()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/getWalletInformation",
                params={"address": address},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return data["result"]
            raise ValueError(f"Failed to get wallet info: {data}")

    async def get_seqno(self, address: Optional[str] = None) -> int:
        """Get current sequence number for the wallet."""
        info = await self.get_wallet_info(address)
        return info.get("seqno", 0)

    async def transfer_native(
        self,
        to: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> dict:
        """
        Transfer native TON.

        Args:
            to: Recipient address (user-friendly or raw).
            amount: Amount in TON (e.g., 1.5 for 1.5 TON).
            memo: Optional text comment attached to the transfer.

        Returns:
            dict with transaction result.
        """
        if not self.wallet:
            raise ValueError("Wallet not set. Use set_wallet() first.")

        if self.wallet_version == "wr5":
            tx_hash = await self._v5_wallet.transfer(
                destination=to,
                amount=amount,
                body=memo,
            )
            return {
                "status": "sent",
                "tx_hash": tx_hash,
                "amount": amount,
                "to": to,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        seqno = await self.get_seqno()
        nano_amount = to_nano(amount, "ton")

        # Build payload (comment)
        payload = memo if memo else None

        query = self.wallet.create_transfer_message(
            to_addr=to,
            amount=nano_amount,
            seqno=seqno,
            payload=payload,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "status": "sent",
                    "result": data["result"],
                    "amount": amount,
                    "to": to,
                }
            raise ValueError(f"Transfer failed: {data}")

    def _build_jetton_transfer_body(
        self,
        to: str,
        amount: int,
        response_address: str,
        forward_amount: int = 0,
        comment: Optional[str] = None,
    ) -> Cell:
        """Build Jetton transfer message body (TEP-74 standard) using tonsdk Cell."""
        body = Cell()
        body.bits.write_uint(0x0F8A7EA5, 32)   # op::transfer
        body.bits.write_uint(0, 64)              # query_id
        body.bits.write_grams(amount)            # jetton amount
        body.bits.write_address(Address(to))     # destination owner
        body.bits.write_address(Address(response_address))  # response_destination
        body.bits.write_bit(0)                   # no custom_payload
        body.bits.write_grams(forward_amount)    # forward_ton_amount

        if comment:
            fwd_body = Cell()
            fwd_body.bits.write_uint(0, 32)
            fwd_body.bits.write_bytes(comment.encode("utf-8"))
            body.bits.write_bit(1)               # forward_payload in ref
            body.refs.append(fwd_body)
        else:
            body.bits.write_bit(0)               # no forward_payload

        return body

    @staticmethod
    def _build_jetton_transfer_body_v5(
        to: str,
        amount: int,
        response_address: str,
        forward_amount: int = 0,
        comment: Optional[str] = None,
    ):
        """Build Jetton transfer message body (TEP-74 standard) using pytoniq_core Cell for WR5."""
        builder = (
            pbegin_cell()
            .store_uint(0x0F8A7EA5, 32)           # op::transfer
            .store_uint(0, 64)                      # query_id
            .store_coins(amount)                    # jetton amount
            .store_address(PAddress(to))            # destination owner
            .store_address(PAddress(response_address))  # response_destination
            .store_bit(0)                           # no custom_payload
            .store_coins(forward_amount)            # forward_ton_amount
        )

        if comment:
            fwd_body = (
                pbegin_cell()
                .store_uint(0, 32)
                .store_snake_string(comment)
                .end_cell()
            )
            builder = builder.store_bit(1).store_ref(fwd_body)
        else:
            builder = builder.store_bit(0)

        return builder.end_cell()

    async def transfer_jetton(
        self,
        jetton_wallet_address: str,
        to: str,
        amount: int,
        forward_amount: int = 0,
        gas_amount: float = 0.05,
        comment: Optional[str] = None,
    ) -> dict:
        """
        Transfer Jettons (TON tokens, TEP-74 standard).

        Args:
            jetton_wallet_address: Sender's Jetton wallet address (not the master contract).
            to: Recipient's owner address.
            amount: Amount of Jettons in the smallest unit (with decimals applied).
            forward_amount: Amount of TON (in nanotons) forwarded with the transfer notification.
            gas_amount: TON amount attached for gas (default 0.05 TON).
            comment: Optional forward comment.

        Returns:
            dict with transaction result.
        """
        if not self.wallet:
            raise ValueError("Wallet not set. Use set_wallet() first.")

        response_address = self.get_address()

        if self.wallet_version == "wr5":
            body = self._build_jetton_transfer_body_v5(
                to=to,
                amount=amount,
                response_address=response_address,
                forward_amount=forward_amount,
                comment=comment,
            )
            tx_hash = await self._v5_wallet.transfer(
                destination=jetton_wallet_address,
                amount=gas_amount,
                body=body,
            )
            return {
                "status": "sent",
                "tx_hash": tx_hash,
                "jetton_amount": amount,
                "to": to,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        seqno = await self.get_seqno()

        body = self._build_jetton_transfer_body(
            to=to,
            amount=amount,
            response_address=response_address,
            forward_amount=forward_amount,
            comment=comment,
        )

        nano_gas = to_nano(gas_amount, "ton")

        query = self.wallet.create_transfer_message(
            to_addr=jetton_wallet_address,
            amount=nano_gas,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "status": "sent",
                    "result": data["result"],
                    "jetton_amount": amount,
                    "to": to,
                }
            raise ValueError(f"Jetton transfer failed: {data}")

    async def get_jetton_wallet_address(
        self, jetton_master: str, owner: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the Jetton wallet address for a given owner from the master contract.

        Args:
            jetton_master: Jetton master contract address.
            owner: Owner address (defaults to current wallet).
        """
        if not owner:
            owner = self.get_address()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/runGetMethod",
                json={
                    "address": jetton_master,
                    "method": "get_wallet_address",
                    "stack": [["tvm.Slice", owner]],
                },
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                stack = data["result"].get("stack", [])
                if stack and len(stack) > 0:
                    return stack[0]
            return None

    async def get_transactions(
        self, address: Optional[str] = None, limit: int = 10
    ) -> list:
        """Get recent transactions for the address."""
        if not address:
            address = self.get_address()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/getTransactions",
                params={"address": address, "limit": limit},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return data["result"]
            return []

    async def get_jetton_data(self, jetton_master: str) -> dict:
        """Get Jetton metadata (name, symbol, decimals, total supply)."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/runGetMethod",
                json={
                    "address": jetton_master,
                    "method": "get_jetton_data",
                    "stack": [],
                },
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return data["result"]
            raise ValueError(f"Failed to get jetton data: {data}")

    # ------------------------------------------------------------------ #
    #  Transaction parsing                                                 #
    # ------------------------------------------------------------------ #

    # Known TEP-74 / TEP-62 opcodes
    _JETTON_OPCODES: Dict[int, str] = {
        0x0F8A7EA5: "jetton_transfer",
        0x178D4519: "jetton_internal_transfer",
        0x7362D09C: "jetton_transfer_notification",
        0xD53276DB: "jetton_excesses",
        0x595F07BC: "jetton_burn",
        0x05138D91: "nft_transfer",
        0x2FCB26A2: "nft_get_static_data",
    }

    @staticmethod
    def _decode_comment(msg_data: dict) -> Optional[str]:
        """Extract human-readable comment from msg_data."""
        if not msg_data:
            return None
        dtype = msg_data.get("@type", "")

        # Plain text comment
        if dtype == "msg.dataText":
            raw = msg_data.get("text", "")
            if not raw:
                return None
            try:
                return base64.b64decode(raw).decode("utf-8")
            except Exception:
                return None

        # Raw body — first 32 bits == 0 means text comment
        if dtype == "msg.dataRaw":
            body_b64 = msg_data.get("body", "")
            if not body_b64:
                return None
            try:
                cell = PCell.one_from_boc(base64.b64decode(body_b64))
                cs = cell.begin_parse()
                if cs.remaining_bits < 32:
                    return None
                op = cs.load_uint(32)
                if op == 0:
                    return cs.load_snake_string()
            except Exception:
                pass
        return None

    @staticmethod
    def _decode_body_op(msg_data: dict) -> Optional[int]:
        """Read the first 32-bit opcode from a raw message body."""
        if not msg_data or msg_data.get("@type") != "msg.dataRaw":
            return None
        body_b64 = msg_data.get("body", "")
        if not body_b64:
            return None
        try:
            cell = PCell.one_from_boc(base64.b64decode(body_b64))
            cs = cell.begin_parse()
            if cs.remaining_bits < 32:
                return None
            return cs.load_uint(32)
        except Exception:
            return None

    @classmethod
    def _parse_jetton_body(cls, msg_data: dict) -> Optional[dict]:
        """Try to decode a Jetton transfer / notification body. Returns parsed fields or None."""
        if not msg_data or msg_data.get("@type") != "msg.dataRaw":
            return None
        body_b64 = msg_data.get("body", "")
        if not body_b64:
            return None
        try:
            cell = PCell.one_from_boc(base64.b64decode(body_b64))
            cs = cell.begin_parse()
            if cs.remaining_bits < 32:
                return None
            op = cs.load_uint(32)
            op_name = cls._JETTON_OPCODES.get(op)
            if not op_name:
                return None

            result: Dict[str, Any] = {"op": hex(op), "op_name": op_name}

            # jetton_transfer (0x0F8A7EA5)
            if op == 0x0F8A7EA5 and cs.remaining_bits >= 64:
                query_id = cs.load_uint(64)
                amount = cs.load_coins()
                destination = cs.load_address()
                response_dest = cs.load_address()
                result.update({
                    "query_id": query_id,
                    "jetton_amount": amount,
                    "destination": destination.to_str(True, True) if destination else None,
                    "response_destination": response_dest.to_str(True, True) if response_dest else None,
                })
                return result

            # jetton_transfer_notification (0x7362D09C)
            if op == 0x7362D09C and cs.remaining_bits >= 64:
                query_id = cs.load_uint(64)
                amount = cs.load_coins()
                sender = cs.load_address()
                result.update({
                    "query_id": query_id,
                    "jetton_amount": amount,
                    "sender": sender.to_str(True, True) if sender else None,
                })
                # try to read forward comment
                try:
                    if cs.remaining_bits >= 1:
                        has_fwd = cs.load_bit()
                        if has_fwd and cs.remaining_refs:
                            fwd_cell = cs.load_ref()
                            fwd_cs = fwd_cell.begin_parse()
                            if fwd_cs.remaining_bits >= 32:
                                fwd_op = fwd_cs.load_uint(32)
                                if fwd_op == 0:
                                    result["forward_comment"] = fwd_cs.load_snake_string()
                except Exception:
                    pass
                return result

            # jetton_internal_transfer (0x178D4519)
            if op == 0x178D4519 and cs.remaining_bits >= 64:
                query_id = cs.load_uint(64)
                amount = cs.load_coins()
                sender = cs.load_address()
                result.update({
                    "query_id": query_id,
                    "jetton_amount": amount,
                    "from": sender.to_str(True, True) if sender else None,
                })
                return result

            # jetton_burn (0x595F07BC)
            if op == 0x595F07BC and cs.remaining_bits >= 64:
                query_id = cs.load_uint(64)
                amount = cs.load_coins()
                result.update({
                    "query_id": query_id,
                    "jetton_amount": amount,
                })
                return result

            # For other known opcodes just return the name
            return result

        except Exception:
            return None

    @staticmethod
    def _parse_message(msg: dict) -> dict:
        """Parse a single in_msg / out_msg into a clean dict."""
        if not msg:
            return {}
        value_nano = int(msg.get("value", 0) or 0)
        fwd_fee = int(msg.get("fwd_fee", 0) or 0)
        ihr_fee = int(msg.get("ihr_fee", 0) or 0)
        return {
            "source": msg.get("source", ""),
            "destination": msg.get("destination", ""),
            "value": value_nano,
            "value_ton": value_nano / NANOTON,
            "fwd_fee": fwd_fee,
            "ihr_fee": ihr_fee,
            "created_lt": msg.get("created_lt", ""),
            "body_hash": msg.get("body_hash", ""),
            "msg_data_type": (msg.get("msg_data") or {}).get("@type", ""),
        }

    @classmethod
    async def parse_transaction(cls, raw_tx: dict, get_price:bool = False, price:float =None) -> dict:
        """
        Parse a single raw TON transaction (as returned by TonCenter ``getTransactions``)
        into a human-readable dict.

        Detects:
          - native TON transfers
          - Jetton transfers / notifications / burns
          - NFT transfers
          - contract interactions (by opcode)
          - text comments

        Args:
            raw_tx: A single transaction dict from TonCenter API v2.

        Returns:
            dict with parsed transaction details.
        """
        tx_id = raw_tx.get("transaction_id", {})
        utime = raw_tx.get("utime", 0)

        # ---- fees ----
        total_fee = int(raw_tx.get("fee", 0) or 0)
        storage_fee = int(raw_tx.get("storage_fee", 0) or 0)
        other_fee = int(raw_tx.get("other_fee", 0) or 0)

        # ---- in_msg ----
        in_msg_raw = raw_tx.get("in_msg") or {}
        in_msg = cls._parse_message(in_msg_raw)
        in_msg_data = in_msg_raw.get("msg_data", {})

        # ---- out_msgs ----
        out_msgs_raw = raw_tx.get("out_msgs", []) or []
        out_msgs = [cls._parse_message(m) for m in out_msgs_raw]

        # ---- comment ----
        comment = cls._decode_comment(in_msg_data)

        # ---- opcode & jetton parsing ----
        in_op = cls._decode_body_op(in_msg_data)
        jetton_info = cls._parse_jetton_body(in_msg_data)

        # ---- determine tx category ----
        if in_op is not None and in_op in cls._JETTON_OPCODES:
            tx_category = cls._JETTON_OPCODES[in_op]
        elif in_op is not None and in_op != 0:
            tx_category = "contract_call"
        elif not in_msg.get("source"):
            tx_category = "external"
        elif in_msg.get("value_ton", 0) > 0 and (in_op is None or in_op == 0):
            tx_category = "native_transfer"
        else:
            tx_category = "other"

        # ---- total outgoing value ----
        total_out_nano = sum(m.get("value", 0) for m in out_msgs)

        result: Dict[str, Any] = {
            "tx_hash": tx_id.get("hash", ""),
            "lt": tx_id.get("lt", ""),
            "timestamp": utime,
            "datetime_utc": (
                datetime.fromtimestamp(utime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                if utime else None
            ),

            "fee": total_fee,
            "fee_ton": total_fee / NANOTON,
            "storage_fee": storage_fee,
            "other_fee": other_fee,

            "tx_category": tx_category,
            "opcode": hex(in_op) if in_op is not None else None,

            "in_msg": in_msg,
            "out_msgs": out_msgs,
            "out_msgs_count": len(out_msgs),
            "total_out_value": total_out_nano,
            "total_out_value_ton": total_out_nano / NANOTON,

            "comment": comment,
        }

        if jetton_info:
            result["jetton"] = jetton_info
        if get_price:
            from OrbisPaySDK.utils import utils as ut
            import asyncio 
            _cog = ut.CoinGecko()
            price = await _cog.get_price(coigeco_id)
            if price != 0.0:
                fee_in_usd = price * result["fee_ton"]
                total_in_usd = price * result["total_out_value_ton"]
                result["fee_in_usd"] = str(fee_in_usd)+"$"
                result["total_out_value_usd"] = str(total_in_usd)+"$"
        if price:
                fee_in_usd = price * result["fee_ton"]
                total_in_usd = price * result["total_out_value_ton"]
                result["fee_in_usd"] = str(fee_in_usd)+"$"
                result["total_out_value_usd"] = str(total_in_usd)+"$"

        return result

    async def get_and_parse_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 10,
        get_price:bool = False,
        price:float = None
    ) -> List[dict]:
        """
        Fetch recent transactions for *address* and return them parsed.

        Args:
            address: TON address (defaults to current wallet).
            limit: Max number of transactions to fetch.

        Returns:
            List of parsed transaction dicts.
        """
        raw_txs = await self.get_transactions(address=address, limit=limit)
        return [await self.parse_transaction(raw_tx=tx, price = price) for tx in raw_txs]

    async def get_and_parse_transaction(
        self,
        tx_hash: str,
        address: Optional[str] = None,
        limit: int = 50,
    ) -> Optional[dict]:
        """
        Find a specific transaction by its hash among recent transactions
        for *address* and return it parsed.

        Args:
            tx_hash: Transaction hash to look for.
            address: TON address to search in (defaults to current wallet).
            limit: How many recent transactions to scan.

        Returns:
            Parsed transaction dict or None if not found.
        """
        raw_txs = await self.get_transactions(address=address, limit=limit)
        for tx in raw_txs:
            tid = tx.get("transaction_id", {})
            if tid.get("hash") == tx_hash:
                return self.parse_transaction(tx)
        return None
