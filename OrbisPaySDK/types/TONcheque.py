import httpx
import time
import hashlib
from typing import Optional, List, Dict, Any

from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.utils import to_nano, from_nano, bytes_to_b64str, Address
from tonsdk.boc import Cell
from pytoniq_core import begin_cell as pbegin_cell, Address as PAddress

from OrbisPaySDK.interface.ton import TON

NANOTON = 1_000_000_000


class TONCheque:
    """
    TON cheque operations for OrbisPaySDK.
    Manages cheque creation, claiming, and parsing on the TON blockchain.

    NOTE: Requires a deployed OrbisPaySDK smart contract on TON.
    Set the contract address via set_params() or constructor.
    """

    def __init__(
        self,
        api_url: str = "https://toncenter.com/api/v2",
        api_key: Optional[str] = None,
        mnemonics: Optional[List[str]] = None,
        wallet_version: str = "v4r2",
        contract_address: Optional[str] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.contract_address = contract_address
        self.wallet_version = wallet_version

        self.ton = TON(
            api_url=api_url,
            api_key=api_key,
            mnemonics=mnemonics,
            wallet_version=wallet_version,
        )

    def set_params(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mnemonics: Optional[List[str]] = None,
        wallet_version: Optional[str] = None,
        contract_address: Optional[str] = None,
    ):
        if contract_address:
            self.contract_address = contract_address
        self.ton.set_params(
            api_url=api_url,
            api_key=api_key,
            mnemonics=mnemonics,
            wallet_version=wallet_version,
        )

    def _ensure_contract(self):
        if not self.contract_address:
            raise ValueError("Contract address not set. Use set_params() to set it.")

    def _ensure_wallet(self):
        if not self.ton.wallet:
            raise ValueError("Wallet not set. Provide mnemonics via set_params().")

    @staticmethod
    def _generate_cheque_id(sender: str, recipient: str, amount: int) -> str:
        """Generate unique cheque ID based on sender, recipient, amount, and timestamp."""
        raw = f"{sender}:{recipient}:{amount}:{time.time()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    async def init_cheque(
        self,
        amount: float,
        recipient: str,
        memo: Optional[str] = None,
    ) -> dict:
        """
        Initialize a native TON cheque.

        Args:
            amount: Amount in TON.
            recipient: Recipient TON address.
            memo: Optional message.

        Returns:
            dict with cheque info and tx result.
        """
        self._ensure_contract()
        self._ensure_wallet()

        sender = self.ton.get_address()
        nano_amount = to_nano(amount, "ton")
        cheque_id = self._generate_cheque_id(sender, recipient, nano_amount)

        if self.ton.wallet_version == "wr5":
            body = (
                pbegin_cell()
                .store_uint(0x01, 32)                    # op: init_cheque
                .store_uint(0, 64)                        # query_id
                .store_coins(nano_amount)                 # amount
                .store_address(PAddress(recipient))       # recipient
                .end_cell()
            )
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=self.contract_address,
                amount=amount,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "amount": amount,
                "recipient": recipient,
                "sender": sender,
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        body = Cell()
        body.bits.write_uint(0x01, 32)             # op: init_cheque
        body.bits.write_uint(0, 64)                  # query_id
        body.bits.write_grams(nano_amount)           # amount
        body.bits.write_address(Address(recipient))  # recipient

        seqno = await self.ton.get_seqno()

        query = self.ton.wallet.create_transfer_message(
            to_addr=self.contract_address,
            amount=nano_amount,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self.ton._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "cheque_id": cheque_id,
                    "amount": amount,
                    "recipient": recipient,
                    "sender": sender,
                    "result": data["result"],
                }
            raise ValueError(f"Init cheque failed: {data}")

    async def claim_cheque(self, cheque_id: str) -> dict:
        """
        Claim (cash out) a native TON cheque.

        Args:
            cheque_id: The cheque identifier.

        Returns:
            dict with claim result.
        """
        self._ensure_contract()
        self._ensure_wallet()

        if self.ton.wallet_version == "wr5":
            body = (
                pbegin_cell()
                .store_uint(0x02, 32)                         # op: claim_cheque
                .store_uint(0, 64)                             # query_id
                .store_bytes(bytes.fromhex(cheque_id))         # cheque_id
                .end_cell()
            )
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=self.contract_address,
                amount=0.05,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "status": "claimed",
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        body = Cell()
        body.bits.write_uint(0x02, 32)  # op: claim_cheque
        body.bits.write_uint(0, 64)      # query_id
        body.bits.write_bytes(bytes.fromhex(cheque_id))  # cheque_id

        seqno = await self.ton.get_seqno()

        # Small amount of TON for gas
        gas_amount = to_nano(0.05, "ton")

        query = self.ton.wallet.create_transfer_message(
            to_addr=self.contract_address,
            amount=gas_amount,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self.ton._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "cheque_id": cheque_id,
                    "status": "claimed",
                    "result": data["result"],
                }
            raise ValueError(f"Claim cheque failed: {data}")

    async def init_jetton_cheque(
        self,
        jetton_wallet_address: str,
        amount: int,
        recipient: str,
    ) -> dict:
        """
        Initialize a Jetton (token) cheque.

        Args:
            jetton_wallet_address: Sender's Jetton wallet address.
            amount: Amount of Jettons (raw, with decimals applied).
            recipient: Recipient TON address.

        Returns:
            dict with cheque info and tx result.
        """
        self._ensure_contract()
        self._ensure_wallet()

        sender = self.ton.get_address()
        cheque_id = self._generate_cheque_id(sender, recipient, amount)

        if self.ton.wallet_version == "wr5":
            forward_body = (
                pbegin_cell()
                .store_uint(0x03, 32)                             # op: init_jetton_cheque
                .store_uint(0, 64)                                 # query_id
                .store_address(PAddress(recipient))                # recipient
                .end_cell()
            )
            body = (
                pbegin_cell()
                .store_uint(0x0F8A7EA5, 32)                       # op::transfer
                .store_uint(0, 64)                                  # query_id
                .store_coins(amount)                                # jetton amount
                .store_address(PAddress(self.contract_address))    # destination (contract)
                .store_address(PAddress(sender))                   # response_destination
                .store_bit(0)                                       # no custom_payload
                .store_coins(to_nano(0.01, "ton"))                 # forward_ton_amount
                .store_bit(1)                                       # forward_payload in ref
                .store_ref(forward_body)
                .end_cell()
            )
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=jetton_wallet_address,
                amount=0.1,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "amount": amount,
                "recipient": recipient,
                "sender": sender,
                "jetton_wallet": jetton_wallet_address,
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        forward_body = Cell()
        forward_body.bits.write_uint(0x03, 32)             # op: init_jetton_cheque
        forward_body.bits.write_uint(0, 64)                  # query_id
        forward_body.bits.write_address(Address(recipient))  # recipient

        body = Cell()
        body.bits.write_uint(0x0F8A7EA5, 32)                      # op::transfer
        body.bits.write_uint(0, 64)                                 # query_id
        body.bits.write_grams(amount)                               # jetton amount
        body.bits.write_address(Address(self.contract_address))     # destination (contract)
        body.bits.write_address(Address(sender))                    # response_destination
        body.bits.write_bit(0)                                      # no custom_payload
        body.bits.write_grams(to_nano(0.01, "ton"))                # forward_ton_amount
        body.bits.write_bit(1)                                      # forward_payload in ref
        body.refs.append(forward_body)

        seqno = await self.ton.get_seqno()
        gas_amount = to_nano(0.1, "ton")

        query = self.ton.wallet.create_transfer_message(
            to_addr=jetton_wallet_address,
            amount=gas_amount,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self.ton._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "cheque_id": cheque_id,
                    "amount": amount,
                    "recipient": recipient,
                    "sender": sender,
                    "jetton_wallet": jetton_wallet_address,
                    "result": data["result"],
                }
            raise ValueError(f"Init jetton cheque failed: {data}")

    async def claim_jetton_cheque(self, cheque_id: str) -> dict:
        """
        Claim a Jetton (token) cheque.

        Args:
            cheque_id: The cheque identifier.

        Returns:
            dict with claim result.
        """
        self._ensure_contract()
        self._ensure_wallet()

        if self.ton.wallet_version == "wr5":
            body = (
                pbegin_cell()
                .store_uint(0x04, 32)                         # op: claim_jetton_cheque
                .store_uint(0, 64)                             # query_id
                .store_bytes(bytes.fromhex(cheque_id))         # cheque_id
                .end_cell()
            )
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=self.contract_address,
                amount=0.05,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "status": "claimed",
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        body = Cell()
        body.bits.write_uint(0x04, 32)  # op: claim_jetton_cheque
        body.bits.write_uint(0, 64)      # query_id
        body.bits.write_bytes(bytes.fromhex(cheque_id))

        seqno = await self.ton.get_seqno()
        gas_amount = to_nano(0.05, "ton")

        query = self.ton.wallet.create_transfer_message(
            to_addr=self.contract_address,
            amount=gas_amount,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self.ton._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "cheque_id": cheque_id,
                    "status": "claimed",
                    "result": data["result"],
                }
            raise ValueError(f"Claim jetton cheque failed: {data}")

    async def get_cheque_info(self, cheque_id: str) -> dict:
        """
        Get information about a cheque from the contract.

        Args:
            cheque_id: The cheque identifier.

        Returns:
            dict with cheque data.
        """
        self._ensure_contract()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/runGetMethod",
                json={
                    "address": self.contract_address,
                    "method": "get_cheque_info",
                    "stack": [["num", "0x" + cheque_id]],
                },
                headers=self.ton._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return data["result"]
            raise ValueError(f"Failed to get cheque info: {data}")
