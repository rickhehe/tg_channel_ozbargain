import os
import logging

import httpx


LOGGER = logging.getLogger(__name__)


def send_telegram_message(chat_id, text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    with httpx.Client(timeout=10, follow_redirects=True) as client:
        response = client.post(
            url,
            data={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )
        response.raise_for_status()

        payload = response.json()
        if not payload.get("ok", False):
            description = payload.get("description", "unknown Telegram API error")
            LOGGER.error("Telegram API returned failure: %s", description)
            raise RuntimeError(description)