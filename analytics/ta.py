from typing import Any, Optional

from analytics.indicators import ema as ema_series
from analytics.indicators import last_value
from analytics.indicators import rsi as rsi_series
from analytics.indicators import sma as sma_series
from analytics.indicators import volatility as volatility_series
from config import STABLECOINS_USD_PEG


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def compact_num(value: Any, digits: int = 6) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def sma(prices: list[float], period: int) -> Optional[float]:
    return last_value(sma_series(prices, period))


def ema(prices: list[float], period: int) -> Optional[float]:
    return last_value(ema_series(prices, period))


def rsi(prices: list[float], period: int = 14) -> Optional[float]:
    return last_value(rsi_series(prices, period))


def volatility_pct(prices: list[float]) -> Optional[float]:
    return last_value(volatility_series(prices, period=14))


def classify_rsi(rsi_value: Optional[float]) -> str:
    if rsi_value is None:
        return "neutral"
    if rsi_value >= 70:
        return "overbought"
    if rsi_value <= 30:
        return "oversold"
    return "neutral"


def classify_trend(
    sma_fast: Optional[float],
    sma_slow: Optional[float],
    ema_fast: Optional[float],
    ema_slow: Optional[float],
) -> str:
    votes = 0
    samples = 0
    if sma_fast is not None and sma_slow is not None:
        samples += 1
        votes += 1 if sma_fast > sma_slow else -1
    if ema_fast is not None and ema_slow is not None:
        samples += 1
        votes += 1 if ema_fast > ema_slow else -1
    if samples == 0:
        return "sideways"
    if votes > 0:
        return "bullish"
    if votes < 0:
        return "bearish"
    return "sideways"


def classify_volatility(vol: Optional[float]) -> str:
    if vol is None:
        return "unknown"
    if vol >= 2.5:
        return "high"
    if vol >= 1.0:
        return "elevated"
    return "low"


def volume_signal(volume: float, market_cap: float, change_24h: float) -> str:
    if market_cap <= 0:
        return "normal"
    turnover = volume / market_cap
    if turnover >= 0.18 and abs(change_24h) >= 3:
        return "spike"
    if turnover >= 0.10:
        return "active"
    return "normal"


def build_insight(
    rsi_value: Optional[float],
    trend: str,
    vol_label: str,
    volume_flag: str,
    change_24h: float,
) -> str:
    rsi_state = classify_rsi(rsi_value)
    parts = []
    if rsi_state == "oversold" and trend != "bearish":
        parts.append("RSI oversold with supportive trend — bounce watch")
    elif rsi_state == "oversold":
        parts.append("RSI oversold in a downtrend — possible mean-reversion, still risky")
    elif rsi_state == "overbought" and trend == "bullish":
        parts.append("RSI overbought in an uptrend — momentum strong, pullback risk")
    elif rsi_state == "overbought":
        parts.append("RSI overbought — cooling / profit-taking risk")
    else:
        parts.append(f"RSI {rsi_state}, trend {trend}")

    if volume_flag == "spike":
        parts.append("volume spike confirms the 24h move")
    if vol_label == "high":
        parts.append("high volatility — size positions carefully")
    if change_24h >= 5 and trend == "bullish":
        parts.append("short-term bullish momentum")
    elif change_24h <= -5 and trend == "bearish":
        parts.append("short-term bearish momentum")
    return "; ".join(parts)


def analyze_sparkline(prices: list[float]) -> dict[str, Any]:
    clean = [safe_float(p) for p in prices if p is not None]
    sma_fast = sma(clean, 12)
    sma_slow = sma(clean, 26)
    ema_fast = ema(clean, 12)
    ema_slow = ema(clean, 26)
    rsi_value = rsi(clean, 14)
    vol = volatility_pct(clean)
    return {
        "sma_12": sma_fast,
        "sma_26": sma_slow,
        "ema_12": ema_fast,
        "ema_26": ema_slow,
        "rsi_14": rsi_value,
        "rsi_state": classify_rsi(rsi_value),
        "trend": classify_trend(sma_fast, sma_slow, ema_fast, ema_slow),
        "volatility_pct": vol,
        "volatility": classify_volatility(vol),
        "bar_interval": "7d sparkline (~hourly samples)",
        "ta_quality": "approximate",
        "label": "7d hourly-sample TA (approximate)",
    }


