import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from typing import Any

import requests

from config import COINGECKO_GLOBAL_URL, COINGECKO_MARKETS_URL, HTTP_TIMEOUT

__all__ = ["fetch_crypto_markets", "fetch_global_market"]


def _http_json(url: str) -> Any:
    res = requests.get(url, timeout=HTTP_TIMEOUT)
    res.raise_for_status()
    return res.json()


def fetch_crypto_markets() -> list[dict[str, Any]]:
    payload = _http_json(COINGECKO_MARKETS_URL)
    return payload if isinstance(payload, list) else []


def fetch_global_market() -> dict[str, Any]:
    payload = _http_json(COINGECKO_GLOBAL_URL)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {}
    mcap = data.get("total_market_cap") or {}
    volume = data.get("total_volume") or {}
    dominance = data.get("market_cap_percentage") or {}
    return {
        "btc_dominance_pct": dominance.get("btc"),
        "eth_dominance_pct": dominance.get("eth"),
        "total_market_cap_usd": mcap.get("usd"),
        "total_volume_usd": volume.get("usd"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
        "markets": data.get("markets"),
        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
    }
if __name__ == "__main__":
    print(fetch_global_market())