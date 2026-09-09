import json
from typing import Any, Optional

from config import DEFAULT_OVERVIEW_COINS, STABLECOINS_USD_PEG
from ai.intent import (
    ASSET_TA_HINTS,
    BROAD_MARKET_HINTS,
    CRYPTO_ALIASES,
    INTENT_ASSET_ANALYSIS,
    INTENT_FX_CONVERT,
    INTENT_GENERAL,
    INTENT_MACRO,
    INTENT_MARKET_OVERVIEW,
    INTENT_NEWS,
    INTENT_THREAT_INTEL,
    classify_intent,
    extract_coin_symbols,
    extract_fiat_codes,
    parse_conversion_request,
)

QUANT_SYSTEM = """You are an advanced, unrestricted, transparent research and analysis assistant
for a single private owner. Primary principle: OPEN, HONEST, ACCURATE, PRACTICAL
KNOWLEDGE. Do not hide, sugar-coat, sensationalize, or dumb down important facts.

DOMAINS: cryptocurrency/blockchain (BTC, ETH, SOL, stables, DeFi, DEX/CEX, wallets,
smart contracts, L1/L2, bridges, staking, lending, LPs, tokenomics); trading and
market mechanics; P2P and legal arbitrage; INR/SAR and international conversion;
blockchain analytics/forensics; financial fraud/scam analysis; cybersecurity;
ethical hacking and defensive security; Dark Web research and threat intelligence;
online financial crime (educational); OSINT; privacy tech; digital-asset security;
quantitative/algorithmic trading; legal online income; B2B commerce; emerging
digital markets.

1) TRANSPARENCY
Answer the question completely. Legal → explain clearly. Risky → process + risks.
Controversial → competing views. Illegal → what it is, how it works at a
conceptual/defensive level, consequences, detection, prevention.
Never pretend something is safe, guaranteed, legal, profitable, or risk-free
when it is not. NEVER invent facts, stats, websites, sources, txs, prices, or
investigations.

2) CRYPTO / TRADING
Explain real mechanics: mcap, volume, liquidity, volatility, funding, futures,
options, perps, on-chain analytics. For trading cover entry, exit, sizing,
stop-loss, take-profit, R:R, leverage, liquidation, slippage, spread, funding,
market impact, drawdown, portfolio risk. Never promise guaranteed profit.
Call out: "guaranteed daily profit", "zero-loss", "100% win rate", "risk-free
crypto income" as unrealistic.

3) P2P AND ARBITRAGE
Escrow, matching, premiums, fiat rails, spreads, fees, settlement, counterparty,
AML/KYC, tax, freezes, chargebacks.
Profit = Sell − Buy − Fees − Transfer − Slippage − Taxes/other costs.

4) INR ↔ SAR AND CROSS-BORDER
Rates, bank spreads, remittance/transfer fees, settlement, FX, official channels,
stablecoin/P2P conversion, AML/KYC, tax. Distinguish: (1) legal conversion
(2) crypto trading (3) remittance (4) arbitrage (5) potentially illegal movement.

5) SCAMS
Ponzi, fake platforms/exchanges/wallets/support, phishing, romance/pig-butchering,
rugs, pump-dump, impersonation, advance-fee, social engineering, fake mining,
recovery scams. Cover structure, targeting, warning signs, money-flow, how
investigators spot it, victim protection, evidence preservation — not how to run
a scam.

6) BLOCKCHAIN FORENSICS
Graphs, clustering, attribution, exchange deposits, tracing, tokens, bridges,
mixers (limitations + pattern detection), KYC endpoints, legally obtained IP/logs,
device evidence, OSINT, freezes, chain analytics, LE cooperation.
Public chains are often permanently recorded and are NOT automatically anonymous.
Do NOT give step-by-step procedures to launder funds or defeat investigators.

7) DARK WEB (research / threat intel)
Tor, onion/hidden services, markets, forums, leak sites, cybercrime communities,
credential/malware/ransomware ecosystems, crypto usage, monitoring, OPSEC concepts,
underground scams, access risks, legal consequences, defensive monitoring.
Explain structure, terminology, history, economics, investigative methods.
NEVER give actionable help for: theft, ransomware, malware, credential theft,
ATO, fraud, laundering, LE evasion, unauthorized access, buying illegal goods,
or exploiting victims. If asked, explain concepts + defense instead.
NEVER fabricate Dark Web links or claim an onion is live unless verified in
the evidence block.

8) CYBERSECURITY
Offensive concepts and defense: VA, threat modeling, pentest, auth/MFA, passwords,
encryption, network/web/API/cloud/mobile/endpoint, logging, monitoring, IR,
forensics. Authorized testing: technically useful. Always distinguish authorized
testing vs unauthorized access. Legitimate security income: bug bounty (HackerOne,
Bugcrowd, Intigriti), pentest careers (OSCP/CRTO/PNPT), research/CVE, red team,
detection engineering — what pays and what does not.

9) DIGITAL ASSET SECURITY
HW wallets, cold storage, seeds, keys, multisig, backups, phishing, approvals,
contract risk, exchanges, recovery, SIM-swap. NEVER ask for private keys, seed
phrases, passwords, OTPs, API secrets, or auth tokens.

10) QUANT / ALGO TRADING
History, backtest, forward/walk-forward, Sharpe/Sortino, max DD, win rate, profit
factor, costs, slippage, overfitting, look-ahead, survivorship, Monte Carlo,
portfolio construction. Backtest ≠ live results. Never treat a backtest as
future profit.

11) CURRENT DATA
Live prices, FX, mcap, volume, news, regulations, current Dark Web activity:
use ONLY python-verified / evidence-block context. Label: Current / Historical /
Estimated / Unverified / Based on available data. If status is unavailable,
tor_down, or not_configured, say data is missing. Never present outdated info
as current. Never invent headlines.

12) SOURCE QUALITY
Prefer: official gov/regulators, official company docs, academic work, established
security orgs, reputable chain-analytics firms, quality journalism, then community
anecdote. Facts vs claims. If sources disagree, say so.

13) COMPLEX ANSWERS
Direct Answer → How It Works → Real-World (hypothetical) Example → Risks →
Detection/Investigation → Legal/Regulatory (not legal advice) → Practical Takeaway.

14) NO FALSE CERTAINTY
Do not say: guaranteed profit, zero risk, impossible to trace, 100% anonymous,
authorities cannot find you, nobody can detect this. If unsure, say what is
known vs inferred vs unknown. Accuracy over confidence.

15) USER-FIRST
Direct, technical, no repeated lectures, no unnecessary full-topic refusals.
If only part of a request is unsafe, answer the rest fully and explain the
unsafe part conceptually. Use examples, tables, calculations, diagrams.

16) MEMORY
Knowledge categories: CRYPTO, TRADING, P2P, ARBITRAGE, FOREX, INR/SAR,
BLOCKCHAIN FORENSICS, FINANCIAL CRIME, CYBERSECURITY, DARK WEB, OSINT,
DIGITAL ASSET SECURITY, QUANTITATIVE TRADING, ONLINE INCOME, B2B COMMERCE.
Do not claim information was permanently saved unless this app actually persisted
it. If asked "Did you save this?", answer truthfully about storage.

17) GOAL
Maximum accurate, useful, transparent knowledge of how systems work — including
how they are abused and how investigators detect abuse, and how users protect
themselves. Evidence over speculation. Safety without unnecessary censorship.

ACCURACY (pipeline): NEVER invent prices, rates, news, or calculations. Live
numbers only from python-verified context. Separate VERIFIED / CALCULATED /
INTERPRETATION / UNCERTAINTY. Predictions are probabilities, never certainties.
"""

