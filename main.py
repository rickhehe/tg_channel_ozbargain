import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

from src.utils.get_deals import get_deals_block, save_anchor
from src.utils.telegram import send_telegram_message


LOGGER = logging.getLogger(__name__)


def configure_logging():
    
    # utc
    logging.Formatter.converter = time.gmtime

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def format_deal_message(deal):
    title = deal.get("title", "")
    url = deal.get("url", "")
    content = deal.get("content", "")
    snippet = content[:240]

    if len(content) > 240:
        snippet = f"{snippet}..."

    return f"{title}\n{url}\n\n{snippet}"


def main():
    configure_logging()

    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        LOGGER.error("Missing TELEGRAM_CHAT_ID environment variable")
        raise ValueError("TELEGRAM_CHAT_ID is missing")

    deals = get_deals_block()
    LOGGER.info("Found %d new deal(s) to send", len(deals))

    if not deals:
        LOGGER.info("No new deals found, exiting")
        return

    # Sort deals by node_id to ensure they are sent in order
    deals.sort(key=lambda x: x['node_id'])
    for deal in deals:
        try:
            node_id = deal.get("node_id")
            message = format_deal_message(deal)
            LOGGER.info("Sending deal: %s", deal.get("title", "<untitled>"))
            send_telegram_message(chat_id, message)
            LOGGER.info("Sent deal successfully: %s", deal.get("title", "<untitled>"))
            save_anchor(node_id)
        except Exception:
            LOGGER.exception("Failed to send deal: %s", deal.get("title", "<untitled>"))
            raise SystemExit(1)  # Exit with error code to indicate failure


if __name__ == "__main__":
    main()