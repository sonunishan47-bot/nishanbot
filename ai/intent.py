"""Intent classification and conversion parsing. Does not import ai.context."""

from __future__ import annotations

import re
from typing import Any, Optional

from config import STABLECOINS_USD_PEG

INTENT_FX_CONVERT = "fx_convert"
INTENT_ASSET_ANALYSIS = "asset_analysis"
INTENT_MARKET_OVERVIEW = "market_overview"
INTENT_NEWS = "news"
INTENT_MACRO = "macro"
INTENT_THREAT_INTEL = "threat_intel"
INTENT_GENERAL = "general"

CRYPTO_ALIASES = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "ether": "ETH",
    "tether": "USDT",
    "solana": "SOL",
    "ripple": "XRP",
    "cardano": "ADA",
    "dogecoin": "DOGE",
    "doge": "DOGE",
    "litecoin": "LTC",
    "polkadot": "DOT",
    "avalanche": "AVAX",
    "chainlink": "LINK",
    "tron": "TRX",
    "toncoin": "TON",
    "shiba": "SHIB",
    "binance": "BNB",
    "polygon": "MATIC",
    "stellar": "XLM",
}

KNOWN_CRYPTO_SYMBOLS = set(CRYPTO_ALIASES.values()) | set(STABLECOINS_USD_PEG)

FIAT_ALIASES = {
    "dollar": "USD",
    "dollars": "USD",
    "buck": "USD",
    "bucks": "USD",
    "rupee": "INR",
    "rupees": "INR",
    "dirham": "AED",
    "dirhams": "AED",
    "euro": "EUR",
    "euros": "EUR",
    "pound": "GBP",
    "pounds": "GBP",
    "sterling": "GBP",
    "riyal": "SAR",
    "riyals": "SAR",
    "dinar": "KWD",
    "dinars": "KWD",
    "yen": "JPY",
    "yuan": "CNY",
    "rmb": "CNY",
}

# Words that look like ISO codes but are English (TRY the verb vs TRY the lira).
ENGLISH_3LETTER = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HAS", "WAS",
    "HOW", "WHY", "WHO", "ANY", "OUT", "TOP", "LOW", "BUY", "NOW", "NEW", "OLD",
    "ASK", "BID", "CAP", "PER", "OFF", "OWN", "OUR", "ITS", "LET", "GET", "PUT",
    "SEE", "USE", "WAY", "MAY", "DAY", "BIG", "ONE", "TWO", "SIX", "TEN", "YES",
    "TRY", "HIS", "HER", "SHE", "HIM", "DID", "HAD", "AGO", "GOT", "SET", "RUN",
    "APP", "BOT", "API",
}

ASSET_TA_HINTS = (
    "rsi", "macd", "bollinger", "ema", "sma", "support", "resistance",
    "volatility", "momentum", "trend", "chart", "indicator", "overbought",
    "oversold", "bullish", "bearish", "analysis", "analyze", "analyse",
    "outlook", "ta ",
)

BROAD_MARKET_HINTS = (
    "market", "overview", "top coins", "leaderboard", "what to buy",
    "watchlist", "heatmap", "altcoin", "alts", "compare coins", "best coins",
    "trend of the market", "overall", "dominance", "top movers",
)

NEWS_PHRASES = (
    "what's going on",
    "whats going on",
    "what is going on",
    "what happened",
)
NEWS_WORDS = ("news", "happening")
MACRO_PHRASES = (
    "interest rate",
    "central bank",
    "federal reserve",
)
MACRO_WORDS = ("fed", "cpi", "inflation", "fomc", "ecb")
THREAT_PHRASES = (
    "dark web",
    "darkweb",
    "hidden service",
    "threat group",
    "threat groups",
    "ransomware",
    "leak site",
    "leak-site",
    "breach",
    "threat intel",
    "osint",
)
THREAT_WORDS = ("onion", "tor")

_CONVERT_RE = re.compile(
    r"(?:(?P<amount>\d+(?:\.\d+)?)\s*)?(?P<base>[A-Za-z]{2,10})\s+(?:to|into|in)\s+(?P<target>[A-Za-z]{2,10})\b",
    re.I,
)
_PAIR_RE = re.compile(
    r"\b(?P<base>[A-Za-z]{2,10})\s*[/\-]\s*(?P<target>[A-Za-z]{2,10})\b",
    re.I,
)
_JUXTAPOSE_RE = re.compile(
    r"\b(?P<base>[A-Za-z]{2,10})\s+(?P<target>[A-Za-z]{2,10})\s*\??\s*$",
    re.I,
)
_HOW_IS_RE = re.compile(
    r"\bhow(?:'s| is)\s+(?:the\s+)?(?P<asset>[A-Za-z]{2,20})\b",
    re.I,
)


