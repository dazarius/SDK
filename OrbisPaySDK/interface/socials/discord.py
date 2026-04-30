import httpx
from typing import Optional, List


class DiscordNotifier:
    """
    Discord notification wrapper for OrbisPaySDK.
    Supports both webhook-based messages and bot token channel messages.

    Usage (webhook):
        dc = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/...")
        await dc.send_message("Hello!")
        await dc.send_tx_notification(tx_hash="0xabc...", amount="1.5", symbol="ETH", to="0x123...")

    Usage (bot token):
        dc = DiscordNotifier(bot_token="Bot TOKEN", channel_id="123456789")
        await dc.send_message("Hello!")
    """

    API_BASE = "https://discord.com/api/v10"

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        """
        Args:
            webhook_url (str): Discord webhook URL. Preferred for simple notifications.
            bot_token   (str): Bot token (include "Bot " prefix or pass bare token — added automatically).
            channel_id  (str): Default channel ID used with bot_token mode.
        """
        self.webhook_url = webhook_url
        self.channel_id = channel_id
        self._bot_token = (
            bot_token if (bot_token or "").startswith("Bot ") else f"Bot {bot_token}"
        ) if bot_token else None

    def set_params(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        """Update instance parameters at runtime."""
        if webhook_url:
            self.webhook_url = webhook_url
        if bot_token:
            self._bot_token = bot_token if bot_token.startswith("Bot ") else f"Bot {bot_token}"
        if channel_id:
            self.channel_id = channel_id

    def _headers(self) -> dict:
        if not self._bot_token:
            raise ValueError("bot_token is required for this operation.")
        return {"Authorization": self._bot_token, "Content-Type": "application/json"}

    def _resolve_channel(self, channel_id: Optional[str]) -> str:
        result = channel_id or self.channel_id
        if not result:
            raise ValueError("channel_id is required — set it in the constructor or pass it explicitly.")
        return result

    # ── Webhook mode ───────────────────────────────────────────────────────────

    async def send_message(
        self,
        content: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> dict:
        """
        Send a plain text message via webhook or bot token.

        Args:
            content    (str):  Message text.
            username   (str):  Override webhook display name. Optional (webhook only).
            avatar_url (str):  Override webhook avatar URL. Optional (webhook only).
            channel_id (str):  Target channel (bot token mode). Falls back to self.channel_id.

        Returns:
            dict: Discord API response.
        """
        if self.webhook_url:
            payload: dict = {"content": content}
            if username:
                payload["username"] = username
            if avatar_url:
                payload["avatar_url"] = avatar_url
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json=payload)
                return resp.json() if resp.content else {"status": resp.status_code}

        ch = self._resolve_channel(channel_id)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/channels/{ch}/messages",
                json={"content": content},
                headers=self._headers(),
            )
            return resp.json()

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x5865F2,
        fields: Optional[List[dict]] = None,
        footer: Optional[str] = None,
        channel_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> dict:
        """
        Send a rich embed message.

        Args:
            title       (str):       Embed title.
            description (str):       Embed description.
            color       (int):       Embed sidebar color as integer. Default: Discord blurple.
            fields      (list[dict]): List of {"name": str, "value": str, "inline": bool}. Optional.
            footer      (str):       Footer text. Optional.
            channel_id  (str):       Target channel (bot mode). Falls back to self.channel_id.
            username    (str):       Override webhook display name (webhook mode). Optional.

        Returns:
            dict: Discord API response.
        """
        embed: dict = {
            "title": title,
            "description": description,
            "color": color,
        }
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}

        payload: dict = {"embeds": [embed]}
        if username:
            payload["username"] = username

        if self.webhook_url:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json=payload)
                return resp.json() if resp.content else {"status": resp.status_code}

        ch = self._resolve_channel(channel_id)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/channels/{ch}/messages",
                json=payload,
                headers=self._headers(),
            )
            return resp.json()

    async def send_tx_notification(
        self,
        tx_hash: str,
        amount: str,
        symbol: str,
        to: str,
        chain: Optional[str] = None,
        explorer_url: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> dict:
        """
        Send a formatted transaction notification embed.

        Args:
            tx_hash      (str):  Transaction hash.
            amount       (str):  Human-readable amount.
            symbol       (str):  Token/coin symbol.
            to           (str):  Recipient address.
            chain        (str):  Network name. Optional.
            explorer_url (str):  Explorer link for the tx. Optional.
            channel_id   (str):  Override channel_id.

        Returns:
            dict: Discord API response.
        """
        fields = [
            {"name": "Amount", "value": f"`{amount} {symbol}`", "inline": True},
            {"name": "Recipient", "value": f"`{to}`", "inline": False},
        ]
        if chain:
            fields.append({"name": "Network", "value": chain, "inline": True})
        if explorer_url:
            fields.append({"name": "Explorer", "value": f"[View tx]({explorer_url})", "inline": True})
        else:
            fields.append({"name": "Tx Hash", "value": f"`{tx_hash}`", "inline": False})

        return await self.send_embed(
            title="✅ Transaction sent",
            description="",
            color=0x57F287,
            fields=fields,
            channel_id=channel_id,
        )

    async def send_cheque_notification(
        self,
        cheque_id: str,
        amount: str,
        symbol: str,
        recipient: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> dict:
        """
        Send a formatted cheque creation notification embed.

        Args:
            cheque_id  (str):  Cheque identifier (hex string).
            amount     (str):  Human-readable amount.
            symbol     (str):  Token/coin symbol.
            recipient  (str):  Recipient address or name. Optional.
            channel_id (str):  Override channel_id.

        Returns:
            dict: Discord API response.
        """
        fields = [
            {"name": "Amount", "value": f"`{amount} {symbol}`", "inline": True},
            {"name": "Cheque ID", "value": f"`{cheque_id}`", "inline": False},
        ]
        if recipient:
            fields.append({"name": "Recipient", "value": f"`{recipient}`", "inline": False})

        return await self.send_embed(
            title="🧾 Cheque created",
            description="",
            color=0xFEE75C,
            fields=fields,
            channel_id=channel_id,
        )

    # ── Bot-only operations ────────────────────────────────────────────────────

    async def get_channel(self, channel_id: Optional[str] = None) -> dict:
        """
        Returns information about a channel.

        Args:
            channel_id (str): Channel to query. Falls back to self.channel_id.

        Returns:
            dict: Discord API channel object.
        """
        ch = self._resolve_channel(channel_id)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/channels/{ch}",
                headers=self._headers(),
            )
            return resp.json()

    async def get_guild_members(self, guild_id: str, limit: int = 100) -> list:
        """
        Returns a list of guild members.

        Args:
            guild_id (str): Guild (server) ID.
            limit    (int): Max members to return (1–1000). Default: 100.

        Returns:
            list[dict]: List of Discord member objects.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/guilds/{guild_id}/members",
                params={"limit": limit},
                headers=self._headers(),
            )
            return resp.json()
