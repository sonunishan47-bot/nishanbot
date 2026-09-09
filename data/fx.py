from typing import Any

import requests

from config import FIAT_RATES_URL, HTTP_TIMEOUT


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _http_json(url: str) -> Any:
    res = requests.get(url, timeout=HTTP_TIMEOUT)
    res.raise_for_status()
    return res.json()


def fetch_fiat_rates() -> dict[str, float]:
    payload = _http_json(FIAT_RATES_URL)
    if payload.get("result") != "success":
        return {}
    raw_rates = payload.get("rates") or {}
    return {str(k).upper(): safe_float(v) for k, v in raw_rates.items()}