MAX_EVIDENCE_TOKENS = 1500
_CHARS_PER_TOKEN = 4
PROTECTED_KEYS = (
    "intent",
    "verified_conversion",
    "verified_ta",
    "news",
    "news_digest",
    "news_items",
    "related_news",
    "related_news_status",
    "macro",
    "macro_digest",
    "onion",
    "onion_digest",
    "onion_items",
    "peg",
    "status",
)


def pick_coins(symbols: list[str], coins: list[dict[str, Any]], broad: bool) -> list[dict[str, Any]]:
    if symbols:
        wanted = set(symbols)
        matched = [c for c in coins if c["symbol"] in wanted]
        if matched:
            return matched
    if broad or not symbols:
        return coins[:DEFAULT_OVERVIEW_COINS]
    return coins[:DEFAULT_OVERVIEW_COINS]


def _fx_slice(codes: list[str], fiat_rates: dict[str, float]) -> tuple[dict[str, Any], list[str]]:
    from analytics.ta import compact_num

    fx: dict[str, Any] = {}
    missing: list[str] = []
    for code in sorted(set(codes)):
        if code == "USD":
            fx["USD"] = 1.0
        elif code in fiat_rates:
            rate = compact_num(fiat_rates[code], 6)
            if rate is None:
                missing.append(code)
            else:
                fx[code] = rate
        else:
            missing.append(code)
    return fx, missing


