from typing import Any

import requests
import streamlit as st

from config import HTTP_TIMEOUT

try:
    from config import HISTORY_CACHE_TTL_SECONDS
except Exception:
    HISTORY_CACHE_TTL_SECONDS = 300

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_CHART_DAYS = (1, 7, 14, 30, 90, 180, 365)
_OHLC_DAYS = (1, 7, 14, 30, 90, 180, 365)


def _snap_days(days: int, allowed: tuple[int, ...]) -> int:
    try:
        wanted = int(days)
    except (TypeError, ValueError):
        wanted = 7
    if wanted <= 0:
        wanted = 7
    return min(allowed, key=lambda d: (abs(d - wanted), d))


def bar_interval_for_days(days: int) -> str:
    """Label bars the way this app uses them: hourly if days<=90, else daily."""
    return "1h" if days <= 90 else "1d"


def _http_json(url: str) -> Any:
    res = requests.get(url, timeout=max(HTTP_TIMEOUT, 15))
    res.raise_for_status()
    return res.json()


@st.cache_data(ttl=HISTORY_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_market_chart(
    coin_id: str,
    days: int,
    vs_currency: str = "usd",
) -> dict[str, Any]:
    """On-demand CoinGecko market_chart. Cached 5 minutes. Not used on dashboard load."""
    coin_id = str(coin_id or "").strip()
    if not coin_id:
        return {"prices": [], "market_caps": [], "total_volumes": [], "days": days, "status": "missing_id"}
    snapped = _snap_days(days, _CHART_DAYS)
    url = (
        f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        f"?vs_currency={vs_currency}&days={snapped}"
    )
    try:
        payload = _http_json(url)
    except Exception as exc:
        return {
            "prices": [],
            "market_caps": [],
            "total_volumes": [],
            "days": snapped,
            "status": "fetch_failed",
            "error": str(exc),
        }
    if not isinstance(payload, dict):
        return {"prices": [], "market_caps": [], "total_volumes": [], "days": snapped, "status": "fetch_failed"}
    return {
        "prices": payload.get("prices") or [],
        "market_caps": payload.get("market_caps") or [],
        "total_volumes": payload.get("total_volumes") or [],
        "days": snapped,
        "status": "ok",
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "bar_interval": bar_interval_for_days(snapped),
    }


@st.cache_data(ttl=HISTORY_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_ohlc(coin_id: str, days: int) -> dict[str, Any]:
    coin_id = str(coin_id or "").strip()
    if not coin_id:
        return {"ohlc": [], "days": days, "status": "missing_id"}
    snapped = _snap_days(days, _OHLC_DAYS)
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={snapped}"
    try:
        payload = _http_json(url)
    except Exception as exc:
        return {"ohlc": [], "days": snapped, "status": "fetch_failed", "error": str(exc)}
    if not isinstance(payload, list):
        return {"ohlc": [], "days": snapped, "status": "fetch_failed"}
    return {
        "ohlc": payload,
        "days": snapped,
        "status": "ok",
        "coin_id": coin_id,
        "bar_interval": bar_interval_for_days(snapped),
    }


__all__ = ["bar_interval_for_days", "fetch_market_chart", "fetch_ohlc"]
