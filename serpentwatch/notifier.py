"""Telegram delivery. The only data that ever leaves the machine is the alert photo."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout: float = 15.0):
        self._token = token
        self._chat_id = chat_id
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    def send_photo(self, jpeg_bytes: bytes, caption: str) -> bool:
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendPhoto"
        try:
            response = requests.post(
                url,
                data={"chat_id": self._chat_id, "caption": caption},
                files={"photo": ("alert.jpg", jpeg_bytes, "image/jpeg")},
                timeout=self._timeout,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            # Log the exception type only: its message embeds the URL, which contains the bot token.
            log.error("Telegram delivery failed (%s)", type(exc).__name__)
            return False