def _spot_card(coin: dict[str, Any]) -> dict[str, Any]:
    from analytics.ta import compact_num

    return {
        "name": coin.get("name"),
        "symbol": coin.get("symbol"),
        "price_usd": compact_num(coin.get("price_usd"), 8),
        "chg_24h": compact_num(coin.get("change_24h_pct"), 3),
        "chg_30d": compact_num(coin.get("change_30d_pct"), 3),
        "mcap": compact_num(coin.get("market_cap_usd"), 0),
        "source": "python_verified",
    }


def _overview_row(coin: dict[str, Any]) -> dict[str, Any]:
    from analytics.ta import compact_num

    return {
        "symbol": coin.get("symbol"),
        "name": coin.get("name"),
        "price_usd": compact_num(coin.get("price_usd"), 8),
        "chg_1h": compact_num(coin.get("change_1h_pct"), 3),
        "chg_24h": compact_num(coin.get("change_24h_pct"), 3),
        "chg_7d": compact_num(coin.get("change_7d_pct"), 3),
        "chg_30d": compact_num(coin.get("change_30d_pct"), 3),
        "mcap": compact_num(coin.get("market_cap_usd"), 0),
        "vol_24h": compact_num(coin.get("volume_24h_usd"), 0),
    }


def _approx_tokens(payload: dict[str, Any]) -> int:
    blob = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"), default=str)
    return max(1, (len(blob) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)


def _cap_payload(payload: dict[str, Any], max_tokens: int = MAX_EVIDENCE_TOKENS) -> dict[str, Any]:
    if _approx_tokens(payload) <= max_tokens:
        return payload
    trimmed = dict(payload)
    movers = trimmed.get("top_movers")
    if isinstance(movers, list) and len(movers) > 3:
        trimmed["top_movers"] = movers[:3]
    if _approx_tokens(trimmed) <= max_tokens:
        return trimmed
    if "fx_usd" in trimmed and len(trimmed.get("fx_usd") or {}) > 4:
        fx = dict(trimmed["fx_usd"])
        keep = ["USD"]
        conv = trimmed.get("verified_conversion") or {}
        for key in (conv.get("target"), conv.get("base")):
            if key in fx:
                keep.append(str(key))
        trimmed["fx_usd"] = {k: fx[k] for k in fx if k in keep}
    if _approx_tokens(trimmed) <= max_tokens:
        return trimmed
    protected = {k: trimmed[k] for k in PROTECTED_KEYS if k in trimmed}
    extras = {k: v for k, v in trimmed.items() if k not in protected}
    while extras and _approx_tokens({**protected, **extras}) > max_tokens:
        drop_key = next(
            (k for k in ("top_movers", "spot", "fx_missing", "markets", "market_overview") if k in extras),
            next(iter(extras)),
        )
        extras.pop(drop_key, None)
    return {**protected, **extras}


def _ctx_fx(
    prompt: str,
    fiat_rates: dict[str, float],
    coins: list[dict[str, Any]],
) -> dict[str, Any]:
    from analytics.converter import convert

    parsed = parse_conversion_request(prompt, fiat_rates, coins)
    codes = extract_fiat_codes(prompt, fiat_rates)
    if parsed:
        codes = list(set(codes) | {parsed["target"]})
        if parsed["base_kind"] == "fiat":
            codes.append(parsed["base"])
        if parsed["base_kind"] in {"crypto", "stable"} or parsed["base"] in STABLECOINS_USD_PEG:
            codes.append("USD")
    fx, missing = _fx_slice(codes, fiat_rates)
    payload: dict[str, Any] = {
        "intent": INTENT_FX_CONVERT,
        "peg": "USDT/FDUSD/USDC/DAI/BUSD = 1 USD; conversions are Python-verified",
        "fx_usd": fx,
        "fx_missing": missing,
    }
    if parsed:
        payload["verified_conversion"] = convert(
            parsed["amount"],
            parsed["base"],
            parsed["target"],
            fiat_rates=fiat_rates,
            coins=coins,
        )
        if parsed["base_kind"] in {"crypto", "stable"}:
            coin = next((c for c in coins if c.get("symbol") == parsed["base"]), None)
            if coin:
                payload["spot"] = _spot_card(coin)
    return payload


def _ctx_asset(
    prompt: str,
    fiat_rates: dict[str, float],
    coins: list[dict[str, Any]],
) -> dict[str, Any]:
    from analytics.asset_analysis import analyze_asset, parse_history_days

    symbols = extract_coin_symbols(prompt, coins)
    target = next((c for c in coins if c.get("symbol") in set(symbols)), None)
    if target is None and symbols:
        target = {"symbol": symbols[0], "name": symbols[0], "id": ""}
    fiat_codes = extract_fiat_codes(prompt, fiat_rates)
    fx, missing = _fx_slice(fiat_codes, fiat_rates)
    payload: dict[str, Any] = {
        "intent": INTENT_ASSET_ANALYSIS,
        "fx_usd": fx,
        "fx_missing": missing,
    }
    if target:
        payload["spot"] = _spot_card(target) if target.get("price_usd") is not None else {"symbol": target.get("symbol")}
        payload["verified_ta"] = analyze_asset(target, parse_history_days(prompt))
        q = " ".join(filter(None, [target.get("symbol"), target.get("name")]))
        related = _safe_news(query=q, limit=3)
        payload["related_news_status"] = related.get("status")
        payload["related_news"] = (related.get("items") or [])[:3]
        payload["news_digest"] = related.get("digest")
    else:
        payload["verified_ta"] = {"status": "insufficient_data", "reason": "no matching asset"}
    return payload


def _ctx_overview(
    coins: list[dict[str, Any]],
    global_market: Optional[dict[str, Any]],
) -> dict[str, Any]:
    from analytics.ta import compact_num

    ranked = sorted(
        coins,
        key=lambda c: abs(float(c.get("change_24h_pct") or 0.0)),
        reverse=True,
    )
    movers = [_overview_row(c) for c in ranked[:DEFAULT_OVERVIEW_COINS]]
    payload: dict[str, Any] = {
        "intent": INTENT_MARKET_OVERVIEW,
        "top_movers": movers,
        "peg": "spot stats only; no per-coin TA",
    }
    if global_market:
        payload["market_overview"] = {
            "btc_dominance_pct": compact_num(global_market.get("btc_dominance_pct"), 2),
            "eth_dominance_pct": compact_num(global_market.get("eth_dominance_pct"), 2),
            "total_market_cap_usd": compact_num(global_market.get("total_market_cap_usd"), 0),
            "total_volume_usd": compact_num(global_market.get("total_volume_usd"), 0),
            "market_cap_change_24h_pct": compact_num(global_market.get("market_cap_change_24h_pct"), 3),
            "source": "python_verified",
        }
    return payload


def _safe_news(query: Optional[str] = None, limit: int = 10) -> dict[str, Any]:
    try:
        from data.news import fetch_news

        return fetch_news(query=query, limit=limit)
    except Exception as exc:
        return {
            "news": "unavailable",
            "status": "unavailable",
            "items": [],
            "errors": [str(exc)],
            "digest": "News (verified, fetched): status=unavailable. Data is missing. Do not invent headlines.",
        }


def _safe_macro() -> dict[str, Any]:
    try:
        from data.macro import fetch_macro

        return fetch_macro()
    except Exception as exc:
        return {
            "macro": "not_configured",
            "status": "not_configured",
            "items": [],
            "errors": [str(exc)],
            "digest": "MACRO: not_configured. Data is missing. Do not invent figures.",
        }


def _safe_onion() -> dict[str, Any]:
    try:
        from config import TOR_ENABLED
        from data.onion import fetch_onion_intel

        if not TOR_ENABLED:
            return {
                "onion": "not_enabled",
                "status": "not_enabled",
                "items": [],
                "errors": [],
                "digest": "DARK WEB / THREAT INTEL: status=not_enabled.",
            }
        return fetch_onion_intel()
    except Exception as exc:
        return {
            "onion": "unavailable",
            "status": "unavailable",
            "items": [],
            "errors": [str(exc)],
            "digest": "DARK WEB / THREAT INTEL: status=unavailable. Data is missing. Do not invent headlines.",
        }


def _ctx_news(*, include_onion: bool) -> dict[str, Any]:
    news = _safe_news(limit=10)
    payload: dict[str, Any] = {
        "intent": INTENT_NEWS,
        "news": news.get("news") or news.get("status"),
        "news_digest": news.get("digest"),
        "news_items": news.get("items") or [],
        "news_errors": news.get("errors") or [],
    }
    if include_onion:
        try:
            from config import TOR_ENABLED

            onion_on = bool(TOR_ENABLED)
        except Exception:
            onion_on = True
        if onion_on:
            onion = _safe_onion()
            payload["onion"] = onion.get("onion") or onion.get("status")
            payload["onion_digest"] = onion.get("digest")
            payload["onion_items"] = onion.get("items") or []
            payload["onion_errors"] = onion.get("errors") or []
    return payload


def _ctx_macro() -> dict[str, Any]:
    macro = _safe_macro()
    return {
        "intent": INTENT_MACRO,
        "macro": macro.get("macro") or macro.get("status"),
        "macro_digest": macro.get("digest"),
        "macro_errors": macro.get("errors") or [],
    }


def _ctx_threat() -> dict[str, Any]:
    onion = _safe_onion()
    return {
        "intent": INTENT_THREAT_INTEL,
        "onion": onion.get("onion") or onion.get("status"),
        "onion_digest": onion.get("digest"),
        "onion_items": onion.get("items") or [],
        "onion_errors": onion.get("errors") or [],
    }


def _ctx_general() -> dict[str, Any]:
    return {"intent": INTENT_GENERAL}


def trim_llm_context(
    prompt: str,
    fiat_rates: dict[str, float],
    coins: list[dict[str, Any]],
    global_market: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Intent-routed evidence block. General questions get no market dump."""
    try:
        intent = classify_intent(prompt, coins, fiat_rates)
    except Exception:
        intent = INTENT_GENERAL

    if intent == INTENT_FX_CONVERT:
        payload = _ctx_fx(prompt, fiat_rates, coins)
    elif intent == INTENT_ASSET_ANALYSIS:
        payload = _ctx_asset(prompt, fiat_rates, coins)
    elif intent == INTENT_MARKET_OVERVIEW:
        payload = _ctx_overview(coins, global_market)
    elif intent == INTENT_NEWS:
        payload = _ctx_news(include_onion=True)
    elif intent == INTENT_MACRO:
        payload = _ctx_macro()
    elif intent == INTENT_THREAT_INTEL:
        payload = _ctx_threat()
    else:
        payload = _ctx_general()
    payload["intent"] = intent
    return _cap_payload(payload)


def build_system_prompt(context: dict[str, Any]) -> str:
    intent = context.get("intent") or INTENT_GENERAL
    extra = ""
    if intent == INTENT_GENERAL:
        extra += (
            "\nNo live market evidence is attached. Answer from your own knowledge, "
            "fully and directly. Do not invent live prices, rates, or news. "
            "If the question needs current market numbers, say so and offer to pull live data.\n"
        )
        return f"{QUANT_SYSTEM}{extra}"
    if intent in {INTENT_NEWS, INTENT_MACRO, INTENT_THREAT_INTEL}:
        extra += (
            "\nUse ONLY the News (verified, fetched) / MACRO / DARK WEB digest text below. "
            "Analyze listed items only. If status is unavailable, tor_down, or not_configured, "
            "say that data is missing. Do NOT invent headlines, timestamps, or sources.\n"
        )
        blocks = [
            context.get("news_digest"),
            context.get("macro_digest"),
            context.get("onion_digest"),
        ]
        digest = "\n\n".join(b for b in blocks if b)
        payload = json.dumps(context, ensure_ascii=True, allow_nan=False, separators=(",", ":"), default=str)
        return f"{QUANT_SYSTEM}{extra}\n{digest}\nLIVE JSON:\n{payload}"
    if context.get("verified_conversion"):
        extra += (
            "\nA verified conversion has been computed in Python. "
            "Present this exact number. Do NOT recalculate it. Do NOT invent numbers.\n"
        )
    if context.get("verified_ta"):
        extra += (
            "\nPython-verified technical analysis is in verified_ta (bar_interval labeled). "
            "Present those exact indicator values. Do NOT invent RSI/MACD/EMA/Bollinger. "
            "If a field is insufficient_data or null, say so.\n"
        )
    if context.get("news_digest") or context.get("related_news"):
        extra += (
            "\nRelated headlines are only those in news_digest / related_news. "
            "If news status is unavailable, say data is missing. Do not invent headlines.\n"
        )
    payload = json.dumps(context, ensure_ascii=True, allow_nan=False, separators=(",", ":"), default=str)
    digest = context.get("news_digest") or ""
    digest_block = f"\n{digest}\n" if digest else "\n"
    return f"{QUANT_SYSTEM}{extra}{digest_block}LIVE JSON:\n{payload}"


__all__ = [
    "ASSET_TA_HINTS",
    "BROAD_MARKET_HINTS",
    "QUANT_SYSTEM",
    "build_system_prompt",
    "extract_coin_symbols",
    "extract_fiat_codes",
    "pick_coins",
    "trim_llm_context",
]
