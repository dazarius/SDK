"""
0x Swap API v2 client — EVM DEX aggregation (Permit2 + AllowanceHolder).

Requires a 0x API key (free at https://dashboard.0x.org).

Example::

    from OrbisPaySDK.utils.zerox import ZeroX

    zx = ZeroX(api_key="your-0x-api-key")

    # Indicative price
    price = await zx.get_price(
        chain_id=1,
        sell_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        buy_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",   # USDC
        sell_amount="1000000000000000000",                          # 1 ETH
    )

    # Firm quote (ready for on-chain execution)
    quote = await zx.get_quote(
        chain_id=1,
        sell_token="WETH",
        buy_token="USDC",
        sell_amount="1000000000000000000",
        taker="0xYourWallet…",
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from OrbisPaySDK.utils.utils import _BaseProvider


# Well-known ERC-20 addresses on popular chains
KNOWN_TOKENS: Dict[int, Dict[str, str]] = {
    # Ethereum mainnet (chain_id=1)
    1: {
        "eth": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdt": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "dai": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "wbtc": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    },
    # Polygon (chain_id=137)
    137: {
        "matic": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "wmatic": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "usdt": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "weth": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    },
    # Arbitrum One (chain_id=42161)
    42161: {
        "eth": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "weth": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "arb": "0x912CE59144191C1204E64559FE8253a0e49E6548",
    },
    # BSC (chain_id=56)
    56: {
        "bnb": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "wbnb": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "usdc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "usdt": "0x55d398326f99059fF775485246999027B3197955",
        "busd": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    },
    # Base (chain_id=8453)
    8453: {
        "eth": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "weth": "0x4200000000000000000000000000000000000006",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
    # Optimism (chain_id=10)
    10: {
        "eth": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "weth": "0x4200000000000000000000000000000000000006",
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "op": "0x4200000000000000000000000000000000000042",
    },
    # Avalanche C-Chain (chain_id=43114)
    43114: {
        "avax": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "wavax": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "usdt": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
    },
}

# Supported chain IDs for 0x API v2
SUPPORTED_CHAINS: Dict[str, int] = {
    "ethereum": 1, "eth": 1,
    "polygon": 137, "matic": 137,
    "arbitrum": 42161, "arb": 42161,
    "bsc": 56, "bnb": 56,
    "base": 8453,
    "optimism": 10, "op": 10,
    "avalanche": 43114, "avax": 43114,
}


class ZeroX(_BaseProvider):
    """
    0x Swap API v2 wrapper.

    Supports Permit2 (recommended) and AllowanceHolder flows.
    """

    def __init__(self, api_key: str):
        super().__init__(
            "https://api.0x.org",
            headers={"0x-api-key": api_key, "0x-version": "2"},
        )

    @staticmethod
    def _resolve_chain_id(chain: Any) -> int:
        """Resolve chain alias to integer chain ID."""
        if isinstance(chain, int):
            return chain
        cid = SUPPORTED_CHAINS.get(str(chain).lower())
        if cid is None:
            raise ValueError(
                f"Unknown chain '{chain}'. Supported: {list(SUPPORTED_CHAINS.keys())}"
            )
        return cid

    @staticmethod
    def _resolve_token(token: str, chain_id: int) -> str:
        """Resolve a token alias to an address for a given chain."""
        chain_tokens = KNOWN_TOKENS.get(chain_id, {})
        return chain_tokens.get(token.lower(), token)

    # ============================== PERMIT2 FLOW ==============================

    async def get_price(
        self,
        chain_id: Any,
        sell_token: str,
        buy_token: str,
        sell_amount: Optional[str] = None,
        buy_amount: Optional[str] = None,
        taker: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get an **indicative price** (Permit2 flow).

        Use this for display purposes; it does NOT return a firm quote.

        Args:
            chain_id: Chain ID (int) or alias (``ethereum``, ``polygon``, …).
            sell_token: Sell token address or alias (``weth``, ``usdc``, …).
            buy_token: Buy token address or alias.
            sell_amount: Sell amount in smallest unit (provide one of
                         *sell_amount* / *buy_amount*).
            buy_amount: Buy amount in smallest unit.
            taker: Taker wallet address (optional for price).
            slippage_bps: Slippage tolerance in basis points.

        Returns:
            Price response dict with ``buyAmount``, ``sellAmount``,
            ``price``, ``estimatedGas``, ``route``, etc.
        """
        cid = self._resolve_chain_id(chain_id)
        params: dict = {
            "chainId": cid,
            "sellToken": self._resolve_token(sell_token, cid),
            "buyToken": self._resolve_token(buy_token, cid),
        }
        if sell_amount:
            params["sellAmount"] = sell_amount
        if buy_amount:
            params["buyAmount"] = buy_amount
        if taker:
            params["taker"] = taker
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps

        return await self._get("/swap/permit2/price", params=params)

    async def get_quote(
        self,
        chain_id: Any,
        sell_token: str,
        buy_token: str,
        sell_amount: Optional[str] = None,
        buy_amount: Optional[str] = None,
        taker: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get a **firm quote** (Permit2 flow).

        The response contains everything needed to execute the swap:
        ``transaction``, ``permit2`` data for signing, ``route``, etc.

        Args:
            chain_id: Chain ID or alias.
            sell_token: Sell token address or alias.
            buy_token: Buy token address or alias.
            sell_amount: Amount in smallest unit (one of *sell_amount* / *buy_amount*).
            buy_amount: Amount in smallest unit.
            taker: **Required** — wallet address that will execute the swap.
            slippage_bps: Slippage tolerance in basis points.

        Returns:
            Quote dict with ``transaction`` (to, data, value, gas),
            ``permit2`` (eip712 data to sign), ``buyAmount``, ``sellAmount``,
            ``route``, ``tokenMetadata``, etc.
        """
        cid = self._resolve_chain_id(chain_id)
        params: dict = {
            "chainId": cid,
            "sellToken": self._resolve_token(sell_token, cid),
            "buyToken": self._resolve_token(buy_token, cid),
        }
        if sell_amount:
            params["sellAmount"] = sell_amount
        if buy_amount:
            params["buyAmount"] = buy_amount
        if taker:
            params["taker"] = taker
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps

        return await self._get("/swap/permit2/quote", params=params)

    # ============================== ALLOWANCE-HOLDER FLOW ==============================

    async def get_price_allowance(
        self,
        chain_id: Any,
        sell_token: str,
        buy_token: str,
        sell_amount: Optional[str] = None,
        buy_amount: Optional[str] = None,
        taker: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get an indicative price using the AllowanceHolder flow.

        Same args as :meth:`get_price`.
        """
        cid = self._resolve_chain_id(chain_id)
        params: dict = {
            "chainId": cid,
            "sellToken": self._resolve_token(sell_token, cid),
            "buyToken": self._resolve_token(buy_token, cid),
        }
        if sell_amount:
            params["sellAmount"] = sell_amount
        if buy_amount:
            params["buyAmount"] = buy_amount
        if taker:
            params["taker"] = taker
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps

        return await self._get("/swap/allowance-holder/price", params=params)

    async def get_quote_allowance(
        self,
        chain_id: Any,
        sell_token: str,
        buy_token: str,
        sell_amount: Optional[str] = None,
        buy_amount: Optional[str] = None,
        taker: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get a firm quote using the AllowanceHolder flow.

        The response contains ``transaction`` (to, data, value, gas) ready
        to be submitted via ``eth_sendTransaction`` after token approval.

        Same args as :meth:`get_quote`.
        """
        cid = self._resolve_chain_id(chain_id)
        params: dict = {
            "chainId": cid,
            "sellToken": self._resolve_token(sell_token, cid),
            "buyToken": self._resolve_token(buy_token, cid),
        }
        if sell_amount:
            params["sellAmount"] = sell_amount
        if buy_amount:
            params["buyAmount"] = buy_amount
        if taker:
            params["taker"] = taker
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps

        return await self._get("/swap/allowance-holder/quote", params=params)

    # ============================== HELPERS ==============================

    @staticmethod
    def supported_chains() -> Dict[str, int]:
        """Return mapping of chain aliases → chain IDs."""
        return dict(SUPPORTED_CHAINS)

    @staticmethod
    def known_tokens(chain_id: int) -> Dict[str, str]:
        """Return known token aliases for a given chain."""
        return dict(KNOWN_TOKENS.get(chain_id, {}))
