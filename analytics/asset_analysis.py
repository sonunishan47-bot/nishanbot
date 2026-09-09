from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from analytics import indicators as ind
from analytics.ta import classify_rsi, compact_num
from data.history import bar_interval_for_days, fetch_market_chart, fetch_ohlc


def _closes_from_prices(prices: list) -> pd.Series:
    pairs: list[tuple[pd.Timestamp, float]] = []
    for item in prices or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            ts = pd.to_datetime(item[0], unit="ms", utc=True)
            px = float(item[1])
        except (TypeError, ValueError):
            continue
        pairs.append((ts, px))
    if not pairs:
        return pd.Series(dtype="float64")
    return pd.Series({t: p for t, p in pairs}).sort_index()


def _closes_from_ohlc(ohlc: list) -> pd.Series:
    pairs: list[tuple[pd.Timestamp, float]] = []
    for item in ohlc or []:
        if not isinstance(item, (list, tuple)) or len(item) < 5:
            continue
        try:
            ts = pd.to_datetime(item[0], unit="ms", utc=True)
            close = float(item[4])
        except (TypeError, ValueError):
            continue
        pairs.append((ts, close))
    if not pairs:
        return pd.Series(dtype="float64")
    return pd.Series({t: p for t, p in pairs}).sort_index()


def _resample_closes(closes: pd.Series, days: int) -> pd.Series:
    if closes.empty:
        return closes
    if not isinstance(closes.index, pd.DatetimeIndex):
        return closes
    rule = "1h" if days <= 90 else "1D"
    return closes.resample(rule).last().dropna()


def _pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    try:
        return ((float(a) / float(b)) - 1.0) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _trend_vote(
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    macd_line: Optional[float],
    macd_hist: Optional[float],
    prev_hist: Optional[float],
) -> tuple[str, str]:
    notes = []
    score = 0
    if price is not None and ema20 is not None:
        if price > ema20:
            score += 1
            notes.append("price > EMA20")
        else:
            score -= 1
            notes.append("price < EMA20")
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            score += 1
            notes.append("EMA20 > EMA50")
        else:
            score -= 1
            notes.append("EMA20 < EMA50")
    if macd_line is not None:
        if macd_line > 0:
            score += 1
            notes.append("MACD positive")
        else:
            score -= 1
            notes.append("MACD negative")
    if macd_hist is not None and prev_hist is not None:
        if macd_hist > prev_hist:
            notes.append("MACD hist rising")
        elif macd_hist < prev_hist:
            notes.append("MACD hist falling")
    if score > 0:
        trend = "bullish"
    elif score < 0:
        trend = "bearish"
    else:
        trend = "sideways"
    return trend, ", ".join(notes) if notes else "insufficient structure"


def parse_history_days(prompt: str) -> int:
    text = (prompt or "").lower()
    if any(k in text for k in ("1y", "365", "year", "annual")):
        return 365
    if "daily" in text or "1d bar" in text:
        return 180
    if any(k in text for k in ("180", "6m", "6 month")):
        return 180
    if any(k in text for k in ("90d", "90 day", "3m", "3 month")):
        return 90
    if any(k in text for k in ("30d", "30-day", "30 day", "1m", "month")):
        return 30
    if any(k in text for k in ("14d", "2w")):
        return 14
    if any(k in text for k in ("24h", "today")):
        return 1
    if any(k in text for k in ("7d", "week", "weekly")):
        return 7
    return 30


