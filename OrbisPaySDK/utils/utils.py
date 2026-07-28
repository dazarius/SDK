import solders
import httpx
import OrbisPaySDK.const as sdk_const
from OrbisPaySDK.const import LAMPORTS_PER_SOL
from OrbisPaySDK.interface import (erc20, erc721, sol)
from OrbisPaySDK.types import EVMcheque, SOLcheque
from web3 import Web3
import dataclasses
import os

from dataclasses import dataclass
from typing import Union, Optional, Dict, List
import base58
import base64
import hashlib
import json
import time
from functools import wraps
import asyncio, inspect



def _await(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
                return loop.run_until_complete(result)
            except RuntimeError:
                return asyncio.run(result)
        return result
    return wrapper



def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} completed for {end - start:.4f} sec")
        return result
    return wrapper

@dataclass 
class Cheque():
    signature:str
    fee_pay:any
    date:str
    
@dataclass
class TokenERC20:
    symbal:any
    name:any
    decimals:any
    icon:any = None


@dataclass
class baseChainSettings:
    name:str 
    rpc:str 

@dataclass
class baseTranserParams:
    from_:any
    to:str | list
    token:any
    bc:any
    amount_ui:any
    amount:any
    contract:any
    chain:baseChainSettings
    

@dataclass
class Chaque:

    baseTranserParam:baseTranserParams = None
    contract:str = None


@dataclass
class ChequeParams:
    """
    Unified cheque parameters for all cheque types:
      - native:  token=None,  token_out=None
      - token:   token=<addr>, token_out=None
      - swap:    token=<token_in>, token_out=<token_out>, amount_out=<amount>

    recipients: single address (str) or list of addresses for multi-receiver native cheques.
    """
    amount: any
    support_bps: any
    recipients: Union[str, List[str]]
    token: Optional[str] = None
    token_out: Optional[str] = None
    amount_out: Optional[any] = None


class _Helper():
    def __init__(self, obj = None, sep: str  = ".", comment_char:str = " ",_KDF_ITERATIONS: int = 390_000, _SALT_SIZE: int = 16, _IV_SIZE: int = 12, _KEY_SIZE: int = 32):
        self.sep: str  = sep
        self.comment_char:str =  comment_char
        self._KDF_ITERATIONS = _KDF_ITERATIONS
        self._SALT_SIZE = _SALT_SIZE
        self._IV_SIZE = _IV_SIZE
        self._KEY_SIZE = _KEY_SIZE
        self.obj = obj
    @staticmethod
    def debug(fn):
        import inspect
        sig = inspect.signature(fn)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            pretty = " | ".join(f"{k}={v!r}" for k, v in bound.arguments.items())
            print(f"[{fn.__name__}] {pretty}")
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    def parse_line(self, line: str, sep: str = None, label: str = "transfer", default="requier") -> list[str]:
        """
        Parse a line into [from, to, amount].

        Formats:
            to.amount          → from = default (or "from_reqier" if default is None)
            from.to.amount     → all three from the line

        Returns:
            [from, to, amount] or [] if unparseable.

        Examples:
            parse_line('ABC.100000')              → ['from_reqier', 'ABC', '100000']
            parse_line('ABC.100000', default='X') → ['X', 'ABC', '100000']
            parse_line('KEY.ABC.100000')           → ['KEY', 'ABC', '100000']
            parse_line('KEY,ABC,100000', sep=',')  → ['KEY', 'ABC', '100000']
        """
        if sep is None:
            sep = self.sep
        import re
        line = line.strip()
        if not line:
            return []

        line = re.sub(r'\s+[-#;].*$', '', line).strip()
        line = re.sub(r'\s*//.*$',    '', line).strip()
        if not line:
            return []

        parts = [p.strip() for p in line.split(sep)]

        if parts and parts[-1]:
            parts[-1] = parts[-1].split()[0]

        

        parts = [p for p in parts if p]

        if len(parts) == 2:
            parts.insert(0, default)

        try:
            parts[-1] = int(parts[-1])
        except (ValueError, IndexError):
            pass

        return parts


    def deep_get(self, data, keys: list, default=None):
        """
        Iteratively search the entire nested structure for any key in *keys*.
        Tries each key in order; returns the value of the first one found (depth-first).
        Returns *default* if none of the keys exist anywhere in the structure.

        Examples:
            data = {"chains": {"evm": {"rpc": "https://...", "tokens": ["USDT"]}}}

            deep_get(data, ["rpc"])              → "https://..."
            deep_get(data, ["tokens"])           → ["USDT"]
            deep_get(data, ["missing"], "N/A")   → "N/A"
            deep_get(data, ["missing", "rpc"])   → "https://..."  (fallback to next key)
        """
        from collections import deque

        for key in keys:
            stack = deque([data])
            while stack:
                obj = stack.pop()
                if isinstance(obj, dict):
                    if key in obj:
                        val = obj[key]
                        return val if val is not None else default
                    stack.extend(obj.values())
                elif isinstance(obj, (list, tuple)):
                    stack.extend(obj)
        return default
    def deep_get_path_traversal(self, data, keys: list, default=None):
        """
        Traverse a nested dict/list by path.
        Each element of *keys* is a step: dict key or list index (int).
        Returns *default* if any step is missing or the type doesn't match.

        Examples:
            data = {"blockchain_card": {"EVM": {"chain": 7}}}

            deep_get(data, ["blockchain_card", "EVM", "chain"])  → 7
            deep_get(data, ["blockchain_card", "SOL", "chain"])  → 0  (default)
            deep_get(data, ["missing"], "N/A")                   → "N/A"
        """
        cur = data
        for key in keys:
            if isinstance(cur, dict):
                if key not in cur:
                    return default
                cur = cur[key]
            elif isinstance(cur, (list, tuple)) and isinstance(key, int):
                if key < 0 or key >= len(cur):
                    return default
                cur = cur[key]
            else:
                return default
        return cur if cur is not None else default
    def _derive_key(self,password: str, salt: bytes) -> bytes:
        """Derive a 256-bit key from a password using PBKDF2-HMAC-SHA256."""
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self._KEY_SIZE,
            salt=salt,
            iterations=self._KDF_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))


    def encrypt_private_key(self,private_key: str, password: str) -> str:
        """
        Encrypt a private key with a password (AES-256-GCM).

        :param private_key: Private key (hex string, base58, etc.)
        :param password:    User password
        :return:            Base64 string (salt + iv + tag + ciphertext)
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        salt = os.urandom(self._SALT_SIZE)
        iv   = os.urandom(self._IV_SIZE)
        key  = self._derive_key(password, salt)

        aesgcm     = AESGCM(key)
        ciphertext = aesgcm.encrypt(iv, private_key.encode("utf-8"), None)
        # ciphertext already contains the tag (last 16 bytes)

        blob = salt + iv + ciphertext
        return base64.b64encode(blob).decode("ascii")


    def decrypt_private_key(self, encrypted_b64: str, password: str) -> str:
        """
        Decrypt a private key from a base64 string.

        :param encrypted_b64: String returned by encrypt_private_key()
        :param password:      User password
        :return:              Original private key
        :raises ValueError:   Wrong password or corrupted data
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag

        try:
            blob = base64.b64decode(encrypted_b64)
        except Exception:
            raise ValueError("Invalid encrypted data format")

        if len(blob) < self._SALT_SIZE + self._IV_SIZE + 16:
            raise ValueError("Data is too short - corrupted or not encrypted")

        salt       = blob[:self._SALT_SIZE]
        iv         = blob[self._SALT_SIZE : self._SALT_SIZE + self._IV_SIZE]
        ciphertext = blob[self._SALT_SIZE + self._IV_SIZE :]

        key    = self._derive_key(password, salt)
        aesgcm = AESGCM(key)

        try:
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
        except InvalidTag:
            raise ValueError("Invalid password or data corrupted")

        return plaintext.decode("utf-8")



