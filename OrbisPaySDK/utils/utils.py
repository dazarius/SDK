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



# ========================= Price providers =========================

import asyncio as _aio
from typing import Any





class _BaseProvider:
    """Shared HTTP logic with retry / rate-limit handling."""

    _RETRIES = 3

    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.request(
                    method, url, params=params, headers=self._headers,
                )
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
        return None

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        return await self._request("GET", path, params)


# ---------------------------------------------------------------------------
#  CoinGecko
# ---------------------------------------------------------------------------

class CoinGecko(_BaseProvider):
    """
    CoinGecko price provider.

    Free tier — no API key required (rate-limit ~30 req/min).
    Pro tier  — pass *api_key* for higher limits.

    Example::

        cg = CoinGecko()
        prices = await cg.get_prices()                # all 6 tokens in USD
        sol    = await cg.get_price("sol", "eur")     # single token in EUR
        info   = await cg.get_coin_info("bitcoin")    # full coin metadata
        res    = await cg.search("ton")               # search coins
    """

    COIN_ID_MAP: Dict[str, str] = {
        "btc": "bitcoin", "bitcoin": "bitcoin",
        "eth": "ethereum", "evm": "ethereum", "ethereum": "ethereum",
        "bnb": "binancecoin", "bsc": "binancecoin", "binancecoin": "binancecoin",
        "sol": "solana", "solana": "solana",
        "trx": "tron", "tron": "tron",
        "ton": "the-open-network", "the-open-network": "the-open-network",
    }
    DEFAULT_COINS = ["bitcoin", "ethereum", "binancecoin", "solana", "tron", "the-open-network"]
    SYMBOL_MAP: Dict[str, str] = {
        "bitcoin": "btc", "ethereum": "eth", "binancecoin": "bnb", "solana": "sol",
        "tron": "trx", "the-open-network": "ton",
    }

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            base = "https://pro-api.coingecko.com/api/v3"
            headers = {"x-cg-pro-api-key": api_key}
        else:
            base = "https://api.coingecko.com/api/v3"
            headers = {}
        super().__init__(base, headers)

    def _resolve_ids(self, coins: Optional[List[str]] = None) -> List[str]:
        if not coins:
            return list(self.DEFAULT_COINS)
        ids = []
        for c in coins:
            cg_id = self.COIN_ID_MAP.get(c.lower())
            if not cg_id:
                raise ValueError(
                    f"Unknown coin '{c}'. Supported: {list(self.COIN_ID_MAP.keys())}"
                )
            ids.append(cg_id)
        return ids

    async def get_prices(
        self,
        coins: Optional[List[str]] = None,
        vs_currency: str = "usd",
    ) -> Dict[str, float]:
        """
        Fetch prices for native tokens.

        Args:
            coins: List of aliases (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).
                   ``None`` — all six.
            vs_currency: Fiat code (``usd``, ``eur``, ``rub``, …).

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, "bnb": 600.0, ...}``
        """
        cg_ids = self._resolve_ids(coins)
        vs = vs_currency.lower()
        data = await self._get(
            "/simple/price",
            params={"ids": ",".join(sorted(set(cg_ids))), "vs_currencies": vs},
        ) or {}
        result: Dict[str, float] = {}
        for cg_id in cg_ids:
            sym = self.SYMBOL_MAP.get(cg_id, cg_id)
            result[sym] = float((data.get(cg_id) or {}).get(vs, 0))
        return result

    async def get_price(self, coin: str, vs_currency: str = "usd") -> float:
        """Get the price of a single token. Returns ``0.0`` if unavailable."""
        prices = await self.get_prices(coins=[coin], vs_currency=vs_currency)
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        sym = self.SYMBOL_MAP.get(cg_id, cg_id)
        return prices.get(sym, 0.0)

    async def get_coin_info(self, coin: str) -> Optional[dict]:
        """
        Full coin metadata (description, links, market data, …).

        *coin* can be an alias (``btc``) or CoinGecko ID (``bitcoin``).
        """
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        return await self._get(f"/coins/{cg_id}")

    async def search(self, query: str) -> list:
        """Search coins, categories, exchanges by keyword."""
        data = await self._get("/search", params={"query": query}) or {}
        return data.get("coins", [])

    async def get_market_chart(
        self,
        coin: str,
        days: int = 7,
        vs_currency: str = "usd",
    ) -> Optional[dict]:
        """
        Price / market-cap / volume chart data.

        Args:
            coin: Alias or CoinGecko ID.
            days: Number of days (1, 7, 30, 90, 365, ``max``).
            vs_currency: Fiat code.

        Returns:
            ``{"prices": [[ts, price], ...], "market_caps": [...], "total_volumes": [...]}``
        """
        cg_id = self.COIN_ID_MAP.get(coin.lower(), coin.lower())
        return await self._get(
            f"/coins/{cg_id}/market_chart",
            params={"vs_currency": vs_currency.lower(), "days": str(days)},
        )


