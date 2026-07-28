"""
DexScreener API client — DEX pair searching, pool liquidity & token price data.

Public API requiring no key.

Example::

    from OrbisPaySDK.utils.dexscreener import DexScreener

    ds = DexScreener()
    pairs = await ds.search("SOL/USDC")
    token = await ds.get_tokens("solana", "So111…112")
    pools = await ds.get_token_pools("solana", "So111…112")
    price = await ds.get_token_price("solana", "So111…112")
    pair  = await ds.get_pair("solana", "0x…")
"""

from __future__ import annotations

from typing import Optional
from OrbisPaySDK.utils.provider import _BaseProvider


class DexScreener(_BaseProvider):
    """
    DexScreener DEX aggregator (free, no API key).
    """

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