class _SOLhelper():
    def __init__(self, client = None):
        self.client = client

    def converted_secret_to_private_key(self, private_key: str) -> str:
        return base58.b58decode(private_key).hex()
    def _get_explorer_link(tx,mode = "mainnet"):
        _explorer = sdk_const.SOLSCAN
        _explorer_link = _explorer + tx
        return _explorer_link + "/devnet" if mode == "devnet" else _explorer_link
    

def extractedParamsChain(data):
    for key in data["chains"]:
        pass
def extractParamsForCheque(transferParams:baseTranserParams) -> Chaque:
    c = Chaque(baseTranserParam=transferParams)
    return c
def extractParamsForTransfer(data)-> baseTranserParams: 
    
    t = baseTranserParams(None,None,None,None,None,None,None,None)
    c = baseChainSettings(None,None)
    transferParams = data["transferParams"]
    chainParms = data["chains"]
    print(t.__dict__.keys())
    for key in transferParams:
        for i in t.__dict__.keys():
            if key == i:
                t.__dict__.__setitem__(key, transferParams[key])
    for key in chainParms:
        for i in t.__dict__.keys():
            if key == i:
                t.__dict__.__setitem__(key, chainParms[key])
    t.chain = c
    
    return t
def modify_tx(tx: dict, w3: Web3, from_addr: str = None, to_addr: str = None, value: int = None) -> dict:
    chain_id  = w3.eth.chain_id

    nonce  = w3.eth.get_transaction_count(from_addr)
    latest = w3.eth.get_block('latest')
    gas    = w3.eth.estimate_gas({'from': from_addr, 'to': to_addr, 'value': value})

    
    if latest.get('baseFeePerGas') is not None:
        tip = w3.eth.max_priority_fee
        base = latest['baseFeePerGas']
        max_fee = base * 2 + tip
        if tx == {}:
            tx = {
                'type': 0x2, 'chainId': chain_id, 'nonce': nonce,
                'to': to_addr, 'value': value, 'gas': int(gas),
                'maxPriorityFeePerGas': int(tip),
                'maxFeePerGas': int(max_fee),
            }
    else:
        if tx == {}:
            tx = {
                'chainId': chain_id, 'nonce': nonce,
                'to': to_addr, 'value': value, 'gas': int(gas),
                'gasPrice': int(w3.eth.gas_price * 1.10),
            }
    return tx
