import asyncio
import httpx
import time
import hashlib
from typing import Optional, List, Dict, Any

from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.utils import to_nano, from_nano, bytes_to_b64str, Address
from tonsdk.boc import Cell
from pytoniq_core import begin_cell as pbegin_cell, Address as PAddress

from OrbisPaySDK.interface.ton import TON
import OrbisPaySDK.const as sdk_const


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
        build_tx: bool = False,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.contract_address = contract_address
        self.wallet_version = wallet_version
        self.build_tx = build_tx

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
        build_tx: Optional[bool] = None,
    ):
        if contract_address:
            self.contract_address = contract_address
        if build_tx is not None:
            self.build_tx = build_tx
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
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
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

        if self.build_tx:
            return boc

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
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
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

        gas_amount = to_nano(0.05, "ton")

        query = self.ton.wallet.create_transfer_message(
            to_addr=self.contract_address,
            amount=gas_amount,
            seqno=seqno,
            payload=body,
        )

        boc = bytes_to_b64str(query["message"].to_boc(False))

        if self.build_tx:
            return boc

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
        amount: int,
        recipient: str,
        jetton_wallet_address: Optional[str] = None,
        token_master: Optional[str] = None,
    ) -> dict:
        """
        Initialize a Jetton (token) cheque.

        Pass either jetton_wallet_address (sender's Jetton wallet) or token_master
        (Jetton master contract address — wallet is resolved automatically).

        Args:
            amount: Amount of Jettons (raw, with decimals applied).
            recipient: Recipient TON address.
            jetton_wallet_address: Sender's Jetton wallet address.
            token_master: Jetton master contract address. Auto-resolves sender's wallet.

        Returns:
            dict with cheque info and tx result.
        """
        self._ensure_contract()
        self._ensure_wallet()

        sender = self.ton.get_address()

        if jetton_wallet_address is None and token_master is None:
            raise ValueError("Provide either jetton_wallet_address or token_master")
        if jetton_wallet_address is None:
            jetton_wallet_address = await self.ton.get_jetton_wallet_address(
                jetton_master=token_master, owner=sender
            )
            if jetton_wallet_address is None:
                raise ValueError(f"Could not resolve Jetton wallet for master {token_master}")
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
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
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

        if self.build_tx:
            return boc

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
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
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

        if self.build_tx:
            return boc

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

    async def get_contract_jetton_wallet(self, token_master: str) -> str:
        """
        Returns the contract's Jetton wallet address for a given token master.

        Pass the result as `contract_jetton_wallet_out` when calling init_swap_cheque
        so the contract knows which Jetton wallet to expect token_out deposits from.

        Args:
            token_master: Jetton master contract address of the token.

        Returns:
            str: Contract's Jetton wallet address for that token.
        """
        self._ensure_contract()
        result = await self.ton.get_jetton_wallet_address(
            jetton_master=token_master,
            owner=self.contract_address,
        )
        if result is None:
            raise ValueError(f"Could not resolve contract Jetton wallet for master {token_master}")
        return result

    async def init_swap_cheque(
        self,
        cheque_id: int,
        amount_in: int,
        amount_out: int,
        recipient: str,
        jetton_wallet_in: Optional[str] = None,
        token_master_in: Optional[str] = None,
        contract_jetton_wallet_out: Optional[str] = None,
        token_master_out: Optional[str] = None,
        user_bps: int = 0,
        ttl: int = 0,
    ) -> dict:
        """
        Create a swap cheque (User A — spender side).

        User A locks token_in in the contract. User B (recipient) must call
        claim_swap_cheque and deposit token_out to complete the exchange.

        Pass either the resolved wallet addresses or the master contract addresses
        — wallets are resolved automatically when masters are provided.

        Args:
            cheque_id: Unique uint64 cheque identifier (caller-supplied).
            amount_in: Raw amount of token_in to lock (with decimals).
            amount_out: Raw amount of token_out User A expects to receive.
            recipient: TON address of User B (the swap counterparty).
            jetton_wallet_in: User A's Jetton wallet for token_in (or use token_master_in).
            token_master_in: Jetton master of token_in — auto-resolves sender's wallet.
            contract_jetton_wallet_out: Contract's Jetton wallet for token_out (or use token_master_out).
            token_master_out: Jetton master of token_out — auto-resolves contract's wallet.
            user_bps: Fee in basis points (0 = use contract default).
            ttl: Cheque lifetime in seconds (0 = 30 days).
        """
        self._ensure_contract()
        self._ensure_wallet()

        sender = self.ton.get_address()

        if jetton_wallet_in is None and token_master_in is None:
            raise ValueError("Provide either jetton_wallet_in or token_master_in")
        if contract_jetton_wallet_out is None and token_master_out is None:
            raise ValueError("Provide either contract_jetton_wallet_out or token_master_out")

        if jetton_wallet_in is None:
            jetton_wallet_in = await self.ton.get_jetton_wallet_address(
                jetton_master=token_master_in, owner=sender
            )
            if jetton_wallet_in is None:
                raise ValueError(f"Could not resolve Jetton wallet for master {token_master_in}")

        if contract_jetton_wallet_out is None:
            contract_jetton_wallet_out = await self.ton.get_jetton_wallet_address(
                jetton_master=token_master_out, owner=self.contract_address
            )
            if contract_jetton_wallet_out is None:
                raise ValueError(f"Could not resolve contract Jetton wallet for master {token_master_out}")

        if self.ton.wallet_version == "wr5":
            forward_body = (
                pbegin_cell()
                .store_uint(0x02, 32)
                .store_uint(cheque_id, 64)
                .store_address(PAddress(recipient))
                .store_address(PAddress(contract_jetton_wallet_out))
                .store_coins(amount_out)
                .store_uint(user_bps, 32)
                .store_uint(ttl, 32)
                .end_cell()
            )
            body = (
                pbegin_cell()
                .store_uint(0x0F8A7EA5, 32)
                .store_uint(0, 64)
                .store_coins(amount_in)
                .store_address(PAddress(self.contract_address))
                .store_address(PAddress(sender))
                .store_bit(0)
                .store_coins(to_nano(0.01, "ton"))
                .store_bit(1)
                .store_ref(forward_body)
                .end_cell()
            )
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=jetton_wallet_in,
                amount=0.1,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "amount_in": amount_in,
                "amount_out": amount_out,
                "recipient": recipient,
                "sender": sender,
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        forward_body = Cell()
        forward_body.bits.write_uint(0x02, 32)
        forward_body.bits.write_uint(cheque_id, 64)
        forward_body.bits.write_address(Address(recipient))
        forward_body.bits.write_address(Address(contract_jetton_wallet_out))
        forward_body.bits.write_grams(amount_out)
        forward_body.bits.write_uint(user_bps, 32)
        forward_body.bits.write_uint(ttl, 32)

        body = Cell()
        body.bits.write_uint(0x0F8A7EA5, 32)
        body.bits.write_uint(0, 64)
        body.bits.write_grams(amount_in)
        body.bits.write_address(Address(self.contract_address))
        body.bits.write_address(Address(sender))
        body.bits.write_bit(0)
        body.bits.write_grams(to_nano(0.01, "ton"))
        body.bits.write_bit(1)
        body.refs.append(forward_body)

        seqno = await self.ton.get_seqno()
        query = self.ton.wallet.create_transfer_message(
            to_addr=jetton_wallet_in,
            amount=to_nano(0.1, "ton"),
            seqno=seqno,
            payload=body,
        )
        boc = bytes_to_b64str(query["message"].to_boc(False))

        if self.build_tx:
            return boc

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
                    "amount_in": amount_in,
                    "amount_out": amount_out,
                    "recipient": recipient,
                    "sender": sender,
                    "result": data["result"],
                }
            raise ValueError(f"Init swap cheque failed: {data}")

    async def claim_swap_cheque(
        self,
        cheque_id: int,
        amount_out: int,
        jetton_wallet_out: Optional[str] = None,
        token_master_out: Optional[str] = None,
    ) -> dict:
        """
        Complete a swap cheque (User B — receiver side).

        User B deposits token_out into the contract. The contract releases
        token_in to User B and token_out to User A.

        Args:
            cheque_id: The swap cheque identifier.
            amount_out: Raw amount of token_out to deposit (must match cheque).
            jetton_wallet_out: User B's own Jetton wallet for token_out (or use token_master_out).
            token_master_out: Jetton master of token_out — auto-resolves sender's wallet.
        """
        self._ensure_contract()
        self._ensure_wallet()

        sender = self.ton.get_address()

        if jetton_wallet_out is None and token_master_out is None:
            raise ValueError("Provide either jetton_wallet_out or token_master_out")
        if jetton_wallet_out is None:
            jetton_wallet_out = await self.ton.get_jetton_wallet_address(
                jetton_master=token_master_out, owner=sender
            )
            if jetton_wallet_out is None:
                raise ValueError(f"Could not resolve Jetton wallet for master {token_master_out}")

        if self.ton.wallet_version == "wr5":
            forward_body = (
                pbegin_cell()
                .store_uint(0x03, 32)
                .store_uint(cheque_id, 64)
                .end_cell()
            )
            body = (
                pbegin_cell()
                .store_uint(0x0F8A7EA5, 32)
                .store_uint(0, 64)
                .store_coins(amount_out)
                .store_address(PAddress(self.contract_address))
                .store_address(PAddress(sender))
                .store_bit(0)
                .store_coins(to_nano(0.01, "ton"))
                .store_bit(1)
                .store_ref(forward_body)
                .end_cell()
            )
            if self.build_tx:
                import base64 as _b64
                return _b64.b64encode(body.to_boc()).decode()
            tx_hash = await self.ton._v5_wallet.transfer(
                destination=jetton_wallet_out,
                amount=0.1,
                body=body,
            )
            return {
                "cheque_id": cheque_id,
                "status": "swap_completed",
                "tx_hash": tx_hash,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        forward_body = Cell()
        forward_body.bits.write_uint(0x03, 32)
        forward_body.bits.write_uint(cheque_id, 64)

        body = Cell()
        body.bits.write_uint(0x0F8A7EA5, 32)
        body.bits.write_uint(0, 64)
        body.bits.write_grams(amount_out)
        body.bits.write_address(Address(self.contract_address))
        body.bits.write_address(Address(sender))
        body.bits.write_bit(0)
        body.bits.write_grams(to_nano(0.01, "ton"))
        body.bits.write_bit(1)
        body.refs.append(forward_body)

        seqno = await self.ton.get_seqno()
        query = self.ton.wallet.create_transfer_message(
            to_addr=jetton_wallet_out,
            amount=to_nano(0.1, "ton"),
            seqno=seqno,
            payload=body,
        )
        boc = bytes_to_b64str(query["message"].to_boc(False))

        if self.build_tx:
            return boc

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
                    "status": "swap_completed",
                    "result": data["result"],
                }
            raise ValueError(f"Claim swap cheque failed: {data}")

    async def get_swap_cheque(self, cheque_id: int) -> dict:
        """
        Get full info about a swap cheque (core + wallets).

        Returns:
            dict with spender, receiver, amountIn, amountOut, claimed,
            expiresAt, jettonWalletIn, jettonWalletOut fields.
        """
        self._ensure_contract()

        async with httpx.AsyncClient() as client:
            headers = self.ton._get_headers()
            base = {"address": self.contract_address, "stack": [["num", cheque_id]]}

            core_resp, wallets_resp = await asyncio.gather(
                client.post(f"{self.api_url}/runGetMethod",
                            json={**base, "method": "swapChequeCore"}, headers=headers),
                client.post(f"{self.api_url}/runGetMethod",
                            json={**base, "method": "swapChequeWallets"}, headers=headers),
            )

        core = core_resp.json()
        wallets = wallets_resp.json()
        if not core.get("ok"):
            raise ValueError(f"Failed to get swap cheque core: {core}")
        if not wallets.get("ok"):
            raise ValueError(f"Failed to get swap cheque wallets: {wallets}")

        return {
            "core": core["result"],
            "wallets": wallets["result"],
        }

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