def enrich_coin(coin: dict[str, Any]) -> dict[str, Any]:
    sparkline = ((coin.get("sparkline_in_7d") or {}).get("price")) or []
    ta = analyze_sparkline(sparkline if isinstance(sparkline, list) else [])
    change_1h = coin.get("price_change_percentage_1h_in_currency")
    change_24h = coin.get("price_change_percentage_24h")
    if change_24h is None:
        change_24h = coin.get("price_change_percentage_24h_in_currency")
    change_7d = coin.get("price_change_percentage_7d_in_currency")
    change_30d = coin.get("price_change_percentage_30d_in_currency")
    volume = safe_float(coin.get("total_volume"))
    market_cap = safe_float(coin.get("market_cap"))
    change_24h_n = safe_float(change_24h)
    vol_flag = volume_signal(volume, market_cap, change_24h_n)
    symbol = str(coin.get("symbol") or "").upper()
    return {
        "id": coin.get("id") or "",
        "name": coin.get("name") or "N/A",
        "symbol": symbol,
        "is_usd_stablecoin": symbol in STABLECOINS_USD_PEG,
        "price_usd": safe_float(coin.get("current_price")),
        "change_1h_pct": None if change_1h is None else safe_float(change_1h),
        "change_24h_pct": None if change_24h is None else safe_float(change_24h),
        "change_7d_pct": None if change_7d is None else safe_float(change_7d),
        "change_30d_pct": None if change_30d is None else safe_float(change_30d),
        "volume_24h_usd": volume,
        "market_cap_usd": market_cap,
        "ath_usd": safe_float(coin.get("ath")),
        "ath_change_pct": None if coin.get("ath_change_percentage") is None else safe_float(coin.get("ath_change_percentage")),
        "atl_usd": safe_float(coin.get("atl")),
        "atl_change_pct": None if coin.get("atl_change_percentage") is None else safe_float(coin.get("atl_change_percentage")),
        "ta": ta,
        "volume_signal": vol_flag,
        "insight": build_insight(ta["rsi_14"], ta["trend"], ta["volatility"], vol_flag, change_24h_n),
    }


def coin_card(coin: dict[str, Any]) -> dict[str, Any]:
    ta = coin["ta"]
    return {
        "name": coin["name"],
        "symbol": coin["symbol"],
        "peg_1_usd": coin["is_usd_stablecoin"],
        "price_usd": compact_num(coin["price_usd"], 8),
        "chg_1h": compact_num(coin["change_1h_pct"], 3),
        "chg_24h": compact_num(coin["change_24h_pct"], 3),
        "chg_7d": compact_num(coin["change_7d_pct"], 3),
        "chg_30d": compact_num(coin.get("change_30d_pct"), 3),
        "vol_24h": compact_num(coin["volume_24h_usd"], 0),
        "mcap": compact_num(coin["market_cap_usd"], 0),
        "ath_chg": compact_num(coin["ath_change_pct"], 2),
        "atl_chg": compact_num(coin["atl_change_pct"], 2),
        "sma12": compact_num(ta["sma_12"], 6),
        "sma26": compact_num(ta["sma_26"], 6),
        "ema12": compact_num(ta["ema_12"], 6),
        "ema26": compact_num(ta["ema_26"], 6),
        "rsi14": compact_num(ta["rsi_14"], 2),
        "rsi": ta["rsi_state"],
        "trend": ta["trend"],
        "volatility": ta["volatility"],
        "vol_sig": coin["volume_signal"],
        "ta_note": coin["insight"],
        "ta_label": ta.get("label") or "7d hourly-sample TA (approximate)",
        "bar_interval": ta.get("bar_interval"),
        "ta_quality": ta.get("ta_quality") or "approximate",
    }
