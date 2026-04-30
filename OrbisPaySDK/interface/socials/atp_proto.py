import httpx
import time
from typing import Optional, List, Dict, Any


class ATProto:
    """
    AT Protocol (Bluesky) wrapper for OrbisPaySDK.
    Supports authentication, posting, profile lookups, and payment notifications.

    Usage:
        atp = ATProto(handle="user.bsky.social", password="app-password")
        await atp.login()
        await atp.create_post("Hello from OrbisPaySDK!")
        await atp.send_tx_notification(tx_hash="0xabc...", amount="1.5", symbol="ETH")
    """

    def __init__(
        self,
        handle: Optional[str] = None,
        password: Optional[str] = None,
        pds_url: str = "https://bsky.social",
    ):
        """
        Args:
            handle   (str): Bluesky handle (e.g. "user.bsky.social") or DID.
            password (str): App password generated in Bluesky settings.
            pds_url  (str): PDS (Personal Data Server) URL. Default: Bluesky mainnet.
        """
        self.handle = handle
        self.password = password
        self.pds_url = pds_url.rstrip("/")

        self._access_jwt: Optional[str] = None
        self._refresh_jwt: Optional[str] = None
        self._did: Optional[str] = None

    def set_params(
        self,
        handle: Optional[str] = None,
        password: Optional[str] = None,
        pds_url: Optional[str] = None,
    ):
        """Update instance parameters at runtime. Clears existing session tokens."""
        if handle:
            self.handle = handle
            self._access_jwt = None
            self._refresh_jwt = None
            self._did = None
        if password:
            self.password = password
        if pds_url:
            self.pds_url = pds_url.rstrip("/")

    def _xrpc(self, method: str) -> str:
        return f"{self.pds_url}/xrpc/{method}"

    def _auth_headers(self) -> dict:
        if not self._access_jwt:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self._access_jwt}"}

    @property
    def is_authenticated(self) -> bool:
        return self._access_jwt is not None

    # ── Auth ───────────────────────────────────────────────────────────────────

    async def login(self) -> dict:
        """
        Authenticate with the PDS using handle + app password.
        Stores access and refresh JWTs for subsequent calls.

        Returns:
            dict: Session info including DID, handle, and accessJwt.

        Raises:
            ValueError: If login fails.
        """
        if not self.handle or not self.password:
            raise ValueError("handle and password are required.")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.server.createSession"),
                json={"identifier": self.handle, "password": self.password},
            )
            data = resp.json()
            if resp.status_code != 200:
                raise ValueError(f"Login failed: {data}")

            self._access_jwt = data["accessJwt"]
            self._refresh_jwt = data["refreshJwt"]
            self._did = data["did"]
            return data

    async def refresh_session(self) -> dict:
        """
        Refresh the access token using the stored refresh JWT.

        Returns:
            dict: New session info.
        """
        if not self._refresh_jwt:
            raise ValueError("No refresh token. Call login() first.")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.server.refreshSession"),
                headers={"Authorization": f"Bearer {self._refresh_jwt}"},
            )
            data = resp.json()
            if resp.status_code != 200:
                raise ValueError(f"Session refresh failed: {data}")

            self._access_jwt = data["accessJwt"]
            self._refresh_jwt = data["refreshJwt"]
            return data

    # ── Posts ──────────────────────────────────────────────────────────────────

    async def create_post(
        self,
        text: str,
        reply_to: Optional[Dict[str, Any]] = None,
        langs: Optional[List[str]] = None,
    ) -> dict:
        """
        Create a new post (skeet) on Bluesky.

        Args:
            text     (str):  Post text. Max 300 graphemes.
            reply_to (dict): Reply reference — {"root": {"uri": ..., "cid": ...}, "parent": {...}}.
            langs    (list): Language tags e.g. ["en"]. Optional.

        Returns:
            dict: Created record with uri and cid.
        """
        record: Dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": _now_iso(),
        }
        if reply_to:
            record["reply"] = reply_to
        if langs:
            record["langs"] = langs

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.repo.createRecord"),
                json={
                    "repo": self._did,
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                headers=self._auth_headers(),
            )
            data = resp.json()
            if resp.status_code != 200:
                raise ValueError(f"Post failed: {data}")
            return data

    async def delete_post(self, rkey: str) -> dict:
        """
        Delete a post by its record key.

        Args:
            rkey (str): The record key from the post URI (last segment after '/').

        Returns:
            dict: API response.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.repo.deleteRecord"),
                json={
                    "repo": self._did,
                    "collection": "app.bsky.feed.post",
                    "rkey": rkey,
                },
                headers=self._auth_headers(),
            )
            return resp.json() if resp.content else {"status": resp.status_code}

    async def send_tx_notification(
        self,
        tx_hash: str,
        amount: str,
        symbol: str,
        to: Optional[str] = None,
        chain: Optional[str] = None,
        explorer_url: Optional[str] = None,
    ) -> dict:
        """
        Post a formatted transaction notification to Bluesky.

        Args:
            tx_hash      (str):  Transaction hash.
            amount       (str):  Human-readable amount.
            symbol       (str):  Token/coin symbol.
            to           (str):  Recipient address. Optional.
            chain        (str):  Network name. Optional.
            explorer_url (str):  Explorer URL for the tx. Optional.

        Returns:
            dict: Created post record.
        """
        parts = [f"✅ Sent {amount} {symbol}"]
        if to:
            parts.append(f"→ {_truncate_addr(to)}")
        if chain:
            parts.append(f"on {chain}")
        if explorer_url:
            parts.append(f"🔗 {explorer_url}")
        else:
            parts.append(f"tx: {_truncate_addr(tx_hash)}")

        text = "\n".join(parts)
        return await self.create_post(text)

    async def send_cheque_notification(
        self,
        cheque_id: str,
        amount: str,
        symbol: str,
        recipient: Optional[str] = None,
    ) -> dict:
        """
        Post a formatted cheque creation notification to Bluesky.

        Args:
            cheque_id  (str):  Cheque identifier.
            amount     (str):  Human-readable amount.
            symbol     (str):  Token/coin symbol.
            recipient  (str):  Recipient address or name. Optional.

        Returns:
            dict: Created post record.
        """
        parts = [f"🧾 Cheque created: {amount} {symbol}"]
        if recipient:
            parts.append(f"→ {_truncate_addr(recipient)}")
        parts.append(f"ID: {cheque_id[:16]}...")

        text = "\n".join(parts)
        return await self.create_post(text)

    # ── Profiles & social ──────────────────────────────────────────────────────

    async def get_profile(self, actor: Optional[str] = None) -> dict:
        """
        Returns the profile for a handle or DID.

        Args:
            actor (str): Handle or DID to query. Falls back to self.handle.

        Returns:
            dict: Profile object with did, handle, displayName, description, etc.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._xrpc("app.bsky.actor.getProfile"),
                params={"actor": actor or self.handle},
                headers=self._auth_headers(),
            )
            return resp.json()

    async def resolve_handle(self, handle: str) -> str:
        """
        Resolves a handle to its DID.

        Args:
            handle (str): Bluesky handle (e.g. "user.bsky.social").

        Returns:
            str: The DID for the handle.

        Raises:
            ValueError: If resolution fails.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._xrpc("com.atproto.identity.resolveHandle"),
                params={"handle": handle},
            )
            data = resp.json()
            if resp.status_code != 200:
                raise ValueError(f"Handle resolution failed: {data}")
            return data["did"]

    async def get_timeline(self, limit: int = 20, cursor: Optional[str] = None) -> dict:
        """
        Returns the authenticated user's home timeline.

        Args:
            limit  (int):  Number of posts to return (1–100). Default: 20.
            cursor (str):  Pagination cursor from a previous response. Optional.

        Returns:
            dict: { "feed": list[dict], "cursor": str | None }
        """
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._xrpc("app.bsky.feed.getTimeline"),
                params=params,
                headers=self._auth_headers(),
            )
            return resp.json()

    async def get_author_feed(
        self,
        actor: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> dict:
        """
        Returns posts by a specific actor.

        Args:
            actor  (str):  Handle or DID. Falls back to self.handle.
            limit  (int):  Number of posts. Default: 20.
            cursor (str):  Pagination cursor. Optional.

        Returns:
            dict: { "feed": list[dict], "cursor": str | None }
        """
        params: dict = {"actor": actor or self.handle, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._xrpc("app.bsky.feed.getAuthorFeed"),
                params=params,
                headers=self._auth_headers(),
            )
            return resp.json()

    async def follow(self, did: str) -> dict:
        """
        Follow an account by DID.

        Args:
            did (str): DID of the account to follow.

        Returns:
            dict: Created follow record.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.repo.createRecord"),
                json={
                    "repo": self._did,
                    "collection": "app.bsky.graph.follow",
                    "record": {
                        "$type": "app.bsky.graph.follow",
                        "subject": did,
                        "createdAt": _now_iso(),
                    },
                },
                headers=self._auth_headers(),
            )
            return resp.json()

    async def like(self, uri: str, cid: str) -> dict:
        """
        Like a post.

        Args:
            uri (str): Post URI (e.g. "at://did:plc:.../app.bsky.feed.post/...").
            cid (str): Post CID.

        Returns:
            dict: Created like record.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xrpc("com.atproto.repo.createRecord"),
                json={
                    "repo": self._did,
                    "collection": "app.bsky.feed.like",
                    "record": {
                        "$type": "app.bsky.feed.like",
                        "subject": {"uri": uri, "cid": cid},
                        "createdAt": _now_iso(),
                    },
                },
                headers=self._auth_headers(),
            )
            return resp.json()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _truncate_addr(addr: str, head: int = 6, tail: int = 4) -> str:
    if len(addr) <= head + tail + 3:
        return addr
    return f"{addr[:head]}...{addr[-tail:]}"