def analyze_asset(
    coin: dict[str, Any],
    days: int = 30,
) -> dict[str, Any]:
    coin_id = str(coin.get("id") or "").strip()
    symbol = str(coin.get("symbol") or "").upper()
    name = coin.get("name") or symbol
    snapped_interval = bar_interval_for_days(days)
    if not coin_id:
        return {
            "status": "insufficient_data",
            "reason": "missing CoinGecko id",
            "symbol": symbol,
            "bar_interval": snapped_interval,
            "source": "python_calculated",
        }

    chart = fetch_market_chart(coin_id, days)
    closes = _closes_from_prices(chart.get("prices") or [])
    if closes.empty:
        ohlc = fetch_ohlc(coin_id, days)
        closes = _closes_from_ohlc(ohlc.get("ohlc") or [])
        days_used = int(ohlc.get("days") or days)
    else:
        days_used = int(chart.get("days") or days)

    if chart.get("status") == "fetch_failed" and closes.empty:
        return {
            "status": "fetch_failed",
            "reason": chart.get("error") or "CoinGecko history unavailable",
            "symbol": symbol,
            "bar_interval": bar_interval_for_days(days_used),
            "source": "python_calculated",
        }

    closes = _resample_closes(closes, days_used)
    bar_interval = bar_interval_for_days(days_used)
    bars_per_year = 24 * 365 if bar_interval == "1h" else 365

    if closes.empty or len(closes) < 16:
        return {
            "status": "insufficient_data",
            "reason": "not enough historical bars for RSI(14)",
            "symbol": symbol,
            "name": name,
            "coin_id": coin_id,
            "days": days_used,
            "bar_interval": bar_interval,
            "bars": int(len(closes)),
            "source": "python_calculated",
        }

    price = ind.last_value(closes)
    rsi_s = ind.rsi(closes, 14)
    sma20_s = ind.sma(closes, 20)
    sma50_s = ind.sma(closes, 50)
    ema20_s = ind.ema(closes, 20)
    ema50_s = ind.ema(closes, 50)
    macd_pack = ind.macd(closes, 12, 26, 9)
    bb_pack = ind.bollinger(closes, 20, 2)
    vol_bar = ind.volatility(closes, 14)
    vol_ann = ind.volatility(closes, 14, bars_per_year=bars_per_year)
    mom = ind.momentum(closes, 14)
    sr = ind.support_resistance(closes)

    macd_line = macd_signal = macd_hist = prev_hist = None
    macd_hist_rising = None
    if macd_pack is not None:
        macd_line = ind.last_value(macd_pack[0])
        macd_signal = ind.last_value(macd_pack[1])
        hist_s = macd_pack[2].dropna()
        macd_hist = float(hist_s.iloc[-1]) if not hist_s.empty else None
        prev_hist = float(hist_s.iloc[-2]) if len(hist_s) >= 2 else None
        if macd_hist is not None and prev_hist is not None:
            macd_hist_rising = macd_hist > prev_hist

    bb_upper = bb_mid = bb_lower = None
    if bb_pack is not None:
        bb_upper = ind.last_value(bb_pack[0])
        bb_mid = ind.last_value(bb_pack[1])
        bb_lower = ind.last_value(bb_pack[2])

    rsi_v = ind.last_value(rsi_s)
    ema20 = ind.last_value(ema20_s)
    ema50 = ind.last_value(ema50_s)
    trend, trend_notes = _trend_vote(price, ema20, ema50, macd_line, macd_hist, prev_hist)

    change_24h = None
    if bar_interval == "1h" and len(closes) > 24:
        change_24h = _pct(price, float(closes.iloc[-25]))
    elif bar_interval == "1d" and len(closes) > 1:
        change_24h = _pct(price, float(closes.iloc[-2]))
    change_7d = None
    lookback_7 = 24 * 7 if bar_interval == "1h" else 7
    if len(closes) > lookback_7:
        change_7d = _pct(price, float(closes.iloc[-(lookback_7 + 1)]))

    evidence = {
        "status": "ok",
        "source": "python_calculated",
        "symbol": symbol,
        "name": name,
        "coin_id": coin_id,
        "days": days_used,
        "bar_interval": bar_interval,
        "bars": int(len(closes)),
        "price_usd": compact_num(price, 8),
        "chg_24h_from_bars": compact_num(change_24h, 3),
        "chg_7d_from_bars": compact_num(change_7d, 3),
        "chg_1h_snapshot": compact_num(coin.get("change_1h_pct"), 3),
        "chg_24h_snapshot": compact_num(coin.get("change_24h_pct"), 3),
        "chg_7d_snapshot": compact_num(coin.get("change_7d_pct"), 3),
        "chg_30d_snapshot": compact_num(coin.get("change_30d_pct"), 3),
        "rsi_14": compact_num(rsi_v, 2),
        "rsi_state": classify_rsi(rsi_v),
        "sma_20": compact_num(ind.last_value(sma20_s), 6),
        "sma_50": compact_num(ind.last_value(sma50_s), 6),
        "ema_20": compact_num(ema20, 6),
        "ema_50": compact_num(ema50, 6),
        "macd_line": compact_num(macd_line, 6),
        "macd_signal": compact_num(macd_signal, 6),
        "macd_histogram": compact_num(macd_hist, 6),
        "macd_hist_rising": macd_hist_rising,
        "bollinger_upper": compact_num(bb_upper, 6),
        "bollinger_middle": compact_num(bb_mid, 6),
        "bollinger_lower": compact_num(bb_lower, 6),
        "volatility_14_pct_per_bar": compact_num(ind.last_value(vol_bar), 4),
        "volatility_14_annualized_pct": compact_num(ind.last_value(vol_ann), 2),
        "momentum_14_pct": compact_num(ind.last_value(mom), 3),
        "support": [compact_num(x, 6) for x in sr.get("support", [])],
        "resistance": [compact_num(x, 6) for x in sr.get("resistance", [])],
        "trend": trend,
        "trend_notes": trend_notes,
    }
    missing = [
        name_k
        for name_k, val in (
            ("RSI(14)", evidence["rsi_14"]),
            ("EMA20", evidence["ema_20"]),
            ("EMA50", evidence["ema_50"]),
            ("MACD", evidence["macd_line"]),
            ("Bollinger", evidence["bollinger_upper"]),
        )
        if val is None
    ]
    evidence["insufficient_fields"] = missing
    evidence["summary"] = format_ta_summary(evidence)
    return evidence


