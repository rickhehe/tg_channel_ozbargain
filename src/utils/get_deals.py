import os
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import httpx


URL = "https://www.ozbargain.com.au/deals/"
LOGGER = logging.getLogger(__name__)


def get_anchor_file():
    # Local runs default to project anchor.txt; containers set ANCHOR_FILE=/data/anchor.txt.
    return Path(os.getenv("ANCHOR_FILE", "./anchor.txt"))


def load_anchor():
    anchor_file = get_anchor_file()
    if not anchor_file.exists():
        LOGGER.info("Anchor file does not exist yet, starting from 0: %s", anchor_file)
        return 0

    value = anchor_file.read_text(encoding="utf-8").strip()
    if not value:
        return 0

    try:
        return int(value)
    except ValueError:
        LOGGER.warning("Invalid anchor value '%s' in %s; resetting to 0", value, anchor_file)
        return 0


def save_anchor(anchor):

    # Ensure the directory exists before writing the anchor value
    # Especially for containers.
    anchor_file = get_anchor_file()
    anchor_file.parent.mkdir(parents=True, exist_ok=True)
    anchor_file.write_text(str(anchor), encoding="utf-8")
    LOGGER.info("Saved anchor %s to %s", anchor, anchor_file)


def get_html():
    LOGGER.info("Fetching OzBargain deals page: %s", URL)
    with httpx.Client(timeout=5, follow_redirects=True) as client:
        response = client.get(URL)
        response.raise_for_status()
        return response.text


def get_deals_block():
    html_content = get_html()
    soup = BeautifulSoup(html_content, "html.parser")

    blocks = soup.select('div.node.node-ozbdeal.node-teaser')
    LOGGER.info("Parsed %d deal block(s) from page", len(blocks))
    deals = []

    # Load the last processed anchor value to avoid duplicates
    anchor = load_anchor()
    LOGGER.info("Current anchor value: %s", anchor)
    for block in blocks:
        node_id = block.get("id", "").replace("node", "")
        node_id = int(node_id) if node_id.isdigit() else None

        if not node_id:  # incase the node_id is not valid, skip this block
            continue

        if node_id > anchor:

            title_tag = block.select_one("h2.title a")
            content_tag = block.select_one("div.content")

            title = title_tag.get_text(strip=True) if title_tag else ""
            href = title_tag.get("href") if title_tag else ""

            url = urljoin(URL, href) if href else ""
            content = content_tag.get_text(" ", strip=True) if content_tag else ""

            deals.append({
                "node_id": node_id,
                "url": url,
                "title": title,
                "content": content,
            })

    return deals