# ---------------------------------------------------------------------------
#  CoinMarketCap
# ---------------------------------------------------------------------------

class CoinMarketCap(_BaseProvider):
    """
    CoinMarketCap price provider (requires free API key).

    Get a key at https://pro.coinmarketcap.com

    Example::

        cmc = CoinMarketCap(api_key="your-key")
        prices = await cmc.get_prices()                     # all 6 in USD
        sol    = await cmc.get_price("sol", "EUR")          # single token
        top    = await cmc.get_listings(limit=20)           # top 20 by mcap
        info   = await cmc.get_coin_info("BTC")             # metadata
    """

    SYMBOL_MAP: Dict[str, str] = {
        "btc": "BTC", "bitcoin": "BTC",
        "eth": "ETH", "evm": "ETH", "ethereum": "ETH",
        "bnb": "BNB", "bsc": "BNB", "binancecoin": "BNB",
        "sol": "SOL", "solana": "SOL",
        "trx": "TRX", "tron": "TRX",
        "ton": "TON", "the-open-network": "TON",
    }
    DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "TRX", "TON"]

    def __init__(self, api_key: str):
        super().__init__(
            "https://pro-api.coinmarketcap.com",
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
        )

    def _resolve_symbols(self, coins: Optional[List[str]] = None) -> List[str]:
        if not coins:
            return list(self.DEFAULT_SYMBOLS)
        syms = []
        for c in coins:
            s = self.SYMBOL_MAP.get(c.lower(), c.upper())
            syms.append(s)
        return syms

    async def get_prices(
        self,
        coins: Optional[List[str]] = None,
        vs_currency: str = "USD",
    ) -> Dict[str, float]:
        """
        Fetch latest prices.

        Args:
            coins: List of aliases (``btc``, ``eth``, ``bnb``, ``sol``, ``trx``, ``ton``).
            vs_currency: Fiat code (``USD``, ``EUR``, …).

        Returns:
            ``{"btc": 97000.0, "eth": 2600.0, "bnb": 600.0, ...}``
        """
        symbols = self._resolve_symbols(coins)
        data = await self._get(
            "/v2/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(symbols), "convert": vs_currency.upper()},
        )
        if not data:
            return {s.lower(): 0.0 for s in symbols}

        result: Dict[str, float] = {}
        quotes = data.get("data", {})
        for sym in symbols:
            entries = quotes.get(sym, [])
            if isinstance(entries, list) and entries:
                entry = entries[0]
            elif isinstance(entries, dict):
                entry = entries
            else:
                result[sym.lower()] = 0.0
                continue
            price = (
                entry.get("quote", {})
                .get(vs_currency.upper(), {})
                .get("price", 0)
            )
            result[sym.lower()] = float(price) if price else 0.0
        return result

    async def get_price(self, coin: str, vs_currency: str = "USD") -> float:
        """Get the price of a single token."""
        prices = await self.get_prices(coins=[coin], vs_currency=vs_currency)
        sym = self.SYMBOL_MAP.get(coin.lower(), coin.upper()).lower()
        return prices.get(sym, 0.0)

    async def get_listings(
        self,
        limit: int = 100,
        vs_currency: str = "USD",
    ) -> list:
        """
        Top cryptocurrencies by market cap.

        Returns:
            List of dicts with ``name``, ``symbol``, ``price``, ``market_cap``, etc.
        """
        data = await self._get(
            "/v1/cryptocurrency/listings/latest",
            params={"limit": str(limit), "convert": vs_currency.upper()},
        )
        if not data:
            return []
        raw = data.get("data", [])
        result = []
        for item in raw:
            q = item.get("quote", {}).get(vs_currency.upper(), {})
            result.append({
                "symbol": item.get("symbol", ""),
                "name": item.get("name", ""),
                "price": q.get("price", 0),
                "market_cap": q.get("market_cap", 0),
                "volume_24h": q.get("volume_24h", 0),
                "percent_change_24h": q.get("percent_change_24h", 0),
                "percent_change_7d": q.get("percent_change_7d", 0),
            })
        return result

    async def get_coin_info(self, coin: str) -> Optional[dict]:
        """
        Coin metadata (logo, description, urls, …).

        *coin* can be an alias (``btc``) or raw symbol (``BTC``).
        """
        sym = self.SYMBOL_MAP.get(coin.lower(), coin.upper())
        data = await self._get(
            "/v2/cryptocurrency/info",
            params={"symbol": sym},
        )
        if not data:
            return None
        entries = data.get("data", {}).get(sym, [])
        if isinstance(entries, list) and entries:
            return entries[0]
        if isinstance(entries, dict):
            return entries
        return None