def format_ta_summary(ev: dict[str, Any]) -> str:
    if ev.get("status") != "ok":
        return (
            f"{ev.get('symbol')}: {ev.get('status')} "
            f"({ev.get('reason') or 'unavailable'}). bar_interval={ev.get('bar_interval')}."
        )

    def n(val: Any, kind: str = "num") -> str:
        if val is None:
            return "insufficient data"
        if kind == "usd":
            return f"${val:,.2f}" if abs(float(val)) >= 1 else f"${val}"
        if kind == "pct":
            return f"{val:+.2f}%"
        return f"{val}"

    hist = ev.get("macd_histogram")
    rising = ev.get("macd_hist_rising")
    hist_note = "n/a"
    if hist is not None:
        hist_note = f"hist {hist:+.2f}"
        if rising is True:
            hist_note += ", rising"
        elif rising is False:
            hist_note += ", falling"

    vol = ev.get("volatility_14_pct_per_bar")
    vol_txt = f"{vol:.2f}%/{ev.get('bar_interval')} bar" if vol is not None else "insufficient data"
    supports = ", ".join(n(x, "usd") for x in (ev.get("support") or []) if x is not None) or "insufficient data"
    resists = ", ".join(n(x, "usd") for x in (ev.get("resistance") or []) if x is not None) or "insufficient data"
    macd_line = ev.get("macd_line")
    macd_txt = f"{macd_line:+.2f} ({hist_note})" if macd_line is not None else "insufficient data"

    return (
        f"{ev.get('symbol')} ({ev.get('days')}d chart, {ev.get('bar_interval')} bars, "
        f"{ev.get('bars')} samples, python-verified):\n"
        f"Price: {n(ev.get('price_usd'), 'usd')} | 24h: {n(ev.get('chg_24h_snapshot'), 'pct')} | "
        f"7d: {n(ev.get('chg_7d_snapshot'), 'pct')} | 30d: {n(ev.get('chg_30d_snapshot'), 'pct')}\n"
        f"RSI(14): {n(ev.get('rsi_14'))} ({ev.get('rsi_state')}) | "
        f"EMA20: {n(ev.get('ema_20'), 'usd')} | EMA50: {n(ev.get('ema_50'), 'usd')}\n"
        f"SMA20: {n(ev.get('sma_20'), 'usd')} | SMA50: {n(ev.get('sma_50'), 'usd')}\n"
        f"MACD: {macd_txt} | Bollinger: upper {n(ev.get('bollinger_upper'), 'usd')} / "
        f"lower {n(ev.get('bollinger_lower'), 'usd')}\n"
        f"Volatility(14): {vol_txt} | Support: {supports} | Resistance: {resists}\n"
        f"Trend: {ev.get('trend')} ({ev.get('trend_notes')})"
    )
