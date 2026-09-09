"""Run with: python tests/test_indicators.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from analytics.indicators import last_value, macd, rsi, sma


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_short_series_insufficient() -> None:
    short = pd.Series([1.0, 1.1, 1.2])
    _assert(rsi(short, 14) is None, "short RSI must be None")
    _assert(sma(short, 20) is None, "short SMA must be None")
    _assert(macd(short) is None, "short MACD must be None")


def test_wilder_rsi_not_simple_mean() -> None:
    # Monotonic rise then a drop — Wilder RSI uses smoothed avg gain/loss.
    prices = [float(i) for i in range(1, 40)] + [35.0, 34.0, 33.0]
    wilder = last_value(rsi(prices, 14))
    _assert(wilder is not None, "RSI should compute")
    _assert(0 < wilder < 100, f"RSI out of range {wilder}")
    # Simple last-14 mean RSI (old sparkline method) differs on this path.
    window = prices[-(14 + 1) :]
    gains = losses = 0.0
    for i in range(1, len(window)):
        d = window[i] - window[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_gain = gains / 14
    avg_loss = losses / 14
    simple = 100 - (100 / (1 + avg_gain / avg_loss))
    _assert(abs(wilder - simple) > 0.01, f"Wilder {wilder} should differ from simple {simple}")


def test_macd_on_trend() -> None:
    prices = [100 + i * 0.5 for i in range(80)]
    pack = macd(prices)
    _assert(pack is not None, "MACD should compute")
    line, signal, hist = pack
    _assert(last_value(line) is not None, "macd line")
    _assert(last_value(signal) is not None, "signal")
    _assert(last_value(hist) is not None, "hist")


if __name__ == "__main__":
    test_short_series_insufficient()
    test_wilder_rsi_not_simple_mean()
    test_macd_on_trend()
    print("indicator tests passed")