# ---------------------------------------------------------------------------
#  DexScreener
# ---------------------------------------------------------------------------

class DexScreener(_BaseProvider):
    """
    DexScreener DEX aggregator (free, no API key).

    Example::

        ds = DexScreener()
        pairs = await ds.search("SOL/USDC")
        token = await ds.get_tokens("solana", "So111...112")
        pools = await ds.get_token_pools("solana", "So111...112")
        price = await ds.get_token_price("solana", "So111...112")
        pair  = await ds.get_pair("solana", "JUPyi...")
    """

    # Common chain IDs used in DexScreener
    CHAINS = {
        "ethereum": "ethereum",
        "eth": "ethereum",
        "evm": "ethereum",
        "bsc": "bsc",
        "solana": "solana",
        "sol": "solana",
        "tron": "tron",
        "trx": "tron",
        "ton": "ton",
        "base": "base",
        "arbitrum": "arbitrum",
        "polygon": "polygon",
        "avalanche": "avalanche",
    }

    def __init__(self):
        super().__init__("https://api.dexscreener.com")

    def _chain(self, chain_id: str) -> str:
        return self.CHAINS.get(chain_id.lower(), chain_id.lower())

    async def search(self, query: str) -> list:
        """
        Search pairs by token name, symbol, or address.

        Args:
            query: Search string (e.g. ``"SOL/USDC"``, ``"PEPE"``, token address).

        Returns:
            List of pair dicts with ``priceUsd``, ``volume``, ``liquidity``, etc.
        """
        data = await self._get("/latest/dex/search", params={"q": query})
        if not data:
            return []
        return data.get("pairs", [])

    async def get_pair(self, chain_id: str, pair_address: str) -> Optional[dict]:
        """
        Get a specific pair by chain and pair address.

        Args:
            chain_id: Chain alias (``solana``, ``ethereum``, ``bsc``, …).
            pair_address: DEX pair / pool address.
        """
        chain = self._chain(chain_id)
        data = await self._get(f"/latest/dex/pairs/{chain}/{pair_address}")
        if not data:
            return None
        pairs = data.get("pairs", [])
        return pairs[0] if pairs else None

    async def get_tokens(
        self,
        chain_id: str,
        token_addresses: str,
    ) -> list:
        """
        Get pairs for one or multiple token addresses (up to 30, comma-separated).

        Args:
            chain_id: Chain alias (``solana``, ``ethereum``, …).
            token_addresses: One or comma-separated token addresses.

        Returns:
            List of pair dicts.
        """
        chain = self._chain(chain_id)
        data = await self._get(f"/tokens/v1/{chain}/{token_addresses}")
        if isinstance(data, list):
            return data
        return []

    async def get_token_pools(
        self,
        chain_id: str,
        token_address: str,
    ) -> list:
        """
        Get all liquidity pools for a token.

        Args:
            chain_id: Chain alias.
            token_address: Token contract address.

        Returns:
            List of pool/pair dicts.
        """
        chain = self._chain(chain_id)
        data = await self._get(f"/token-pairs/v1/{chain}/{token_address}")
        if isinstance(data, list):
            return data
        return []

    async def get_token_price(
        self,
        chain_id: str,
        token_address: str,
    ) -> float:
        """
        Convenience: get USD price for a token from its highest-liquidity pair.

        Returns:
            Price in USD as float, or ``0.0`` if not found.
        """
        pairs = await self.get_tokens(chain_id, token_address)
        if not pairs:
            return 0.0
        # Pick the pair with the most liquidity
        best = max(
            pairs,
            key=lambda p: (p.get("liquidity") or {}).get("usd", 0),
            default=None,
        )
        if best and best.get("priceUsd"):
            return float(best["priceUsd"])
        return 0.0

    async def get_top_boosts(self) -> list:
        """Get tokens with most active boosts."""
        data = await self._get("/token-boosts/top/v1")
        if isinstance(data, list):
            return data
        return []


# ---------------------------------------------------------------------------
#  Backward-compatible module-level functions
# ---------------------------------------------------------------------------

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

    