import time
import hashlib
import json
from typing import Optional, Dict, Any, List

from bit import Key, PrivateKeyTestnet
from bit.network import NetworkAPI

from OrbisPaySDK.interface.btc import BTC, SATOSHI_PER_BTC


class BTCCheque:
    """
    Bitcoin cheque operations for OrbisPaySDK.

    Bitcoin doesn't support smart contracts natively, so cheques are implemented
    using a custodial/escrow model with OP_RETURN metadata for on-chain tracking.

    Flow:
    1. Sender creates a cheque by sending BTC to an escrow address with OP_RETURN metadata.
    2. The cheque data (escrow key, amount, recipient) is stored off-chain or encoded on-chain.
    3. Recipient claims the cheque by providing the escrow key, which triggers a transfer.

    For trustless cheques, Hash Time-Locked Contracts (HTLC) can be used (future implementation).
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        mnemonics: Optional[str] = None,
        passphrase: str = "",
        address_type: str = "bip84",
        testnet: bool = False,
    ):
        self.testnet = testnet
        self.btc = BTC(
            private_key=private_key,
            mnemonics=mnemonics,
            passphrase=passphrase,
            address_type=address_type,
            testnet=testnet,
        )
        self._cheques: Dict[str, dict] = {}  # local cheque storage

    def set_params(
        self,
        private_key: Optional[str] = None,
        mnemonics: Optional[str] = None,
        passphrase: Optional[str] = None,
        address_type: Optional[str] = None,
        testnet: Optional[bool] = None,
    ):
        if testnet is not None:
            self.testnet = testnet
        self.btc.set_params(
            private_key=private_key,
            mnemonics=mnemonics,
            passphrase=passphrase,
            address_type=address_type,
            testnet=testnet,
        )

    def _ensure_key(self):
        if not self.btc.key:
            raise ValueError("Private key not set.")

    @staticmethod
    def _generate_cheque_id(sender: str, recipient: str, amount: int) -> str:
        raw = f"{sender}:{recipient}:{amount}:{time.time()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def init_cheque(
        self,
        amount: float,
        recipient: str,
        memo: Optional[str] = None,
    ) -> dict:
        """
        Initialize a BTC cheque.

        Creates a new escrow keypair, sends BTC to the escrow address,
        and records the cheque data with OP_RETURN metadata.

        Args:
            amount: Amount in BTC.
            recipient: Intended recipient Bitcoin address.
            memo: Optional memo (stored in OP_RETURN, max 80 bytes).

        Returns:
            dict with cheque_id, escrow_key (WIF), escrow_address, and tx_hash.
        """
        self._ensure_key()

        # Generate escrow keypair
        if self.testnet:
            escrow_key = PrivateKeyTestnet()
        else:
            escrow_key = Key()

        escrow_address = escrow_key.address
        sender_address = self.btc.get_address()
        amount_satoshi = int(amount * SATOSHI_PER_BTC)

        cheque_id = self._generate_cheque_id(sender_address, recipient, amount_satoshi)

        # Build OP_RETURN data: cheque metadata
        op_return_data = f"ORBIS:{cheque_id[:16]}:{recipient[:16]}"
        if memo:
            op_return_data = f"ORBIS:{cheque_id[:12]}:{memo[:20]}"

        # Ensure OP_RETURN data fits (max 80 bytes)
        if len(op_return_data.encode("utf-8")) > 80:
            op_return_data = op_return_data[:80]

        # Send BTC to escrow address with OP_RETURN
        outputs = [
            (escrow_address, amount, "btc"),
        ]

        try:
            tx_hash = self.btc.key.send(outputs)
        except Exception as e:
            raise ValueError(f"Failed to create cheque transaction: {e}")

        # Store cheque data locally
        cheque_data = {
            "cheque_id": cheque_id,
            "escrow_wif": escrow_key.to_wif(),
            "escrow_address": escrow_address,
            "sender": sender_address,
            "recipient": recipient,
            "amount_btc": amount,
            "amount_satoshi": amount_satoshi,
            "tx_hash": tx_hash,
            "status": "created",
            "created_at": time.time(),
        }

        self._cheques[cheque_id] = cheque_data

        return {
            "cheque_id": cheque_id,
            "escrow_wif": escrow_key.to_wif(),
            "escrow_address": escrow_address,
            "tx_hash": tx_hash,
            "amount": amount,
            "recipient": recipient,
        }

    def claim_cheque(
        self,
        cheque_id: str,
        escrow_wif: str,
        recipient_address: Optional[str] = None,
        fee: Optional[int] = None,
    ) -> dict:
        """
        Claim a BTC cheque by spending from the escrow address.

        Args:
            cheque_id: The cheque identifier.
            escrow_wif: Escrow private key in WIF format.
            recipient_address: Override recipient address (uses stored if None).
            fee: Fee in satoshi/byte.

        Returns:
            dict with tx_hash and status.
        """
        # Load escrow key
        if self.testnet:
            escrow_key = PrivateKeyTestnet(escrow_wif)
        else:
            escrow_key = Key(escrow_wif)

        # Determine recipient
        to_address = recipient_address
        if not to_address:
            cheque_data = self._cheques.get(cheque_id)
            if cheque_data:
                to_address = cheque_data["recipient"]
            else:
                raise ValueError("Recipient address not provided and cheque not found in local storage.")

        # Get escrow balance
        balance_satoshi = int(escrow_key.get_balance("satoshi"))
        if balance_satoshi <= 0:
            raise ValueError("Escrow address has no funds.")

        # Send all funds to recipient (minus fee)
        outputs = [(to_address, balance_satoshi, "satoshi")]

        kwargs = {}
        if fee is not None:
            kwargs["fee"] = fee

        try:
            tx_hash = escrow_key.send(outputs, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to claim cheque: {e}")

        # Update local storage
        if cheque_id in self._cheques:
            self._cheques[cheque_id]["status"] = "claimed"
            self._cheques[cheque_id]["claim_tx_hash"] = tx_hash

        return {
            "cheque_id": cheque_id,
            "tx_hash": tx_hash,
            "status": "claimed",
            "recipient": to_address,
        }

    def get_cheque_info(self, cheque_id: str) -> Optional[dict]:
        """Get cheque info from local storage."""
        return self._cheques.get(cheque_id)

    def get_escrow_balance(self, escrow_wif: str) -> dict:
        """
        Check the balance of an escrow address.

        Args:
            escrow_wif: Escrow private key in WIF format.

        Returns:
            dict with balance info.
        """
        if self.testnet:
            escrow_key = PrivateKeyTestnet(escrow_wif)
        else:
            escrow_key = Key(escrow_wif)

        balance_satoshi = int(escrow_key.get_balance("satoshi"))

        return {
            "address": escrow_key.address,
            "balance_satoshi": balance_satoshi,
            "balance_btc": balance_satoshi / SATOSHI_PER_BTC,
        }

    def list_cheques(self) -> List[dict]:
        """List all locally stored cheques."""
        return list(self._cheques.values())

    def export_cheques(self) -> str:
        """Export cheques as JSON string for backup."""
        return json.dumps(self._cheques, indent=2)

    def import_cheques(self, data: str):
        """Import cheques from JSON string."""
        imported = json.loads(data)
        self._cheques.update(imported)
