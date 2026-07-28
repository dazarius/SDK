"""
Base HTTP Provider class for OrbisPay SDK integrations.
"""

from __future__ import annotations

import asyncio as _aio
from typing import Any, Dict, Optional
import httpx


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
