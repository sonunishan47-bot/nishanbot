"""Shared snapshot cache, formatters, and session init. Caching logic matches the pre-Phase-6 app."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import streamlit as st

import config
from analytics.ta import enrich_coin, safe_float
from data.crypto import fetch_crypto_markets, fetch_global_market
from data.fx import fetch_fiat_rates

CACHE_TTL_SECONDS = getattr(config, "CACHE_TTL_SECONDS", 30)
CHAT_HISTORY_TURNS = getattr(config, "CHAT_HISTORY_TURNS", 6)
ERROR_CACHE_TTL_SECONDS = getattr(config, "ERROR_CACHE_TTL_SECONDS", 60)
HISTORY_CACHE_TTL_SECONDS = getattr(config, "HISTORY_CACHE_TTL_SECONDS", 300)
STABLECOINS_USD_PEG = getattr(
    config, "STABLECOINS_USD_PEG", ("USDT", "FDUSD", "USDC", "DAI", "BUSD")
)
POPULAR_FIATS = ("SAR", "AED", "INR", "KWD", "EUR", "GBP", "PKR", "JPY", "CNY")


def fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def fmt_usd(value: Any, decimals: int = 2) -> str:
    number = safe_float(value, 0.0)
    if abs(number) >= 1:
        return f"${number:,.{decimals}f}"
    return f"${number:.8f}".rstrip("0").rstrip(".")


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _fetch_live_snapshot() -> tuple[dict[str, float], list[dict[str, Any]]]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        fiat_future = pool.submit(fetch_fiat_rates)
        crypto_future = pool.submit(fetch_crypto_markets)
        try:
            fiat_rates = fiat_future.result()
        except Exception:
            fiat_rates = {}
        try:
            raw_coins = crypto_future.result()
        except Exception:
            raw_coins = []
    return fiat_rates, [enrich_coin(coin) for coin in raw_coins]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_ok_snapshot() -> tuple[dict[str, float], list[dict[str, Any]]]:
    fiat_rates, coins = _fetch_live_snapshot()
    if not fiat_rates or not coins:
        raise RuntimeError("incomplete_snapshot")
    return fiat_rates, coins


@st.cache_data(ttl=ERROR_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_retry_snapshot() -> tuple[dict[str, float], list[dict[str, Any]]]:
    return _fetch_live_snapshot()


def load_live_snapshot() -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Cache complete snapshots for 30s. Incomplete/failed fetches retry after 5s, not 30s."""
    try:
        return _cached_ok_snapshot()
    except Exception:
        _cached_ok_snapshot.clear()
        return _cached_retry_snapshot()


@st.cache_data(ttl=HISTORY_CACHE_TTL_SECONDS, show_spinner=False)
def load_global_market() -> dict[str, Any]:
    try:
        data = fetch_global_market()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_app_data() -> tuple[dict[str, float], list[dict[str, Any]], dict[str, Any]]:
    try:
        fiat_rates, coins = load_live_snapshot()
    except Exception:
        fiat_rates, coins = {}, []
        st.warning("Live snapshot failed. UI will retry on the next cache window.")
    global_market = load_global_market()
    return fiat_rates, coins, global_market
