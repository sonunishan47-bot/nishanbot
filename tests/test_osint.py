"""Offline tests for OSINT evidence formatting. Run: python tests/test_osint.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.intent import classify_intent
from data.news import headline_sentiment
from data.rss_util import evidence_item, format_digest


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_digest_format() -> None:
    items = [
        evidence_item(
            headline="Bitcoin ETF flows",
            source="CoinDesk",
            url="https://example.com/a",
            published_at="2026-09-08T14:32:00+00:00",
        )
    ]
    digest = format_digest("NEWS", items, 6)
    _assert(digest.startswith("NEWS (last 6h):"), digest)
    _assert("[CoinDesk 14:32]" in digest, digest)
    _assert("https://example.com/a" in digest, digest)


def test_sentiment() -> None:
    _assert(headline_sentiment("Bitcoin ETF inflows hit a record") == "positive", "pos")
    _assert(headline_sentiment("Exchange hacked, funds stolen") == "negative", "neg")
    _assert(headline_sentiment("Market update for Wednesday") == "neutral", "neu")


def test_intents() -> None:
    _assert(classify_intent("What's the news on crypto?") == "news", classify_intent("What's the news on crypto?"))
    happening = classify_intent("what's happening in crypto?")
    _assert(happening == "news", happening)
    _assert(classify_intent("Any dark web activity?") == "threat_intel", classify_intent("Any dark web activity?"))
    _assert(classify_intent("What did the Fed say about inflation?") == "macro", classify_intent("What did the Fed say about inflation?"))


if __name__ == "__main__":
    test_digest_format()
    test_sentiment()
    test_intents()
    print("osint tests passed")
