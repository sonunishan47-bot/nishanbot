"""Run with: python tests/test_converter.py  (no extra dependencies)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.converter import convert
from ai.intent import parse_conversion_request
from ai.context import trim_llm_context


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
        "name": "Bitcoin",
        "symbol": "BTC",
        "price_usd": 112450.0,
        "is_usd_stablecoin": False,
        "change_1h_pct": None,
        "change_24h_pct": None,
        "change_7d_pct": None,
        "volume_24h_usd": 0,
        "market_cap_usd": 0,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
    {
        "name": "Ethereum",
        "symbol": "ETH",
        "price_usd": 2493.08,
        "is_usd_stablecoin": False,
        "change_1h_pct": None,
        "change_24h_pct": None,
        "change_7d_pct": None,
        "volume_24h_usd": 0,
        "market_cap_usd": 0,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
    {
        "name": "Tether",
        "symbol": "USDT",
        "price_usd": 1.0,
        "is_usd_stablecoin": True,
        "change_1h_pct": None,
        "change_24h_pct": None,
        "change_7d_pct": None,
        "volume_24h_usd": 0,
        "market_cap_usd": 0,
        "ath_change_pct": None,
        "atl_change_pct": None,
        "ta": _TA,
        "volume_signal": "normal",
        "insight": "",
    },
]


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_btc_to_inr() -> None:
    out = convert(1, "BTC", "INR", fiat_rates=FIAT, coins=COINS)
    expected = 1 * 112450.0 * 94.544084
    _assert(out["status"] == "ok", f"status {out['status']}")
    _assert(out["source"] == "python_calculated", "source")
    _assert(out["result"] == expected, f"result {out['result']} != {expected}")
    _assert(out["result"] > 1_000_000, "BTC→INR must be far above the FX rate alone")
    _assert(out["base_usd_price"] == 112450.0, "base usd")
    _assert(out["fx_rate_used"] == 94.544084, "fx")


def test_usdt_to_pkr() -> None:
    out = convert(100, "USDT", "PKR", fiat_rates=FIAT, coins=COINS)
    expected = 100 * 278.5
    _assert(out["status"] == "ok", f"status {out['status']}")
    _assert(out["result"] == expected, f"result {out['result']} != {expected}")
    _assert(out["base_usd_price"] == 1.0, "stable peg")


def test_usd_to_eur() -> None:
    out = convert(1, "USD", "EUR", fiat_rates=FIAT, coins=COINS)
    _assert(out["status"] == "ok", f"status {out['status']}")
    _assert(out["result"] == 0.92, f"result {out['result']}")
    _assert(out["fx_rate_used"] == 0.92, "fx")


def test_unknown_base_price_missing() -> None:
    out = convert(1, "XYZ", "INR", fiat_rates=FIAT, coins=COINS)
    _assert(out["status"] == "price_missing", f"status {out['status']}")
    _assert(out["result"] is None, f"result must not be 0, got {out['result']}")


def test_unknown_target_fx_missing() -> None:
    out = convert(1, "USD", "ZZZ", fiat_rates=FIAT, coins=COINS)
    _assert(out["status"] == "fx_missing", f"status {out['status']}")
    _assert(out["result"] is None, f"result must not be 0, got {out['result']}")


def test_parse_and_trim_injects_verified() -> None:
    parsed = parse_conversion_request("1 BTC in INR", FIAT, COINS)
    _assert(parsed is not None, "parse BTC in INR")
    _assert(parsed["base"] == "BTC" and parsed["target"] == "INR", str(parsed))
    ctx = trim_llm_context("1 BTC in INR", FIAT, COINS)
    verified = ctx.get("verified_conversion") or {}
    _assert(verified.get("status") == "ok", str(verified))
    _assert(verified.get("result") == 1 * 112450.0 * 94.544084, str(verified.get("result")))

    usdt = parse_conversion_request("100 USDT to PKR", FIAT, COINS)
    _assert(usdt is not None and usdt["amount"] == 100, str(usdt))
    usd = parse_conversion_request("1 USD to EUR", FIAT, COINS)
    _assert(usd is not None and usd["base"] == "USD" and usd["target"] == "EUR", str(usd))
    missing = trim_llm_context("XYZ to INR", FIAT, COINS)["verified_conversion"]
    _assert(missing["status"] == "price_missing", str(missing))
    _assert(missing["result"] is None, str(missing))


if __name__ == "__main__":
    test_btc_to_inr()
    test_usdt_to_pkr()
    test_usd_to_eur()
    test_unknown_base_price_missing()
    test_unknown_target_fx_missing()
    test_parse_and_trim_injects_verified()
    print("converter tests passed")
