import os

import pytest

from src.utils.classifier import Category, DiscountWorth, classify_deal


# Live regression test against the Gemini API: checks output structure, not
# classification accuracy (accuracy is reviewed manually via the eval log).
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set; skipping live classifier regression test",
)

FIXED_SAMPLES = [
    {
        "title": "Nintendo Switch 2 $329.95 (Was $659.90) @ Big W In-Store Only",
        "content": "Half price on the Nintendo Switch 2 console at Big W, in-store only, while stocks last.",
    },
    {
        "title": "Ryobi 18V ONE+ T50 Stapler - Tool Only $129 Delivered (Was $179) / C&C / in-Store @ Bunnings",
        "content": "Ryobi cordless stapler, tool only, no battery included.",
    },
    {
        "title": "Woolworths 20% off Fresh Fruit and Vegetables for Rewards Members",
        "content": "Everyday Rewards members get 20% off fresh produce this week only.",
    },
]


@pytest.mark.parametrize("sample", FIXED_SAMPLES, ids=[s["title"] for s in FIXED_SAMPLES])
def test_classify_deal_structure(sample):
    result = classify_deal(sample["title"], sample["content"])

    assert isinstance(result.category, Category)
    assert isinstance(result.discount_worth, DiscountWorth)
    assert isinstance(result.summary, str)
    assert len(result.summary) <= 200
