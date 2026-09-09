from __future__ import annotations

from typing import Optional, Union

import pandas as pd

NumberSeries = Union[pd.Series, list, tuple]


def _as_series(values: NumberSeries) -> pd.Series:
    if isinstance(values, pd.Series):
        s = pd.to_numeric(values, errors="coerce")
        return s
    return pd.to_numeric(pd.Series(list(values), dtype="float64"), errors="coerce")


def last_value(series: Optional[pd.Series]) -> Optional[float]:
    if series is None:
        return None
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return float(clean.iloc[-1])


def sma(series: NumberSeries, period: int = 20) -> Optional[pd.Series]:
    if period <= 0:
        return None
    s = _as_series(series).dropna()
    if len(s) < period:
        return None
    return s.rolling(window=period, min_periods=period).mean()


def ema(series: NumberSeries, period: int = 20) -> Optional[pd.Series]:
    if period <= 0:
        return None
    s = _as_series(series).dropna()
    if len(s) < period:
        return None
    return s.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: NumberSeries, period: int = 14) -> Optional[pd.Series]:
    """Wilder's RSI. Needs period+1 prices. Returns None if the series is too short."""
    if period <= 0:
        return None
    s = _as_series(series).dropna()
    if len(s) < period + 1:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = pd.Series(index=s.index, dtype="float64")
    avg_loss = pd.Series(index=s.index, dtype="float64")
    avg_gain.iloc[period] = float(gain.iloc[1 : period + 1].mean())
    avg_loss.iloc[period] = float(loss.iloc[1 : period + 1].mean())
    out = pd.Series(index=s.index, dtype="float64")
    for i in range(period + 1, len(s)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + float(gain.iloc[i])) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + float(loss.iloc[i])) / period
    for i in range(period, len(s)):
        ag = float(avg_gain.iloc[i])
        al = float(avg_loss.iloc[i])
        if al == 0.0 and ag == 0.0:
            out.iloc[i] = 50.0
        elif al == 0.0:
            out.iloc[i] = 100.0
        else:
            rs = ag / al
            out.iloc[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def macd(
    series: NumberSeries,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Optional[tuple[pd.Series, pd.Series, pd.Series]]:
    s = _as_series(series).dropna()
    if fast <= 0 or slow <= 0 or signal <= 0 or fast >= slow:
        return None
    if len(s) < slow + signal:
        return None
    ema_fast = s.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = s.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger(
    series: NumberSeries,
    period: int = 20,
    std: float = 2.0,
) -> Optional[tuple[pd.Series, pd.Series, pd.Series]]:
    s = _as_series(series).dropna()
    if period <= 0 or len(s) < period:
        return None
    middle = s.rolling(window=period, min_periods=period).mean()
    dev = s.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + std * dev
    lower = middle - std * dev
    return upper, middle, lower


def volatility(
    series: NumberSeries,
    period: int = 14,
    bars_per_year: Optional[float] = None,
) -> Optional[pd.Series]:
    """Rolling stdev of percent returns, in percent per bar.

    If bars_per_year is set, the series is annualized (std * sqrt(bars_per_year) * 100).
    Otherwise values are % per bar (std of returns * 100).
    """
    if period <= 1:
        return None
    s = _as_series(series).dropna()
    if len(s) < period + 1:
        return None
    rets = s.pct_change()
    rolling = rets.rolling(window=period, min_periods=period).std(ddof=0)
    if bars_per_year:
        return rolling * (bars_per_year ** 0.5) * 100.0
    return rolling * 100.0


def momentum(series: NumberSeries, period: int = 14) -> Optional[pd.Series]:
    if period <= 0:
        return None
    s = _as_series(series).dropna()
    if len(s) < period + 1:
        return None
    return s.pct_change(periods=period) * 100.0


def support_resistance(
    series: NumberSeries,
    lookback: int = 80,
    prominence: int = 3,
) -> dict[str, list[float]]:
    s = _as_series(series).dropna()
    if len(s) < prominence * 2 + 5:
        return {"support": [], "resistance": []}
    window = s.iloc[-min(lookback, len(s)) :]
    vals = window.to_numpy(dtype="float64")
    supports: list[float] = []
    resistances: list[float] = []
    for i in range(prominence, len(vals) - prominence):
        left = vals[i - prominence : i]
        right = vals[i + 1 : i + 1 + prominence]
        v = vals[i]
        if v <= left.min() and v <= right.min():
            supports.append(float(v))
        if v >= left.max() and v >= right.max():
            resistances.append(float(v))
    return {
        "support": supports[-2:],
        "resistance": resistances[-2:],
    }
