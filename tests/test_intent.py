"""Run with: python tests/test_intent.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.context import build_system_prompt, trim_llm_context
from ai.intent import classify_intent, parse_conversion_request

FIAT = {"USD": 1.0, "INR": 94.544084, "EUR": 0.92, "PKR": 278.5}
_TA = {
    "sma_12": None,
    "sma_26": None,
    "ema_12": None,
    "ema_26": None,
    "rsi_14": None,
    "rsi_state": "neutral",
    "trend": "sideways",
    "volatility_pct": None,
    "volatility": "unknown",
}
COINS = [
    {
        "id": "",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price_usd": 112450.0,
        "is_usd_stablecoin": False,
        "change_1h_pct": 0.1,
        "change_24h_pct": 2.5,
        "change_7d_pct": 4.0,
        "change_30d_pct": 8.0,
        "volume_24h_usd": 1_000_000,
        "market_cap_usd": 2_000_000_000_000,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
    {
        "id": "",
        "name": "Ethereum",
        "symbol": "ETH",
        "price_usd": 2493.08,
        "is_usd_stablecoin": False,
        "change_1h_pct": -0.2,
        "change_24h_pct": -1.1,
        "change_7d_pct": 3.0,
        "change_30d_pct": 5.0,
        "volume_24h_usd": 500_000,
        "market_cap_usd": 300_000_000_000,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
    {
        "id": "",
        "name": "Tether",
        "symbol": "USDT",
        "price_usd": 1.0,
        "is_usd_stablecoin": True,
        "change_1h_pct": 0.0,
        "change_24h_pct": 0.0,
        "change_7d_pct": 0.0,
        "change_30d_pct": 0.0,
        "volume_24h_usd": 0,
        "market_cap_usd": 0,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
]
GLOBAL = {
    "btc_dominance_pct": 54.2,
    "eth_dominance_pct": 12.1,
    "total_market_cap_usd": 2.4e12,
    "total_volume_usd": 8e10,
    "market_cap_change_24h_pct": 1.2,
}


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_fx_usdt_pkr() -> None:
    text = "100 USDT to PKR"
    _assert(classify_intent(text, COINS, FIAT) == "fx_convert", classify_intent(text, COINS, FIAT))
    ctx = trim_llm_context(text, FIAT, COINS)
    _assert(ctx["intent"] == "fx_convert", str(ctx))
    _assert("markets" not in ctx, "fx payload must not dump markets")
    _assert("verified_ta" not in ctx, "fx payload must not include TA")
    verified = ctx.get("verified_conversion") or {}
    _assert(verified.get("status") == "ok", str(verified))
    _assert(verified.get("result") == 100 * 278.5, str(verified.get("result")))
    _assert("PKR" in (ctx.get("fx_usd") or {}), str(ctx.get("fx_usd")))


def test_ambiguous_btc_inr() -> None:
    text = "BTC INR?"
    _assert(classify_intent(text, COINS, FIAT) == "fx_convert", classify_intent(text, COINS, FIAT))
    parsed = parse_conversion_request(text, FIAT, COINS)
    _assert(parsed is not None and parsed["base"] == "BTC" and parsed["target"] == "INR", str(parsed))
    ctx = trim_llm_context(text, FIAT, COINS)
    _assert(ctx.get("verified_conversion"), str(ctx))
    _assert(ctx.get("spot", {}).get("price_usd") == 112450.0, str(ctx.get("spot")))


def test_btc_rsi() -> None:
    text = "BTC RSI?"
    _assert(classify_intent(text, COINS, FIAT) == "asset_analysis", classify_intent(text, COINS, FIAT))
    ctx = trim_llm_context(text, FIAT, COINS)
    _assert(ctx["intent"] == "asset_analysis", str(ctx))
    _assert("top_movers" not in ctx, str(ctx))
    ta = ctx.get("verified_ta") or {}
    _assert("bar_interval" in ta, str(ta))
    _assert(ta.get("symbol") == "BTC", str(ta))
    _assert("related_news" in ctx, str(ctx))
    _assert(ctx.get("related_news_status") in {"ok", "unavailable"}, str(ctx.get("related_news_status")))


def test_market_overview() -> None:
    text = "How is the crypto market today?"
    _assert(classify_intent(text, COINS, FIAT) == "market_overview", classify_intent(text, COINS, FIAT))
    ctx = trim_llm_context(text, FIAT, COINS, global_market=GLOBAL)
    _assert(ctx["intent"] == "market_overview", str(ctx))
    _assert("verified_ta" not in ctx, str(ctx))
    _assert(ctx.get("market_overview", {}).get("btc_dominance_pct") == 54.2, str(ctx))
    _assert(ctx.get("top_movers"), str(ctx))
    for row in ctx["top_movers"]:
        _assert("rsi14" not in row and "rsi" not in row, str(row))


def test_general_open() -> None:
    text = "Explain how AES encryption works"
    _assert(classify_intent(text) == "general", classify_intent(text))
    ctx = trim_llm_context(text, FIAT, COINS, global_market=GLOBAL)
    _assert(ctx == {"intent": "general"}, str(ctx))
    prompt = build_system_prompt(ctx)
    _assert("LIVE JSON" not in prompt, "general must not inject a market dump")
    _assert("unrestricted" in prompt.lower(), "system prompt present")
    _assert("OPEN, HONEST, ACCURATE" in prompt, "open-knowledge identity")
    _assert("NEVER invent" in prompt, "anti-hallucination")


def test_news_layer() -> None:
    text = "What's the news on ETH?"
    _assert(classify_intent(text, COINS, FIAT) == "news", classify_intent(text, COINS, FIAT))
    ctx = trim_llm_context(text, FIAT, COINS)
    _assert(ctx.get("intent") == "news", str(ctx))
    _assert("verified_ta" not in ctx, str(ctx))
    _assert(ctx.get("news") in {"ok", "unavailable"}, str(ctx.get("news")))
    _assert("News (verified, fetched)" in (ctx.get("news_digest") or ""), str(ctx.get("news_digest")))
    prompt = build_system_prompt(ctx)
    _assert("invent" in prompt.lower() or "unavailable" in prompt.lower() or "NEWS" in prompt, prompt[:500])


def test_threat_intel_intent() -> None:
    text = "Any dark web activity?"
    _assert(classify_intent(text) == "threat_intel", classify_intent(text))
    ctx = trim_llm_context(text, FIAT, COINS)
    _assert(ctx.get("intent") == "threat_intel", str(ctx))
    _assert(ctx.get("onion") in {"ok", "unavailable", "tor_down", "not_enabled"}, str(ctx.get("onion")))
    _assert(ctx.get("onion_digest"), str(ctx))


def test_parse_failure_is_general() -> None:
    _assert(classify_intent("") == "general", classify_intent(""))
    _assert(classify_intent("hello there") == "general", classify_intent("hello there"))


if __name__ == "__main__":
    test_fx_usdt_pkr()
    test_ambiguous_btc_inr()
    test_btc_rsi()
    test_market_overview()
    test_general_open()
    test_news_layer()
    test_threat_intel_intent()
    test_parse_failure_is_general()
    print("intent tests passed")
