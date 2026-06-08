import asyncio
import httpx
import base64
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any, List

from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.utils import to_nano, from_nano, bytes_to_b64str, Address
from tonsdk.boc import Cell
from tonutils.contracts.wallet import WalletV5R1
from tonutils.clients.http.toncenter import ToncenterClient as ToncenterV3Client
from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key

from pytoniq_core import begin_cell as pbegin_cell, Address as PAddress
from pytoniq_core import Cell as PCell
from OrbisPaySDK.utils.utils import _Helper 

NANOTON = 1_000_000_000  # 1 TON = 1,000,000,000 nanotons
DECIMALS = 9
DEFAULT_VERSION = "v3r1" 
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
        "v2r1": WalletVersionEnum.v2r1,
        "v2r2": WalletVersionEnum.v2r2,
        "v3r1": WalletVersionEnum.v3r1,
        "v3r2": WalletVersionEnum.v3r2,
        "v4r1": WalletVersionEnum.v4r1,
        "v4r2": WalletVersionEnum.v4r2,
        "hv2":  WalletVersionEnum.hv2,
        "wr5":  "wr5",  # handled separately via tonutils WalletV5R1
    }

    def __init__(
        self,
        api_url: str = "https://toncenter.com/api/v2",
        api_key: Optional[str] = None,
        mnemonics: Optional[List[str]] = None,
        wallet_version: str = DEFAULT_VERSION,
        build_tx: bool = False,
    ):
        """
        Args:
            api_url        (str):       TonCenter API v2 base URL. Default: mainnet.
            api_key        (str):       TonCenter API key for higher rate limits. Optional.
            mnemonics      (list[str]): 24-word mnemonic phrase. If provided, wallet is loaded immediately.
            wallet_version (str):       Wallet contract version — 'v3r1', 'v3r2', 'v4r2', 'wr5'.
                                        Default: 'wr5' (WalletV5R1).
            build_tx       (bool):      If True, transfer_* methods return the BOC instead of broadcasting.
                                        Only supported for legacy wallet versions (v3r1, v3r2, v4r2).
        """
        # support embedded api_key in URL: https://toncenter.com/api/v2?api_key=xxx
        if api_key is None and api_url and "api_key=" in api_url:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(api_url)
            params = parse_qs(parsed.query)
            extracted = params.pop("api_key", [None])[0]
            clean_query = urlencode({k: v[0] for k, v in params.items()})
            api_url = urlunparse(parsed._replace(query=clean_query))
            api_key = extracted
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.build_tx = build_tx
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
        """
        Builds HTTP headers for TonCenter API requests.

        Returns:
            dict: Headers with Content-Type and optional X-API-Key.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def set_wallet(self, mnemonics: Union[str, List[str]], version: str = "v4r2"):
        """
        Loads a wallet from a mnemonic phrase and sets it as the active wallet.

        Args:
            mnemonics (str | list[str]): 24-word mnemonic — either a list or a space-separated string.
            version   (str):             Wallet contract version: 'v3r1', 'v3r2', 'v4r2', 'wr5'.
                                         'wr5' uses tonutils WalletV5R1; others use tonsdk Wallets.
        """
        if isinstance(mnemonics, str):
            mnemonics = mnemonics.split()
        self.mnemonics = mnemonics
        self.wallet_version = version

        if version == "wr5":
            from tonutils.clients.http.toncenter import NetworkGlobalID
            self._v5_client = ToncenterV3Client(NetworkGlobalID.MAINNET, api_key=self.api_key)
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
        mnemonics: Optional[Union[str, List[str]]] = None,
        wallet_version: Optional[str] = DEFAULT_VERSION,
        build_tx: Optional[bool] = None,
    ):
        """
        Updates instance parameters at runtime without recreating the object.

        Args:
            api_url        (str):             New TonCenter API base URL.
            api_key        (str):             New API key.
            mnemonics      (str | list[str]): New mnemonic — triggers set_wallet() if provided.
            wallet_version (str):             New wallet version to use when loading from mnemonics.
            build_tx       (bool):            New value for the build_tx flag.
        """
        if api_url:
            self.api_url = api_url.rstrip("/")
        if api_key:
            self.api_key = api_key
        if wallet_version:
            self.wallet_version = wallet_version
        if build_tx is not None:
            self.build_tx = build_tx
        if mnemonics:
            self.set_wallet(mnemonics, self.wallet_version)

    @staticmethod
    def gen_wallet(version: str = "wr5") -> dict:
        """
        Generates a new random TON wallet.

        Args:
            version (str): Wallet contract version: 'v3r1', 'v3r2', 'v4r2', 'wr5'. Default: 'wr5'.

        Returns:
            dict: {
                "mnemonics": str | list,   # 24-word mnemonic (string for legacy, list for wr5)
                "address":   str,          # user-friendly bounceable address
                "raw_address": str,        # raw workchain:hex address
                "WR5":       str,          # WalletV5R1 user-friendly address
                "key":       bytes,        # private key bytes (legacy versions only)
            }
        """
        client = ToncenterV3Client()
        version_map = {
            "v3r1": WalletVersionEnum.v3r1,
            "v3r2": WalletVersionEnum.v3r2,
            "v4r2": WalletVersionEnum.v4r2,
        }

        if version == "wr5":
            wallet_v5, pub_k, priv_k, mnemonics = WalletV5R1.create(client=client)
            return {
                "mnemonics": mnemonics,
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
        """
        Returns the active wallet address in user-friendly Base64url format.

        Args:
            bounceable (bool): If True, returns a bounceable address (default for smart contracts).
                               If False, returns a non-bounceable address (safer for plain wallets).

        Returns:
            str: User-friendly TON address string.

        Raises:
            ValueError: If no wallet has been loaded.
        """
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

    def get_all_addresses(self, bounceable: bool = True) -> dict:
        """
        Derives addresses for every supported wallet version from the current mnemonic.
        Useful for checking which version holds funds.

        Args:
            bounceable (bool): Address bounceable flag (see get_address).

        Returns:
            dict: { version_str: address_str | None }
                  None if derivation failed for a given version.

        Raises:
            ValueError: If no mnemonic has been set.
        """
        if not self.mnemonics:
            raise ValueError("Wallet not set. Use set_wallet() first.")
        result = {}
        for version in self.WALLET_VERSIONS:
            try:
                wv = self.WALLET_VERSIONS[version]
                if version == "wr5":
                    from tonutils.clients.http.toncenter import NetworkGlobalID
                    client = ToncenterV3Client(NetworkGlobalID.MAINNET, api_key=self.api_key)
                    wallet_v5, _, _, _ = WalletV5R1.from_mnemonic(client=client, mnemonic=self.mnemonics)
                    result[version] = wallet_v5.address.to_str(
                        is_user_friendly=True, is_url_safe=True, is_bounceable=bounceable
                    )
                else:
                    _, _, _, wallet = Wallets.from_mnemonics(
                        mnemonics=self.mnemonics, version=wv, workchain=0
                    )
                    result[version] = wallet.address.to_string(
                        is_user_friendly=True, is_url_safe=True, is_bounceable=bounceable
                    )
            except Exception:
                result[version] = None
        return result

    def sign_msg(self, msg: str) -> str:
        """
        Signs an arbitrary UTF-8 message with the wallet's Ed25519 private key.

        Args:
            msg (str): Message to sign.

        Returns:
            str: 64-byte Ed25519 signature as a hex string.

        Raises:
            ValueError: If no wallet / private key has been loaded.
        """
        if not self._priv_k:
            raise ValueError("Wallet not set")
        import nacl.signing
        signing_key = nacl.signing.SigningKey(self._priv_k)
        signed = signing_key.sign(msg.encode("utf-8"))
        return signed.signature.hex()

    async def get_balance(self, address: Optional[str] = None) -> dict:
        """
        Fetches the TON balance for an address.

        Args:
            address (str): TON address to query. Defaults to the active wallet address.

        Returns:
            dict: {
                "symbol":      "TON",
                "decimals":    9,
                "balance":     float,  # amount in TON
                "raw_balance": int,    # amount in nanotons
            }

        Raises:
            ValueError: If the RPC call fails.
        """
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
        Fetches TON balances for multiple addresses concurrently.

        Args:
            address_list (list[str]): List of TON address strings.

        Returns:
            dict: { address: {"symbol": "TON", "decimals": 9, "balance": float, "raw_balance": int} }
                  On error for a given address returns balance 0.0 / raw_balance 0.
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
        """
        Returns detailed wallet information from TonCenter getWalletInformation.

        Args:
            address (str): TON address to query. Defaults to the active wallet address.

        Returns:
            dict: Raw TonCenter result containing fields like balance, seqno,
                  wallet_type, account_state, last_transaction_id, etc.

        Raises:
            ValueError: If the RPC call fails.
        """
        if not address:
            address = self.get_address()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/getWalletInformation",
                params={"address": address},
                headers=self._get_headers(),
            )
            try:
                data = resp.json()
            except Exception:
                raise ValueError(f"TonCenter returned non-JSON (status {resp.status_code}). "
                                 f"Check api_key or rate limits. Body: {resp.text[:200]}")
            if data.get("ok"):
                return data["result"]
            raise ValueError(f"Failed to get wallet info: {data}")

    async def get_seqno(self, address: Optional[str] = None) -> int:
        """
        Returns the current sequence number (seqno) of the wallet.
        Required when building legacy transactions (v3/v4) to prevent replay attacks.

        Args:
            address (str): TON address to query. Defaults to the active wallet address.

        Returns:
            int: Current seqno. Returns 0 if not yet deployed.
        """
        info = await self.get_wallet_info(address)
        return info.get("seqno", 0)

    # ── Address helpers ────────────────────────────────────────────────────────

    _WALLET_TYPE_MAP: Dict[str, str] = {
        "wallet v1 r1": "v1r1",
        "wallet v1 r2": "v1r2",
        "wallet v1 r3": "v1r3",
        "wallet v2 r1": "v2r1",
        "wallet v2 r2": "v2r2",
        "wallet v3 r1": "v3r1",
        "wallet v3 r2": "v3r2",
        "wallet v4 r1": "v4r1",
        "wallet v4 r2": "v4r2",
        "wallet v5 r1": "wr5",
        "wallet v5beta r1": "wr5",
    }

    @staticmethod
    def normalize_address(address: str, bounceable: bool = True) -> str:
        """
        Converts any TON address format (raw workchain:hex or user-friendly base64url)
        to a canonical 48-character user-friendly string that tonsdk accepts.

        Args:
            address    (str):  Raw "0:abc..." or user-friendly "EQ..." / "UQ..." address.
            bounceable (bool): True → bounceable "EQ..." prefix, False → non-bounceable "UQ...".

        Returns:
            str: 48-character user-friendly TON address.

        Raises:
            ValueError: If the address cannot be parsed.
        """
        try:
            from tonsdk.utils import Address as _TonAddr
            addr = _TonAddr(address)
            return addr.to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=bounceable)
        except Exception as e:
            raise ValueError(f"Invalid TON address '{address}': {e}")

    def _normalize_address(self, address: str, bounceable: bool = True) -> str:
        """Instance alias for the static normalize_address."""
        return TON.normalize_address(address, bounceable)

    async def get_recipient_wallet_type(self, address: str) -> dict:
        """
        Queries TonCenter to detect the wallet contract type of any TON address.
        Useful for knowing which wallet version a recipient is using before sending.

        Args:
            address (str): Any valid TON address format (user-friendly or raw).

        Returns:
            dict: {
                "address":        str,          # as passed
                "wallet_type":    str | None,   # raw string from TonCenter e.g. "wallet v4 r2"
                "wallet_version": str | None,   # short SDK version string: "v4r2", "wr5", etc.
                "account_state":  str,          # "active", "uninitialized", or "frozen"
                "balance":        float,         # TON balance
                "balance_raw":    int,           # nanotons
                "seqno":          int | None,    # None if not deployed
            }

        Raises:
            ValueError: If the TonCenter call fails.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/getWalletInformation",
                params={"address": address},
                headers=self._get_headers(),
            )
            data = resp.json()
            if not data.get("ok"):
                raise ValueError(f"Failed to get wallet info for {address}: {data}")

            result = data["result"]
            wallet_type: Optional[str] = result.get("wallet_type")
            wallet_version = self._WALLET_TYPE_MAP.get(wallet_type.lower()) if wallet_type else None
            balance_nano = int(result.get("balance", 0) or 0)

            return {
                "address": address,
                "wallet_type": wallet_type,
                "wallet_version": wallet_version,
                "account_state": result.get("account_state", "uninitialized"),
                "balance": balance_nano / NANOTON,
                "balance_raw": balance_nano,
                "seqno": result.get("seqno"),
            }

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
            if self.build_tx:
                import base64 as _b64
                if memo:
                    body_cell = (
                        pbegin_cell()
                        .store_uint(0, 32)
                        .store_snake_string(memo)
                        .end_cell()
                    )
                    return {"tx": _b64.b64encode(body_cell.to_boc()).decode()}
                return {"tx": None}
            tx_hash = await self._v5_wallet.transfer(
                destination=to,
                amount=amount,
                body=memo,
            )
            return {
                "tx": tx_hash,
                "status": "sent",
                "amount": amount,
                "to": to,
            }

        # Legacy wallets (v3r1, v3r2, v4r2)
        seqno = await self.get_seqno()
        nano_amount = to_nano(amount, "ton")

        payload = memo if memo else None

        query = self.wallet.create_transfer_message(
            to_addr=to,
            amount=nano_amount,
            seqno=seqno,
            payload=payload,
        )

        boc_bytes = query["message"].to_boc(False)
        boc = bytes_to_b64str(boc_bytes)

        if self.build_tx:
            return {"tx": boc}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self._get_headers(),
            )
            data = resp.json()
            if not data.get("ok"):
                raise ValueError(f"Transfer failed: {data}")

        address = self.get_address()
        for _ in range(10):
            await asyncio.sleep(2)
            txs = await self.get_transactions(address=address, limit=5)
            if txs:
                tx_hash = txs[0].get("transaction_id", {}).get("hash")
                if tx_hash:
                    return {"tx": tx_hash}
        return {"tx": None}

    def _build_jetton_transfer_body(
        self,
        to: str,
        amount: int,
        response_address: str,
        forward_amount: int = 0,
        comment: Optional[str] = None,
    ) -> Cell:
        """
        Builds a Jetton transfer message body cell (TEP-74, op 0x0F8A7EA5) using tonsdk.
        Used for legacy wallet versions (v3r1, v3r2, v4r2).

        Args:
            to               (str): Recipient owner address (not their Jetton wallet).
            amount           (int): Jetton amount in the smallest unit (raw, decimals already applied).
            response_address (str): Address that receives the excess TON response.
            forward_amount   (int): Nanotons forwarded with the transfer notification. Default: 0.
            comment          (str): Optional text comment attached as forward payload.

        Returns:
            Cell: Serialised tonsdk Cell ready to attach as a transfer payload.
        """
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
        """
        Builds a Jetton transfer message body cell (TEP-74, op 0x0F8A7EA5) using pytoniq_core.
        Used for WalletV5R1 (wr5) which requires pytoniq_core cells.

        Args:
            to               (str): Recipient owner address (not their Jetton wallet).
            amount           (int): Jetton amount in the smallest unit (raw, decimals already applied).
            response_address (str): Address that receives the excess TON response.
            forward_amount   (int): Nanotons forwarded with the transfer notification. Default: 0.
            comment          (str): Optional text comment attached as forward payload via snake_string.

        Returns:
            pytoniq_core.Cell: Serialised cell ready to use as a transfer body.
        """
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
            if self.build_tx:
                import base64 as _b64
                return {"tx": _b64.b64encode(body.to_boc()).decode()}
            tx_hash = await self._v5_wallet.transfer(
                destination=jetton_wallet_address,
                amount=gas_amount,
                body=body,
            )
            return {
                "tx": tx_hash,
                "status": "sent",
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

        if self.build_tx:
            return {"tx": boc}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self._get_headers(),
            )
            data = resp.json()
            if data.get("ok"):
                return {
                    "tx": data["result"],
                    "status": "sent",
                    "jetton_amount": amount,
                    "to": to,
                }
            raise ValueError(f"Jetton transfer failed: {data}")

    async def get_jetton_wallet_address(
        self, jetton_master: str, owner: Optional[str] = None
    ) -> Optional[str]:
        """
        Queries the Jetton master contract to find the Jetton wallet address for an owner.
        Each owner has a unique personal Jetton wallet derived from the master contract.

        Args:
            jetton_master (str): Jetton master contract address.
            owner         (str): Owner address to derive the wallet for. Defaults to active wallet.

        Returns:
            str | None: The Jetton wallet address for the owner, or None if the call failed.
        """
        if not owner:
            owner = self.get_address()

        # Encode owner address as BOC cell — TonCenter runGetMethod requires
        # address arguments as base64-encoded BOC slices, not plain strings.
        owner_boc = base64.b64encode(
            bytes(pbegin_cell().store_address(PAddress(owner)).end_cell().to_boc())
        ).decode()

        data = await self._run_get_method(
            jetton_master, "get_wallet_address", [["tvm.Slice", owner_boc]]
        )

        if not data.get("ok"):
            raise ValueError(f"get_wallet_address RPC error: {data}")
        stack = data["result"].get("stack", [])
        if not stack:
            raise ValueError(f"get_wallet_address returned empty stack: {data['result']}")

        item = stack[0]
        # TonCenter v2 returns ["tvm.Slice"/"cell", "<base64_boc>"] or ["cell", {"bytes": "..."}]
        raw = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else item
        if isinstance(raw, dict):
            raw = raw.get("bytes") or raw.get("boc") or ""
        try:
            cell = PCell.one_from_boc(base64.b64decode(raw))
            addr = cell.begin_parse().load_address()
            return addr.to_str(is_user_friendly=True, is_url_safe=True, is_bounceable=False)
        except Exception as e:
            raise ValueError(f"address decode failed (stack[0]={item}): {e}")

    async def send_ton_connect_tx(self, tx: dict) -> str:
        """
        Signs and broadcasts a TON Connect 2.0 sendTransaction payload.

        Args:
            tx (dict): {
                'from':        str,            # sender address (ignored, uses active wallet)
                'network':     str,            # '-239' mainnet / '-3' testnet
                'valid_until': int,            # unix expiry timestamp
                'messages': [{
                    'address': str,            # destination
                    'amount':  str,            # nanoTON (already in nano, no conversion)
                    'payload': str | None,     # base64 BoC body cell (optional)
                    'stateInit': str | None,   # base64 BoC stateInit (optional)
                }]
            }

        Returns:
            str: Transaction hash hex string.
        """
        messages = tx.get("messages", [])
        if not messages:
            raise ValueError("TON Connect tx has no messages")

        def _parse_payload_pcell(b64: str | None):
            """Parse BoC → pytoniq_core Cell (for wr5 / tonutils path)."""
            if not b64:
                return None
            return PCell.one_from_boc(base64.b64decode(b64))

        def _parse_payload_tonsdk(b64: str | None):
            """Parse BoC → tonsdk-compatible Cell (for legacy wallets).
            Converts PCell tree recursively to tonsdk Cell.
            """
            if not b64:
                return None
            pcell = PCell.one_from_boc(base64.b64decode(b64))

            def _convert(pc) -> Cell:
                tc = Cell()
                # copy bit data as raw bytes
                data = bytes(pc.data) if hasattr(pc, 'data') else b''
                if data:
                    tc.bits.write_bytes(data)
                for ref in (pc.refs if hasattr(pc, 'refs') else []):
                    tc.refs.append(_convert(ref))
                return tc

            try:
                return _convert(pcell)
            except Exception:
                return None  # drop payload on conversion failure

        # ── WalletV5R1 (wr5) — uses pytoniq_core PCell ───────────
        if self.wallet_version == "wr5":
            from tonutils.contracts.wallet import WalletMessage

            wallet_messages = []
            for m in messages:
                body = _parse_payload_pcell(m.get("payload"))
                wallet_messages.append(
                    WalletMessage(
                        destination=m["address"],
                        amount=int(m["amount"]),
                        body=body,
                    )
                )

            if len(wallet_messages) == 1:
                ext_msg = self._v5_wallet.transfer_message(
                    destination=messages[0]["address"],
                    amount=int(messages[0]["amount"]),
                    body=_parse_payload_pcell(messages[0].get("payload")),
                )
            else:
                ext_msg = self._v5_wallet.batch_transfer_message(wallet_messages)

            boc = base64.b64encode(bytes(ext_msg.serialize())).decode()
            return await self.send_boc(boc)

        # ── Legacy tonsdk (v3r1, v3r2, v4r2) — uses tonsdk Cell ──
        seqno = await self.get_seqno()

        if len(messages) == 1:
            m = messages[0]
            to     = self._normalize_address(m["address"])
            amount = int(m["amount"])
            body   = _parse_payload_tonsdk(m.get("payload"))
            query  = self.wallet.create_transfer_message(
                to_addr=to, amount=amount, seqno=seqno, payload=body
            )
            boc_bytes = query["message"].to_boc(False)
            boc = bytes_to_b64str(boc_bytes)
        else:
            last_hash = None
            for m in messages:
                to     = self._normalize_address(m["address"])
                amount = int(m["amount"])
                body   = _parse_payload_tonsdk(m.get("payload"))
                cur_seqno = await self.get_seqno()
                query = self.wallet.create_transfer_message(
                    to_addr=to, amount=amount, seqno=cur_seqno, payload=body
                )
                boc_bytes = query["message"].to_boc(False)
                boc = bytes_to_b64str(boc_bytes)
                last_hash = await self.send_boc(boc)  # returns hex hash
                await asyncio.sleep(3)
            return last_hash or ""

        return await self.send_boc(boc)

    async def send_boc(self, boc: str) -> dict:
        """
        Broadcasts a pre-built and signed BOC directly to TonCenter.
        Use this to send transactions built externally or returned by build_tx=True.

        Args:
            boc (str): Base64-encoded BOC string (e.g. "te6cck...").

        Returns:
            dict: {"hash": "<msg_hash_hex>", "ok": True, "result": {...}} on success.

        Raises:
            ValueError: If TonCenter returns an error.
        """
        cell = PCell.one_from_boc(base64.b64decode(boc))
        msg_hash = cell.hash.hex()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendBoc",
                json={"boc": boc},
                headers=self._get_headers(),
            )
            data = resp.json()
            if not data.get("ok"):
                raise ValueError(f"sendBoc failed: {data}")
            return {"tx": msg_hash}

    async def get_transactions(
        self, address: Optional[str] = None, limit: int = 10
    ) -> list:
        """
        Fetches raw recent transactions for an address from TonCenter getTransactions.

        Args:
            address (str): TON address to query. Defaults to the active wallet address.
            limit   (int): Maximum number of transactions to return. Default: 10.

        Returns:
            list[dict]: Raw TonCenter transaction dicts. Empty list on failure.
        """
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
        """
        Calls get_jetton_data on the Jetton master contract to retrieve token metadata.

        Args:
            jetton_master (str): Jetton master contract address.

        Returns:
            dict: Raw TonCenter result — typically contains total_supply, mintable,
                  admin_address, jetton_content, and jetton_wallet_code stack values.

        Raises:
            ValueError: If the RPC call fails.
        """
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

    @staticmethod
    def _parse_stack_int(item) -> int:
        """Parse a TonCenter stack num entry: ['num', '0x...'] or ['num', '123']."""
        val = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else item
        if isinstance(val, int):
            return val
        val = str(val).strip()
        if val.startswith("0x") or val.startswith("0X"):
            return int(val, 16)
        return int(val)

    async def _run_get_method(self, address: str, method: str, stack: list,
                              retries: int = 3, retry_delay: float = 1.5) -> dict:
        """Calls runGetMethod with automatic retry on 429 rate-limit responses."""
        for attempt in range(retries):
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.api_url}/runGetMethod",
                    json={"address": address, "method": method, "stack": stack},
                    headers=self._get_headers(),
                )
                data = resp.json()
            if data.get("ok"):
                return data
            if data.get("code") == 429 and attempt < retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            return data
        return data

    async def get_jetton_balance(
        self,
        jetton_master: str,
        owner_address: Optional[str] = None,
    ) -> dict:
        """
        Returns the Jetton token balance for an owner address.

        Fetches the personal Jetton wallet address for the owner, reads its balance
        via get_wallet_data, and enriches the result with symbol/decimals from
        TonCenter getTokenData (best-effort — falls back to defaults on parse error).

        Args:
            jetton_master  (str): Jetton master contract address.
            owner_address  (str): Owner TON address. Defaults to the active wallet.

        Returns:
            dict: {
                "symbol":        str,   # e.g. "USDT"  (or "JETTON" if unknown)
                "name":          str,   # full token name
                "decimals":      int,   # token decimals (or 9 if unknown)
                "balance":       float, # human-readable amount
                "raw_balance":   int,   # amount in minimal units
                "jetton_wallet": str,   # derived Jetton wallet address
                "jetton_master": str,   # master contract address (echo)
            }

        Raises:
            ValueError: If the Jetton wallet address cannot be determined or the
                        balance RPC call fails.
        """
        if not owner_address:
            owner_address = self.get_address()

        import hashlib as _hl
        _KNOWN = {_hl.sha256(k.encode()).digest(): k
                  for k in ("uri", "name", "description", "image", "symbol", "decimals")}

        # Phase 1: derive jetton wallet + fetch jetton master metadata in parallel
        async def _fetch_wallet_addr() -> str:
            return await self.get_jetton_wallet_address(jetton_master, owner_address)

        async def _fetch_master_meta() -> dict:
            """Returns parsed attrs dict from get_jetton_data content cell."""
            attrs: dict = {}
            try:
                jd = await self._run_get_method(jetton_master, "get_jetton_data", [])
                if not jd.get("ok"):
                    return attrs
                jstack = jd["result"].get("stack", [])
                if len(jstack) < 4:
                    return attrs
                raw_cell = jstack[3][1]
                if isinstance(raw_cell, dict):
                    raw_cell = raw_cell.get("bytes") or raw_cell.get("boc") or ""
                cs = PCell.one_from_boc(base64.b64decode(raw_cell)).begin_parse()
                prefix = cs.load_uint(8)
                if prefix == 0x01:
                    attrs["uri"] = cs.load_snake_string().lstrip("\x00")
                elif prefix == 0x00:
                    hmap = cs.load_dict(256)
                    for k_int, v_slice in (hmap or {}).items():
                        attr_name = _KNOWN.get(k_int.to_bytes(32, "big"))
                        if attr_name and v_slice.remaining_refs > 0:
                            raw_val = v_slice.load_ref().begin_parse().load_snake_string().lstrip("\x00")
                            attrs[attr_name] = raw_val
                # follow off-chain URI
                uri = attrs.get("uri", "")
                if uri.startswith("http"):
                    async with httpx.AsyncClient(timeout=6) as c:
                        rj = await c.get(uri)
                        attrs.update(rj.json())
            except Exception:
                pass
            return attrs

        jetton_wallet, meta_attrs = await asyncio.gather(
            _fetch_wallet_addr(), _fetch_master_meta()
        )

        if not jetton_wallet:
            raise ValueError(
                f"Could not resolve Jetton wallet for master={jetton_master} owner={owner_address}"
            )

        # Phase 2: read balance from the personal jetton wallet
        raw_balance = 0
        data = await self._run_get_method(jetton_wallet, "get_wallet_data", [])
        if not data.get("ok"):
            raise ValueError(f"get_wallet_data failed: {data}")
        stack = data["result"].get("stack", [])
        if stack:
            try:
                raw_balance = self._parse_stack_int(stack[0])
            except Exception:
                raw_balance = 0

        # Apply metadata
        symbol = str(meta_attrs["symbol"]) if meta_attrs.get("symbol") else "JETTON"
        name   = str(meta_attrs["name"])   if meta_attrs.get("name")   else ""
        decimals = 9
        if meta_attrs.get("decimals") is not None:
            try:
                decimals = int(meta_attrs["decimals"])
            except (ValueError, TypeError):
                pass

        return {
            "symbol":        symbol,
            "name":          name or symbol,
            "decimals":      decimals,
            "raw_balance":   raw_balance,
            "balance":       raw_balance / (10 ** decimals),
            "jetton_wallet": str(jetton_wallet),
            "jetton_master": jetton_master,
        }

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
        """
        Extracts a human-readable text comment from a TonCenter msg_data object.
        Handles both msg.dataText (Base64 UTF-8) and msg.dataRaw (BOC cell with op=0).

        Args:
            msg_data (dict): The msg_data field from a TonCenter transaction message.

        Returns:
            str | None: Decoded text comment, or None if not present / not decodable.
        """
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
        """
        Reads the first 32-bit opcode from a raw message body cell.
        Used to identify TEP-74 Jetton ops, NFT ops, or arbitrary contract calls.

        Args:
            msg_data (dict): The msg_data field from a TonCenter transaction message
                             (must have @type == "msg.dataRaw").

        Returns:
            int | None: The opcode as an integer, or None if not decodable.
        """
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
        """
        Attempts to decode a known Jetton / NFT operation body from a raw message cell.
        Supports: jetton_transfer, jetton_transfer_notification, jetton_internal_transfer,
                  jetton_burn, nft_transfer, and other TEP-74/TEP-62 opcodes.

        Args:
            msg_data (dict): The msg_data field from a TonCenter transaction message
                             (must have @type == "msg.dataRaw").

        Returns:
            dict | None: Parsed fields including op, op_name, and opcode-specific data
                         (jetton_amount, destination, sender, query_id, etc.), or None if not decodable.
        """
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
        """
        Normalises a single in_msg or out_msg object from TonCenter into a clean flat dict.

        Args:
            msg (dict): Raw message dict from a TonCenter transaction.

        Returns:
            dict: {
                "source":        str,
                "destination":   str,
                "value":         int,    # nanotons
                "value_ton":     float,  # TON
                "fwd_fee":       int,    # nanotons
                "ihr_fee":       int,    # nanotons
                "created_lt":    str,    # logical time
                "body_hash":     str,
                "msg_data_type": str,    # @type of msg_data, e.g. "msg.dataRaw"
            }
        """
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
    async def parse_transaction(cls, raw_tx: dict, get_price: bool = False, price: float = None) -> dict:
        """
        Parses a single raw TON transaction (as returned by TonCenter getTransactions)
        into a structured human-readable dict.

        Detects transaction categories: native_transfer, jetton_transfer,
        jetton_transfer_notification, jetton_burn, nft_transfer, contract_call, external, other.

        Args:
            raw_tx    (dict):  A single transaction dict from TonCenter API v2.
            get_price (bool):  If True, fetches the current TON/USD price from CoinGecko
                               and appends fee_in_usd and total_out_value_usd fields.
            price     (float): Pre-fetched TON/USD price. If provided, skips CoinGecko call.

        Returns:
            dict: {
                "tx_hash":              str,
                "lt":                   str,            # logical time
                "timestamp":            int,            # unix timestamp
                "datetime_utc":         str,
                "fee":                  int,            # nanotons
                "fee_ton":              float,
                "storage_fee":          int,
                "other_fee":            int,
                "tx_category":          str,
                "opcode":               str | None,     # hex opcode of in_msg
                "in_msg":               dict,           # normalised incoming message
                "out_msgs":             list[dict],     # normalised outgoing messages
                "out_msgs_count":       int,
                "total_out_value":      int,            # nanotons
                "total_out_value_ton":  float,
                "comment":              str | None,
                "jetton":               dict | None,    # present if Jetton op detected
                "fee_in_usd":           str | None,     # present if price provided
                "total_out_value_usd":  str | None,     # present if price provided
            }
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
        get_price: bool = False,
        price: float = None
    ) -> List[dict]:
        """
        Fetches recent transactions and returns them fully parsed via parse_transaction.

        Args:
            address   (str):   TON address to query. Defaults to the active wallet address.
            limit     (int):   Maximum number of transactions to fetch. Default: 10.
            get_price (bool):  If True, appends USD values using a live CoinGecko price.
            price     (float): Pre-fetched TON/USD price to use instead of CoinGecko.

        Returns:
            list[dict]: List of parse_transaction results (see parse_transaction for the schema).
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
        Finds a specific transaction by hash in recent history and returns it parsed.
        Does not retry — use parse_tx_by_hash if the transaction may not be indexed yet.

        Args:
            tx_hash (str): Transaction hash (Base64) to look for.
            address (str): TON address to search in. Defaults to the active wallet.
            limit   (int): How many recent transactions to scan. Default: 50.

        Returns:
            dict | None: Parsed transaction dict, or None if not found in the scanned range.
        """
        raw_txs = await self.get_transactions(address=address, limit=limit)
        for tx in raw_txs:
            tid = tx.get("transaction_id", {})
            if tid.get("hash") == tx_hash:
                return self.parse_transaction(tx)
        return None

    def parse_raw_tx(self, tx: dict) -> dict:
        """
        Parses a TON Connect 2.0 sendTransaction payload locally — no network call.
        Decodes payload BOC cells for each message: opcode, jetton fields, comment.

        Args:
            tx (dict): {
                'from':        str,         # sender address
                'network':     str,         # '-239' mainnet / '-3' testnet
                'valid_until': int,         # unix expiry timestamp
                'messages': [{
                    'address':   str,       # destination
                    'amount':    str,       # nanoTON
                    'payload':   str | None,  # base64 BOC body cell
                    'stateInit': str | None,  # base64 BOC stateInit
                }]
            }

        Returns:
            dict: {
                'sender':          str,
                'network':         'mainnet' | 'testnet',
                'valid_until':     int,
                'valid_until_utc': str,
                'num_messages':    int,
                'total_ton_nano':  int,
                'total_ton':       float,
                'tx_type':         str,  # 'native_transfer' | 'jetton_transfer' | 'contract_call' | 'mixed'
                'messages': list[{
                    'destination':    str,
                    'amount_nano':    int,
                    'amount_ton':     float,
                    'op':             str | None,   # hex opcode
                    'op_name':        str | None,
                    'comment':        str | None,
                    'jetton':         dict | None,
                    'has_state_init': bool,
                }],
            }
        """
        network_raw = str(tx.get("network", "-239"))
        network = "mainnet" if network_raw == "-239" else "testnet"
        valid_until = tx.get("valid_until", 0)

        parsed_msgs = []
        for m in tx.get("messages", []):
            amount_nano = int(m.get("amount", 0))
            payload_b64 = m.get("payload")

            msg_data = (
                {"@type": "msg.dataRaw", "body": payload_b64}
                if payload_b64 else None
            )

            op_int   = self._decode_body_op(msg_data)
            comment  = self._decode_comment(msg_data) if (op_int is None or op_int == 0) else None
            jetton   = self._parse_jetton_body(msg_data)
            op_name  = self._JETTON_OPCODES.get(op_int) if op_int else None

            parsed_msgs.append({
                "destination":    m.get("address", ""),
                "amount_nano":    amount_nano,
                "amount_ton":     amount_nano / NANOTON,
                "op":             hex(op_int) if op_int is not None else None,
                "op_name":        op_name,
                "comment":        comment,
                "jetton":         jetton,
                "has_state_init": bool(m.get("stateInit")),
            })

        total_nano = sum(m["amount_nano"] for m in parsed_msgs)

        # detect overall tx type
        ops = {m["op_name"] for m in parsed_msgs if m["op_name"]}
        has_contract = any(m["op"] and m["op"] != "0x0" for m in parsed_msgs if not m["op_name"])
        if len(parsed_msgs) > 1:
            categories = {m["op_name"] or ("native" if not m["op"] else "contract") for m in parsed_msgs}
            tx_type = "mixed" if len(categories) > 1 else next(iter(categories), "multi_message")
        elif ops:
            tx_type = next(iter(ops))
        elif has_contract:
            tx_type = "contract_call"
        else:
            tx_type = "native_transfer"

        return {
            "sender":          tx.get("from", ""),
            "network":         network,
            "valid_until":     valid_until,
            "valid_until_utc": (
                datetime.fromtimestamp(valid_until, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                if valid_until else None
            ),
            "num_messages":    len(parsed_msgs),
            "total_ton_nano":  total_nano,
            "total_ton":       total_nano / NANOTON,
            "tx_type":         tx_type,
            "messages":        parsed_msgs,
        }

    async def parse_tx_by_hash(
        self,
        tx_hash: str,
        address: Optional[str] = None,
        retries: int = 5,
        retry_delay: float = 2.0,
    ) -> Optional[dict]:
        """
        Finds and parses a transaction by its hash with automatic retries.
        Accepts both hex (64-char) and Base64 hash formats — converts hex to Base64 internally.
        Useful right after broadcasting when the transaction may not be indexed yet.

        Args:
            tx_hash     (str):   Transaction hash — hex (64 chars) or Base64 string.
            address     (str):   TON address to search in. Defaults to the active wallet.
            retries     (int):   Number of polling attempts if not found. Default: 5.
            retry_delay (float): Seconds to wait between attempts. Default: 2.0.

        Returns:
            dict | None: Parsed transaction dict (see parse_transaction), or None if not found.
        """
        import base64

        if not address:
            address = self.get_address()

        if all(c in "0123456789abcdefABCDEF" for c in tx_hash) and len(tx_hash) == 64:
            tx_hash_b64 = base64.b64encode(bytes.fromhex(tx_hash)).decode()
        else:
            tx_hash_b64 = tx_hash

        # First try exact hash match (works if TonCenter uses same hash format)
        for attempt in range(retries):
            raw_txs = await self.get_transactions(address=address, limit=20)
            for tx in raw_txs:
                tid = tx.get("transaction_id", {})
                if tid.get("hash") in (tx_hash_b64, tx_hash):
                    return await self.parse_transaction(tx)
            if attempt < retries - 1:
                await asyncio.sleep(retry_delay)

        # Fallback: external msg hash ≠ internal tx hash in TON.
        # Return the most recent transaction for this address.
        try:
            raw_txs = await self.get_transactions(address=address, limit=5)
            if raw_txs:
                return await self.parse_transaction(raw_txs[0])
        except Exception:
            pass
        return None

    async def parse_receipt_gas(
        self,
        tx_hash: str = None,
        raw_tx: dict = None,
        address: str = None,
        latest: bool = False,
    ) -> dict:
        """
        Extracts fee breakdown for a TON transaction.

        ⚠️  TON has TWO different hashes — do not confuse them:
            msg_hash  — hash of the BOC cell returned by send_boc().
                        This is NOT stored in transaction_id.hash on TonCenter.
            tx_hash   — hash of the transaction itself, from transaction_id.hash
                        in getTransactions response (Base64 or hex).

        TON fee structure:
          fee  =  storage_fee  +  other_fee
          other_fee ≈ execution cost (closest to EVM gas_used * gas_price)
          storage_fee = on-chain cell storage rent

        Args:
            tx_hash (str):   TonCenter transaction hash — Base64 or hex (64 chars).
                             ⚠️ Do NOT pass the msg_hash from send_boc() here.
            raw_tx  (dict):  Already-fetched raw TonCenter transaction dict.
                             Preferred path — avoids hash confusion entirely.
            address (str):   Sender address to search in. Defaults to active wallet.
            latest  (bool):  If True, skips hash lookup and returns fees for the
                             most recent OUTGOING transaction (largest fee).
                             Use this right after send_boc() when you don't have
                             the transaction hash yet.

        Returns:
            dict: {
                "fee_nano":          int,    # total fee in nanotons  (≈ EVM fee_wei / SOL fee_lamports)
                "fee_ton":           float,  # total fee in TON       (≈ EVM fee_eth  / SOL fee_sol)
                "storage_fee_nano":  int,    # storage phase cost
                "storage_fee_ton":   float,
                "other_fee_nano":    int,    # execution + action phase cost (≈ EVM gas cost)
                "other_fee_ton":     float,
                "lt":                str,    # logical time           (≈ EVM block_number / SOL slot)
                "timestamp":         int,    # unix timestamp
                "status":            str,    # "success"
            }

        Raises:
            ValueError: If no input provided or the transaction is not found.
        """
        if raw_tx is None:
            if not address:
                address = self.get_address()

            raw_txs = await self.get_transactions(address=address, limit=50)

            if latest:
                # Outgoing tx has an empty in_msg.source (triggered by external message)
                # and the highest fee among recent transactions.
                outgoing = [
                    t for t in raw_txs
                    if not (t.get("in_msg") or {}).get("source")
                ]
                raw_tx = outgoing[0] if outgoing else (raw_txs[0] if raw_txs else None)
                if raw_tx is None:
                    raise ValueError("No transactions found for address")

            elif tx_hash:
                if all(c in "0123456789abcdefABCDEF" for c in tx_hash) and len(tx_hash) == 64:
                    tx_hash_b64 = base64.b64encode(bytes.fromhex(tx_hash)).decode()
                else:
                    tx_hash_b64 = tx_hash

                raw_tx = next(
                    (t for t in raw_txs if t.get("transaction_id", {}).get("hash") == tx_hash_b64),
                    None,
                )
                if raw_tx is None:
                    raise ValueError(
                        f"Transaction {tx_hash} not found. "
                        "Note: msg_hash from send_boc() ≠ transaction_id.hash. "
                        "Use latest=True or pass raw_tx directly."
                    )
            else:
                raise ValueError("Provide tx_hash, raw_tx, or set latest=True")

        tx_id       = raw_tx.get("transaction_id", {})
        total_fee   = int(raw_tx.get("fee", 0) or 0)
        storage_fee = int(raw_tx.get("storage_fee", 0) or 0)
        other_fee   = int(raw_tx.get("other_fee", 0) or 0)
        utime       = raw_tx.get("utime", 0)

        return {
            "fee":               total_fee,
            "fee_ton":           total_fee   / NANOTON,
            "storage_fee_nano":  storage_fee,
            "storage_fee_ton":   storage_fee / NANOTON,
            "other_fee_nano":    other_fee,
            "other_fee_ton":     other_fee   / NANOTON,
            "lt":                tx_id.get("lt", ""),
            "timestamp":         utime,
            "status":            "success",
        }


async def main():
    ton = TON()
    data = await ton.parse_receipt_gas(latest=True, address="EQCzYN15-IOT0LeXIM9Sc2TXmck3BNBr43_PaSiD3GAhCfAi")
    return data

if __name__ == "__main__":
    import asyncio
    print(asyncio.run(main()))