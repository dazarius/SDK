import time
import hashlib
from typing import Optional, Dict, Any

from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

from OrbisPaySDK.interface.trx import TRX, SUN_PER_TRX


class TRXCheque:
    """
    Tron cheque operations for OrbisPaySDK.
    Manages cheque creation, claiming, and querying on the Tron blockchain.

    Similar to EVMcheque.py — uses a deployed Solidity smart contract on Tron.
    """

    def __init__(
        self,
        network: str = "mainnet",
        private_key: Optional[str] = None,
        provider_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        contract_abi: Optional[list] = None,
        api_key: Optional[str] = None,
        return_build_tx: bool = False,
    ):
        self.trx = TRX(
            network=network,
            private_key=private_key,
            provider_url=provider_url,
            api_key=api_key,
        )
        self.contract_address = contract_address
        self.contract_abi = contract_abi
        self.contract = None
        self.return_build_tx = return_build_tx

        if contract_address:
            self._load_contract()

    def _load_contract(self):
        """Load the cheque smart contract."""
        if self.contract_address:
            self.contract = self.trx.client.get_contract(self.contract_address)

    def set_params(
        self,
        network: Optional[str] = None,
        private_key: Optional[str] = None,
        provider_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        contract_abi: Optional[list] = None,
        api_key: Optional[str] = None,
    ):
        self.trx.set_params(
            network=network,
            private_key=private_key,
            provider_url=provider_url,
            api_key=api_key,
        )
        if contract_address:
            self.contract_address = contract_address
            self._load_contract()
        if contract_abi:
            self.contract_abi = contract_abi

    def _ensure_contract(self):
        if not self.contract:
            raise ValueError("Contract not set. Use set_params() with contract_address.")

    def _ensure_key(self):
        if not self.trx.private_key:
            raise ValueError("Private key not set.")

    def _resolve_key(self, private_key: Optional[str] = None) -> PrivateKey:
        return self.trx._resolve_key(private_key)

    async def InitCheque(
        self,
        amount: float,
        receiver: list,
        support_bps: int = 0,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Initialize a native TRX cheque.

        Args:
            amount: Amount in TRX.
            receiver: List of receiver addresses.
            support_bps: Support fee in basis points.
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash and cheque ID.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()
        amount_sun = int(amount * SUN_PER_TRX)

        txn = (
            self.contract.functions.InitCheque(receiver, support_bps)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .call_value(amount_sun)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "raw_result": result,
        }

    async def CashOutCheque(
        self,
        cheque_id: str,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Cash out (claim) a native TRX cheque.

        Args:
            cheque_id: Cheque ID (hex string).
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        txn = (
            self.contract.functions.CashOutCheque(cheque_bytes)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
        }

    async def InitTokenCheque(
        self,
        token_address: str,
        amount: int,
        receiver: str,
        support_bps: int = 0,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Initialize a TRC20 token cheque.

        Args:
            token_address: TRC20 token contract address.
            amount: Token amount (raw, with decimals applied).
            receiver: Receiver address.
            support_bps: Support fee in basis points.
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash and cheque ID.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        txn = (
            self.contract.functions.InitTokenCheque(
                token_address,
                amount,
                receiver,
                support_bps,
            )
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "raw_result": result,
        }

    async def CashOutTokenCheque(
        self,
        cheque_id: str,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Cash out a TRC20 token cheque.

        Args:
            cheque_id: Cheque ID (hex string).
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        txn = (
            self.contract.functions.CashOutTokenCheque(cheque_bytes)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
        }

    async def InitSwapCheque(
        self,
        token_in: str,
        amount_in: int,
        token_out: str,
        amount_out: int,
        receiver: str,
        support_bps: int = 0,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Initialize a swap cheque (token-to-token exchange).

        Args:
            token_in: Input token contract address.
            amount_in: Input amount (raw).
            token_out: Output token contract address.
            amount_out: Expected output amount (raw).
            receiver: Receiver address.
            support_bps: Support fee basis points.
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash and cheque ID.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        txn = (
            self.contract.functions.InitSwapCheque(
                receiver,
                token_in,
                amount_in,
                token_out,
                amount_out,
                support_bps,
            )
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
            "raw_result": result,
        }

    async def CashOutSwapCheque(
        self,
        cheque_id: str,
        private_key: Optional[str] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Cash out a swap cheque.

        Args:
            cheque_id: Cheque ID (hex string).
            private_key: Optional hex private key.
            fee_limit: Max energy cost in sun.

        Returns:
            dict with tx hash.
        """
        self._ensure_contract()
        key = self._resolve_key(private_key)
        from_addr = key.public_key.to_base58check_address()

        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        txn = (
            self.contract.functions.CashOutSwapCheque(cheque_bytes)
            .with_owner(from_addr)
            .fee_limit(fee_limit)
            .build()
        )

        if self.return_build_tx:
            return {"build_tx": txn}

        signed = txn.sign(key)
        result = signed.broadcast()

        return {
            "hash": result.get("txid", ""),
            "status": "success" if result.get("result", False) else "failed",
        }

    async def getChequeInfo(self, cheque_id: str) -> dict:
        """Get cheque info from contract."""
        self._ensure_contract()
        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        info = self.contract.functions.getChequeInfo(cheque_bytes)
        return {
            "sender": info[0],
            "receiver": info[1],
            "status": "claimed" if info[2] else "unclaimed",
        }

    async def getTokenChequeDetail(self, cheque_id: str) -> dict:
        """Get token cheque details from contract."""
        self._ensure_contract()
        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        info = self.contract.functions.getTokenChequeDetail(cheque_bytes)
        return {
            "sender": info[0],
            "token": info[1],
            "amount": info[2],
            "receivers": info[3],
            "status": info[4],
        }

    async def getSwapDetail(self, cheque_id: str) -> dict:
        """Get swap cheque details from contract."""
        self._ensure_contract()
        cheque_bytes = bytes.fromhex(cheque_id) if not cheque_id.startswith("0x") else bytes.fromhex(cheque_id[2:])
        cheque_bytes = cheque_bytes.rjust(32, b'\x00')

        s = self.contract.functions.getSwapDetail(cheque_bytes)
        return {
            "tokenIn": s[0],
            "amountIn": s[1],
            "tokenOut": s[2],
            "amountOut": s[3],
            "spender": s[4],
            "receiver": s[5],
            "status": "claimed" if s[6] else "unclaimed",
        }
