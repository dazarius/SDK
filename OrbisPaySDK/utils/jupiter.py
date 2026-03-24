"""
Jupiter Solana DEX aggregator client (Metis Swap API v1 + Price API v2).

No API key required for public endpoints.

Example::

    from OrbisPaySDK.utils.jupiter import Jupiter

    jup = Jupiter()

    # Get swap quote
    quote = await jup.get_quote(
        input_mint="So11111111111111111111111111111111111111112",
        output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        amount=1_000_000_000,            # 1 SOL in lamports
        slippage_bps=50,                 # 0.5%
    )

    # Build swap transaction
    swap = await jup.get_swap(
        quote_response=quote,
        user_public_key="YourSolanaWallet…",
    )

    # Get token price in USD
    price = await jup.get_price("So11111111111111111111111111111111111111112")

    # List all supported tokens
    tokens = await jup.get_token_list()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from OrbisPaySDK.utils.utils import _BaseProvider


# Well-known Solana token mint addresses
KNOWN_MINTS: Dict[str, str] = {
    "sol": "So11111111111111111111111111111111111111112",
    "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "usdt": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "bonk": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "jup": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "ray": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "wif": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "jto": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
}


class Jupiter(_BaseProvider):
    """
    Jupiter DEX aggregator client.

    Uses:
    - Metis Swap API: ``https://api.jup.ag/swap/v1``
    - Price API: ``https://api.jup.ag/price/v2``
    - Token list: ``https://token.jup.ag``
    """

    def __init__(self, api_key: Optional[str] = None):
        # Swap API base — the price / token endpoints use different bases,
        # handled per-method.
        headers: dict = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__("https://api.jup.ag", headers)

    @staticmethod
    def _resolve_mint(token: str) -> str:
        """Resolve a shorthand alias to a full mint address."""
        return KNOWN_MINTS.get(token.lower(), token)

    # ============================== SWAP API ==============================

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        swap_mode: str = "ExactIn",
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
        max_accounts: Optional[int] = None,
        platform_fee_bps: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get a swap quote from Jupiter.

        Args:
            input_mint: Input token mint address (or alias like ``sol``, ``usdc``).
            output_mint: Output token mint address (or alias).
            amount: Amount in smallest unit (lamports for SOL, etc.).
            slippage_bps: Slippage tolerance in basis points (default 50 = 0.5%).
            swap_mode: ``ExactIn`` | ``ExactOut``.
            only_direct_routes: Skip multi-hop routes.
            as_legacy_transaction: Use legacy tx instead of versioned.
            max_accounts: Limit accounts for composability.
            platform_fee_bps: Platform referral fee in bps.

        Returns:
            Quote dict with ``inAmount``, ``outAmount``, ``otherAmountThreshold``,
            ``routePlan``, ``priceImpactPct``, etc.
        """
        params: dict = {
            "inputMint": self._resolve_mint(input_mint),
            "outputMint": self._resolve_mint(output_mint),
            "amount": str(amount),
            "slippageBps": slippage_bps,
            "swapMode": swap_mode,
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "asLegacyTransaction": str(as_legacy_transaction).lower(),
        }
        if max_accounts is not None:
            params["maxAccounts"] = max_accounts
        if platform_fee_bps is not None:
            params["platformFeeBps"] = platform_fee_bps

        return await self._get("/swap/v1/quote", params=params)

    async def get_swap(
        self,
        quote_response: dict,
        user_public_key: str,
        wrap_and_unwrap_sol: bool = True,
        use_shared_accounts: bool = True,
        fee_account: Optional[str] = None,
        compute_unit_price_micro_lamports: Optional[int] = None,
        as_legacy_transaction: bool = False,
        use_token_ledger: bool = False,
        destination_token_account: Optional[str] = None,
        dynamic_compute_unit_limit: bool = False,
        priority_level_with_max_lamports: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Build a swap transaction from a quote.

        Args:
            quote_response: The quote dict returned by :meth:`get_quote`.
            user_public_key: Solana wallet public key (base58).
            wrap_and_unwrap_sol: Auto-wrap/unwrap SOL.
            use_shared_accounts: Allow Jupiter to use shared intermediary accounts.
            fee_account: Token account for platform fees.
            compute_unit_price_micro_lamports: Priority fee.
            as_legacy_transaction: Use legacy tx.
            use_token_ledger: Use token ledger for exact output.
            destination_token_account: Custom destination token account.
            dynamic_compute_unit_limit: Let Jupiter estimate CU.
            priority_level_with_max_lamports: Priority fee config dict.

        Returns:
            Dict with ``swapTransaction`` (base64-encoded), ``lastValidBlockHeight``,
            ``prioritizationFeeLamports``, etc.
        """
        import httpx, asyncio as _aio

        body: dict = {
            "quoteResponse": quote_response,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": wrap_and_unwrap_sol,
            "useSharedAccounts": use_shared_accounts,
            "asLegacyTransaction": as_legacy_transaction,
            "useTokenLedger": use_token_ledger,
            "dynamicComputeUnitLimit": dynamic_compute_unit_limit,
        }
        if fee_account:
            body["feeAccount"] = fee_account
        if compute_unit_price_micro_lamports is not None:
            body["computeUnitPriceMicroLamports"] = compute_unit_price_micro_lamports
        if destination_token_account:
            body["destinationTokenAccount"] = destination_token_account
        if priority_level_with_max_lamports:
            body["prioritizationFeeLamports"] = priority_level_with_max_lamports

        url = f"{self._base_url}/swap/v1/swap"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=body, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
        return None

    async def get_swap_instructions(
        self,
        quote_response: dict,
        user_public_key: str,
        wrap_and_unwrap_sol: bool = True,
    ) -> Optional[dict]:
        """
        Get individual swap instructions instead of a serialized transaction.

        Useful for composing Jupiter swap into your own transaction.

        Returns:
            Dict with ``setupInstructions``, ``swapInstruction``,
            ``cleanupInstruction``, ``addressLookupTableAddresses``, etc.
        """
        import httpx, asyncio as _aio

        body: dict = {
            "quoteResponse": quote_response,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": wrap_and_unwrap_sol,
        }

        url = f"{self._base_url}/swap/v1/swap-instructions"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=body, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
        return None

    # ============================== PRICE API ==============================

    async def get_price(
        self,
        token: str,
        vs_token: Optional[str] = None,
    ) -> float:
        """
        Get price for a single token in USD (or vs another token).

        Args:
            token: Mint address or alias (``sol``, ``usdc``, …).
            vs_token: Optional quote token mint / alias. Defaults to USD.

        Returns:
            Price as float, or ``0.0`` if unavailable.
        """
        prices = await self.get_prices([token], vs_token=vs_token)
        mint = self._resolve_mint(token)
        return prices.get(mint, 0.0)

    async def get_prices(
        self,
        tokens: List[str],
        vs_token: Optional[str] = None,
        show_extra_info: bool = False,
    ) -> Dict[str, float]:
        """
        Get prices for multiple tokens.

        Args:
            tokens: List of mint addresses or aliases.
            vs_token: Optional quote token mint / alias.
            show_extra_info: Include extra fields (buy/sell price, confidence).

        Returns:
            ``{"mint_address": price, ...}``
        """
        mints = [self._resolve_mint(t) for t in tokens]
        params: dict = {"ids": ",".join(mints)}
        if vs_token:
            params["vsToken"] = self._resolve_mint(vs_token)
        if show_extra_info:
            params["showExtraInfo"] = "true"

        data = await self._request(
            "GET",
            "",
            params=params,
        )
        # Override base_url for this call
        import httpx, asyncio as _aio

        url = "https://api.jup.ag/price/v2"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return {m: 0.0 for m in mints}
                resp.raise_for_status()
                data = resp.json()
                break
        else:
            return {m: 0.0 for m in mints}

        result: Dict[str, float] = {}
        price_data = data.get("data", {})
        for mint in mints:
            entry = price_data.get(mint)
            if entry and entry.get("price"):
                result[mint] = float(entry["price"])
            else:
                result[mint] = 0.0
        return result

    # ============================== TOKEN LIST ==============================

    async def get_token_list(self, list_type: str = "strict") -> List[dict]:
        """
        Get Jupiter's curated token list.

        Args:
            list_type: ``strict`` (verified) or ``all`` (includes unverified).

        Returns:
            List of token dicts with ``address``, ``symbol``, ``name``,
            ``decimals``, ``logoURI``, etc.
        """
        import httpx, asyncio as _aio

        url = f"https://token.jup.ag/{list_type}"
        for attempt in range(self._RETRIES):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 429:
                    if attempt < self._RETRIES - 1:
                        await _aio.sleep(2 ** attempt)
                        continue
                    return []
                resp.raise_for_status()
                return resp.json()
        return []

    async def search_token(self, query: str, list_type: str = "strict") -> List[dict]:
        """
        Search the token list by symbol or name.

        Args:
            query: Search string (case-insensitive).
            list_type: ``strict`` or ``all``.

        Returns:
            Matching token dicts.
        """
        tokens = await self.get_token_list(list_type)
        q = query.lower()
        return [
            t for t in tokens
            if q in t.get("symbol", "").lower()
            or q in t.get("name", "").lower()
            or q in t.get("address", "").lower()
        ]
