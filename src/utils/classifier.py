import os
import json
import time
import hashlib
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


LOGGER = logging.getLogger(__name__)

# Confirm in AI Studio (https://aistudio.google.com/apikey) that this model name
# is still valid for your account/region; swap via GEMINI_MODEL env var if not.
# MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Free tier is rate-limited per-minute; space out calls to stay under it.
FREE_TIER_RPM = 10
MIN_SECONDS_BETWEEN_CALLS = 60 / FREE_TIER_RPM


class Category(str, Enum):
    ELECTRONICS = "electronics"
    GAMING = "gaming"
    HOME_KITCHEN = "home_kitchen"
    FASHION = "fashion"
    GROCERY = "grocery"
    TRAVEL = "travel"
    FINANCE = "finance"
    HEALTH_BEAUTY = "health_beauty"
    ENTERTAINMENT = "entertainment"
    AUTOMOTIVE = "automotive"
    OTHER = "other"


class DiscountWorth(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class DealClassification(BaseModel):
    category: Category
    discount_worth: DiscountWorth
    summary: str = Field(max_length=200)


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing")
    return genai.Client(api_key=api_key)


def classify_deal(title, content, client=None):
    client = client or get_client()

    prompt = (
        "Classify this OzBargain deal.\n\n"
        f"Title: {title}\n"
        f"Content: {content}"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DealClassification,
        ),
    )

    LOGGER.info("Classified deal '%s' as %s", title, response.parsed)
    return response.parsed


def get_cache_file():
    # Local runs default to project dir; containers set CLASSIFIER_CACHE_FILE=/data/....
    return Path(os.getenv("CLASSIFIER_CACHE_FILE", "./classifier_cache.json"))


def load_cache():
    cache_file = get_cache_file()
    if not cache_file.exists():
        return {}

    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Could not read classifier cache at %s; starting fresh", cache_file)
        return {}


def save_cache(cache):
    cache_file = get_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def cache_key(title, content):
    # Content-based key so identical deal text is never re-classified, regardless of node_id.
    digest = hashlib.sha256(f"{title}\n{content}".encode("utf-8"))
    return digest.hexdigest()


def get_eval_log_file():
    # Local runs default to project dir; containers set CLASSIFIER_EVAL_LOG_FILE=/data/....
    return Path(os.getenv("CLASSIFIER_EVAL_LOG_FILE", "./classifier_eval_log.jsonl"))


def log_eval_entry(node_id, title, content, classification):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node_id": node_id,
        "title": title,
        "content": content,
        **classification,
    }

    eval_log_file = get_eval_log_file()
    eval_log_file.parent.mkdir(parents=True, exist_ok=True)
    with eval_log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def classify_deals(deals, client=None):
    client = client or get_client()
    cache = load_cache()
    cache_updated = False
    last_call_time = None

    for deal in deals:
        key = cache_key(deal.get("title", ""), deal.get("content", ""))

        if key in cache:
            deal["classification"] = cache[key]
            continue

        if last_call_time is not None:
            elapsed = time.monotonic() - last_call_time
            if elapsed < MIN_SECONDS_BETWEEN_CALLS:
                time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)

        try:
            result = classify_deal(deal.get("title", ""), deal.get("content", ""), client=client)
        except Exception:
            LOGGER.exception("Failed to classify deal: %s", deal.get("title", "<untitled>"))
            deal["classification"] = None
            continue
        finally:
            last_call_time = time.monotonic()

        classification = result.model_dump()
        deal["classification"] = classification
        cache[key] = classification
        cache_updated = True

        # Eval log is for weekly manual sampling; only log fresh calls, not cache hits.
        log_eval_entry(deal.get("node_id"), deal.get("title", ""), deal.get("content", ""), classification)

    if cache_updated:
        save_cache(cache)

    return deals


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    logging.basicConfig(level=logging.INFO)

    result = classify_deal(
        title="Nintendo Switch 2 $329.95 (Was $659.90) @ Big W In-Store Only",
        content="Half price on the Nintendo Switch 2 console at Big W, in-store only, while stocks last.",
    )
    print(json.dumps(result.model_dump(), indent=2))