def convert_to_wei():
    pass
def _format_tx(explorer,tx_hash: str) -> str:
    if explorer:
        return f"{explorer.rstrip('/')}/tx/{tx_hash}"
    return tx_hash


def derive_cheque_id(params: dict) -> str:
    """
    Deterministic cheque_id (hex) from params dict.

    sha256 of the same raw bytes that encode_cheque_payload() produces,
    so encode → decode always gives the same cheque_id.

    For uniqueness across identical param sets add a timestamp/nonce directly
    into params: derive_cheque_id({**params, "ts": int(time.time())})
    """
    raw = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def encode_cheque_payload(params: dict) -> str:
    """
    Pack cheque params into a hex string (raw UTF-8 JSON bytes).
    sha256 of those same bytes = the on-chain cheque_id.

    Share this string — recipient decodes it locally with decode_cheque_payload().
    """
    raw = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str).encode()
    return raw.hex()


def decode_cheque_payload(payload: str) -> dict:
    """
    Reverse of encode_cheque_payload(): unpack params and derive cheque_id locally.

    Returns:
        dict: {"params": dict, "cheque_id": str (hex)}
    """
    raw = bytes.fromhex(payload)
    return {
        "params":    json.loads(raw),
        "cheque_id": hashlib.sha256(raw).hexdigest(),
    }



# ========================= Price providers =========================

import asyncio as _aio
from typing import Any





from OrbisPaySDK.utils.provider import _BaseProvider
from OrbisPaySDK.utils.coingecko import CoinGecko
from OrbisPaySDK.utils.coinmarketcap import CoinMarketCap
from OrbisPaySDK.utils.dexscreener import DexScreener


_default_cg = CoinGecko()


async def get_native_prices(
    vs_currency: str = "usd",
    coins: Optional[List[str]] = None, 
) -> Dict[str, float]:
    """Shortcut: ``CoinGecko().get_prices(coins, vs_currency)``."""
    return await _default_cg.get_prices(coins=coins, vs_currency=vs_currency)


async def get_native_price(
    coin: str,
    vs_currency: str = "usd",
) -> float:
    """Shortcut: ``CoinGecko().get_price(coin, vs_currency)``."""
    return await _default_cg.get_price(coin=coin, vs_currency=vs_currency)
def _rand_str(n=8):
        return "".join(random.choices(string.ascii_lowercase, k=n))
_helper = _Helper()
@timer
def main():
        # Build a flat dict with 10_000 entries, one known nested target buried inside
        flat = {_rand_str(): _rand_str() for _ in range(1000)}
        flat["chain_meta"] = {
            "evm": {
                "rpc": "https://mainnet.infura.io",
                "tokens": ["USDT", "USDC"],
                "target_key": "FOUND_IT",
            }
        }
        flat["extra_a"] = [{"noise": _rand_str()} for _ in range(50)]
        flat["extra_b"] = {_rand_str(): {"nested": _rand_str()} for _ in range(50)}

        N = 1_000  # number of benchmark iterations

        scenarios = [
            ("hit  — key at shallow level",   ["tokens"],     flat),
            ("hit  — key deep in nested dict", ["target_key"], flat),
            ("miss — key not present",         ["xxxxxxxx"],   flat),
            ("multi-key, first hits",          ["tokens", "xxxxxxxx"], flat),
            ("multi-key, second hits",         ["xxxxxxxx", "target_key"], flat),
        ]

        print(f"\n{'Scenario':<42} {'N':>6}  {'total ms':>9}  {'per-call µs':>11}  {'result'}")
        print("-" * 95)

        for label, keys, d in scenarios:
            t0 = time.perf_counter()
            for _ in range(N):
                result = _helper.deep_get(data=d, keys=keys, default="NOT_FOUND")
            elapsed = time.perf_counter() - t0
            total_ms = elapsed * 1000
            per_us   = elapsed / N * 1_000_000
            short = repr(result)[:30]
            print(f"{label:<42} {N:>6}  {total_ms:>9.2f}  {per_us:>11.2f}  {short}")

        print()




if __name__ == "__main__":
    import time
    import random
    import string
    # def _rand_str(n=8):
    #         return "".join(random.choices(string.ascii_lowercase, k=n))
    # _pass = _rand_str(10)
    # _key = {
    #     "w":"efcwad",
    #     "k":"efwcaefwdfcvwaseceazDsfzFCsezdf"
    # }
    
    # encrypt_private_key = _helper.encrypt_private_key(str(_key), _pass)
    # decrypt_private_key = _helper.decrypt_private_key(encrypt_private_key,_pass)
    # print("[encrypt_private_key]:", " ", encrypt_private_key)
    # print("[decrypt_private_key]:", " " ,dict(decrypt_private_key))
    main()

    