import httpx
from typing import Optional, Union


class TelegramNotifier:
    """
    Telegram Bot API wrapper for OrbisPaySDK notifications.

    Usage:
        tg = TelegramNotifier(token="123:ABC", chat_id="@mychannel")
        await tg.send_message("Hello!")
        await tg.send_tx_notification(tx_hash="0xabc...", amount="1.5", symbol="ETH", to="0x123...")
    """

    API_BASE = "https://api.telegram.org/bot{token}"

    def __init__(
        self,
        token: str,
        chat_id: Optional[Union[str, int]] = None,
        parse_mode: str = "HTML",
    ):
        """
        Args:
            token      (str):       Telegram Bot token from @BotFather.
            chat_id    (str | int): Default chat/channel ID or @username. Can be overridden per call.
            parse_mode (str):       Default parse mode — "HTML" or "Markdown". Default: "HTML".
        """
        self.token = token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self._base = self.API_BASE.format(token=token)

    def set_params(
        self,
        token: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        parse_mode: Optional[str] = None,
    ):
        """Update instance parameters at runtime."""
        if token:
            self.token = token
            self._base = self.API_BASE.format(token=token)
        if chat_id is not None:
            self.chat_id = chat_id
        if parse_mode:
            self.parse_mode = parse_mode

    def _resolve_chat(self, chat_id: Optional[Union[str, int]]) -> Union[str, int]:
        result = chat_id if chat_id is not None else self.chat_id
        if result is None:
            raise ValueError("chat_id is required — set it in the constructor or pass it explicitly.")
        return result

    async def send_message(
        self,
        text: str,
        chat_id: Optional[Union[str, int]] = None,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
        disable_notification: bool = False,
    ) -> dict:
        """
        Send a plain or HTML/Markdown text message.

        Args:
            text                      (str):           Message text (supports HTML/Markdown tags).
            chat_id                   (str | int):     Target chat. Falls back to self.chat_id.
            parse_mode                (str):           "HTML" or "Markdown". Falls back to self.parse_mode.
            disable_web_page_preview  (bool):          Suppress link previews. Default: True.
            disable_notification      (bool):          Silent message. Default: False.

        Returns:
            dict: Telegram API response.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/sendMessage",
                json={
                    "chat_id": self._resolve_chat(chat_id),
                    "text": text,
                    "parse_mode": parse_mode or self.parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                    "disable_notification": disable_notification,
                },
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
        chat_id: Optional[Union[str, int]] = None,
    ) -> dict:
        """
        Send a formatted transaction confirmation notification.

        Args:
            tx_hash      (str):  Transaction hash.
            amount       (str):  Human-readable amount (e.g. "1.5").
            symbol       (str):  Token/coin symbol (e.g. "ETH", "USDT").
            to           (str):  Recipient address.
            chain        (str):  Network name shown in the message. Optional.
            explorer_url (str):  Full explorer URL for the tx. Optional.
            chat_id      (str | int): Override default chat_id.

        Returns:
            dict: Telegram API response.
        """
        chain_line = f"\n🌐 <b>Network:</b> {chain}" if chain else ""
        link_line = f"\n🔗 <a href='{explorer_url}'>View on explorer</a>" if explorer_url else \
                    f"\n🔗 <b>Tx:</b> <code>{tx_hash}</code>"

        text = (
            f"✅ <b>Transaction sent</b>\n"
            f"💸 <b>Amount:</b> {amount} {symbol}\n"
            f"📬 <b>To:</b> <code>{to}</code>"
            f"{chain_line}"
            f"{link_line}"
        )
        return await self.send_message(text, chat_id=chat_id)

    async def send_cheque_notification(
        self,
        cheque_id: str,
        amount: str,
        symbol: str,
        recipient: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
    ) -> dict:
        """
        Send a formatted cheque creation notification.

        Args:
            cheque_id  (str):       Cheque identifier (hex string).
            amount     (str):       Human-readable amount.
            symbol     (str):       Token/coin symbol.
            recipient  (str):       Recipient address or name. Optional.
            chat_id    (str | int): Override default chat_id.

        Returns:
            dict: Telegram API response.
        """
        recipient_line = f"\n📬 <b>Recipient:</b> <code>{recipient}</code>" if recipient else ""
        text = (
            f"🧾 <b>Cheque created</b>\n"
            f"💸 <b>Amount:</b> {amount} {symbol}"
            f"{recipient_line}\n"
            f"🆔 <b>ID:</b> <code>{cheque_id}</code>"
        )
        return await self.send_message(text, chat_id=chat_id)

    async def send_photo(
        self,
        photo: str,
        caption: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        parse_mode: Optional[str] = None,
    ) -> dict:
        """
        Send a photo by URL or file_id with an optional caption.

        Args:
            photo      (str):       URL or Telegram file_id of the photo.
            caption    (str):       Caption text. Optional.
            chat_id    (str | int): Override default chat_id.
            parse_mode (str):       "HTML" or "Markdown".

        Returns:
            dict: Telegram API response.
        """
        payload: dict = {
            "chat_id": self._resolve_chat(chat_id),
            "photo": photo,
            "parse_mode": parse_mode or self.parse_mode,
        }
        if caption:
            payload["caption"] = caption

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self._base}/sendPhoto", json=payload)
            return resp.json()

    async def get_me(self) -> dict:
        """
        Returns basic information about the bot.

        Returns:
            dict: Telegram API result with bot info.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base}/getMe")
            return resp.json()

    async def get_chat(self, chat_id: Optional[Union[str, int]] = None) -> dict:
        """
        Returns information about a chat.

        Args:
            chat_id (str | int): Chat to query. Falls back to self.chat_id.

        Returns:
            dict: Telegram API result with chat info.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/getChat",
                params={"chat_id": self._resolve_chat(chat_id)},
            )
            return resp.json()