def wants_broad_market(prompt: str) -> bool:
    text = (prompt or "").lower()
    return any(hint in text for hint in BROAD_MARKET_HINTS)


def has_asset_ta_hint(prompt: str) -> bool:
    text = f" {(prompt or '').lower()} "
    return any(hint in text for hint in ASSET_TA_HINTS)


def extract_coin_symbols(prompt: str, coins: Optional[list[dict[str, Any]]] = None) -> list[str]:
    coins = coins or []
    found: set[str] = set()
    lower = (prompt or "").lower()
    for alias, symbol in CRYPTO_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            found.add(symbol)
    by_symbol = {str(c.get("symbol") or "").upper(): c for c in coins if c.get("symbol")}
    by_name = {str(c.get("name") or "").lower(): str(c.get("symbol") or "").upper() for c in coins}
    for token in re.findall(r"\b[A-Za-z]{2,10}\b", prompt or ""):
        symbol = token.upper()
        if symbol in ENGLISH_3LETTER:
            continue
        if symbol in by_symbol or symbol in KNOWN_CRYPTO_SYMBOLS:
            found.add(symbol)
        name_hit = by_name.get(token.lower())
        if name_hit:
            found.add(name_hit)
    for stable in STABLECOINS_USD_PEG:
        if re.search(rf"\b{stable}\b", prompt or "", flags=re.I):
            found.add(stable)
    return sorted(found)


def extract_fiat_codes(prompt: str, available: Optional[dict[str, float]] = None) -> list[str]:
    available = available or {}
    found: set[str] = set()
    lower = (prompt or "").lower()
    for alias, code in FIAT_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            found.add(code)
    for token in re.findall(r"\b[A-Za-z]{3}\b", prompt or ""):
        code = token.upper()
        if code in ENGLISH_3LETTER:
            continue
        if code == "USD" or code in available:
            found.add(code)
    return sorted(found)


def _resolve_asset_code(
    token: str,
    fiat_rates: dict[str, float],
    coins: list[dict[str, Any]],
) -> tuple[str, str]:
    raw = (token or "").strip()
    lower = raw.lower()
    upper = raw.upper()
    if lower in FIAT_ALIASES:
        return FIAT_ALIASES[lower], "fiat"
    if lower in CRYPTO_ALIASES:
        kind = "stable" if CRYPTO_ALIASES[lower] in STABLECOINS_USD_PEG else "crypto"
        return CRYPTO_ALIASES[lower], kind
    if upper in STABLECOINS_USD_PEG:
        return upper, "stable"
    if upper == "USD" or upper in fiat_rates:
        return upper, "fiat"
    for coin in coins:
        if str(coin.get("symbol") or "").upper() == upper:
            if coin.get("is_usd_stablecoin") or upper in STABLECOINS_USD_PEG:
                return upper, "stable"
            return upper, "crypto"
        if str(coin.get("name") or "").lower() == lower:
            symbol = str(coin.get("symbol") or "").upper()
            kind = "stable" if coin.get("is_usd_stablecoin") or symbol in STABLECOINS_USD_PEG else "crypto"
            return symbol, kind
    if upper in KNOWN_CRYPTO_SYMBOLS:
        kind = "stable" if upper in STABLECOINS_USD_PEG else "crypto"
        return upper, kind
    return upper, "unknown"


def _pair_from_match(
    match: re.Match[str],
    fiat_rates: dict[str, float],
    coins: list[dict[str, Any]],
    amount: float,
) -> Optional[dict[str, Any]]:
    base_code, base_kind = _resolve_asset_code(match.group("base"), fiat_rates, coins)
    target_code, target_kind = _resolve_asset_code(match.group("target"), fiat_rates, coins)
    if target_kind == "fiat" and base_kind in {"crypto", "stable", "fiat", "unknown"}:
        return {
            "amount": amount,
            "base": base_code,
            "target": target_code,
            "base_kind": base_kind,
        }
    if base_kind == "fiat" and target_kind in {"crypto", "stable"}:
        return {
            "amount": amount,
            "base": target_code,
            "target": base_code,
            "base_kind": target_kind,
        }
    return None


def parse_conversion_request(
    prompt: str,
    fiat_rates: Optional[dict[str, float]] = None,
    coins: Optional[list[dict[str, Any]]] = None,
) -> Optional[dict[str, Any]]:
    fiat_rates = fiat_rates or {}
    coins = coins or []
    text = prompt or ""
    match = _CONVERT_RE.search(text)
    if match:
        amount_raw = match.group("amount")
        amount = float(amount_raw) if amount_raw else 1.0
        parsed = _pair_from_match(match, fiat_rates, coins, amount)
        if parsed:
            return parsed
    for match in _PAIR_RE.finditer(text):
        parsed = _pair_from_match(match, fiat_rates, coins, 1.0)
        if parsed and parsed["base_kind"] in {"crypto", "stable", "fiat"}:
            return parsed
    juxta = _JUXTAPOSE_RE.search(text.strip())
    if juxta:
        parsed = _pair_from_match(juxta, fiat_rates, coins, 1.0)
        if parsed and parsed["base_kind"] in {"crypto", "stable"}:
            return parsed
    return None


def _has_news_intent(prompt: str) -> bool:
    text = (prompt or "").lower()
    if any(phrase in text for phrase in NEWS_PHRASES):
        return True
    if re.search(r"\bnews\b", text):
        return True
    if re.search(r"\bhappening\b", text):
        return True
    if re.search(r"\blatest\b", text) and not has_asset_ta_hint(prompt):
        return True
    return False


def _has_threat_intel_intent(prompt: str) -> bool:
    text = (prompt or "").lower()
    if any(phrase in text for phrase in THREAT_PHRASES):
        return True
    if re.search(r"\b(onion|tor)\b", text) and any(
        token in text for token in ("dark", "activity", "intel", "threat", "hidden")
    ):
        return True
    if "dark web activity" in text or "any dark web" in text:
        return True
    return False


def _has_macro_intent(prompt: str) -> bool:
    text = (prompt or "").lower()
    if any(phrase in text for phrase in MACRO_PHRASES):
        return True
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in MACRO_WORDS)


def _how_is_named_asset(prompt: str, coins: list[dict[str, Any]]) -> bool:
    match = _HOW_IS_RE.search(prompt or "")
    if not match:
        return False
    token = match.group("asset")
    if token.lower() in {"market", "crypto", "overall", "economy", "fed"}:
        return False
    _code, kind = _resolve_asset_code(token, {}, coins)
    return kind in {"crypto", "stable"}


def is_asset_analysis_intent(
    prompt: str,
    coins: Optional[list[dict[str, Any]]] = None,
    parsed_conversion: Optional[dict[str, Any]] = None,
) -> bool:
    if parsed_conversion:
        return False
    coins = coins or []
    symbols = extract_coin_symbols(prompt, coins)
    if not symbols and not _how_is_named_asset(prompt, coins):
        return False
    if wants_broad_market(prompt) and not has_asset_ta_hint(prompt) and not _how_is_named_asset(prompt, coins):
        return False
    if has_asset_ta_hint(prompt) or _how_is_named_asset(prompt, coins):
        return True
    return False


def classify_intent(
    text: str,
    coins: Optional[list[dict[str, Any]]] = None,
    fiat_rates: Optional[dict[str, float]] = None,
) -> str:
    """Rule-based: fx_convert | asset_analysis | market_overview | news | macro | general."""
    try:
        coins = coins or []
        fiat_rates = fiat_rates or {}
        parsed = parse_conversion_request(text, fiat_rates, coins)
        if parsed:
            return INTENT_FX_CONVERT
        if _has_threat_intel_intent(text):
            return INTENT_THREAT_INTEL
        if _has_news_intent(text):
            return INTENT_NEWS
        if _has_macro_intent(text):
            return INTENT_MACRO
        if is_asset_analysis_intent(text, coins, parsed):
            return INTENT_ASSET_ANALYSIS
        if wants_broad_market(text):
            return INTENT_MARKET_OVERVIEW
        return INTENT_GENERAL
    except Exception:
        return INTENT_GENERAL


__all__ = [
    "ASSET_TA_HINTS",
    "BROAD_MARKET_HINTS",
    "CRYPTO_ALIASES",
    "ENGLISH_3LETTER",
    "FIAT_ALIASES",
    "INTENT_ASSET_ANALYSIS",
    "INTENT_FX_CONVERT",
    "INTENT_GENERAL",
    "INTENT_MACRO",
    "INTENT_MARKET_OVERVIEW",
    "INTENT_NEWS",
    "INTENT_THREAT_INTEL",
    "classify_intent",
    "extract_coin_symbols",
    "extract_fiat_codes",
    "is_asset_analysis_intent",
    "parse_conversion_request",
    "wants_broad_market",
]
