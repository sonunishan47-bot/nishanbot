import pandas as pd
import streamlit as st

from analytics.asset_analysis import analyze_asset
from ui.setup import fmt_pct, fmt_usd, init_session, load_app_data

_DAY_OPTIONS = (7, 14, 30, 90, 180, 365)


def _fmt_num(value, kind: str = "num") -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if kind == "usd":
        return fmt_usd(number)
    if kind == "pct":
        return fmt_pct(number)
    return str(number)


def render_asset() -> None:
    init_session()
    st.title("📈 Asset analysis")
    st.caption("Phase 4 CoinGecko history TA. Indicators are python-calculated. Interval is labeled.")

    _fiat_rates, coins, _global_market = load_app_data()
    if not coins:
        st.info("No coins in the live snapshot yet.")
        return

    labels = [f"{c['symbol']} — {c['name']}" for c in coins]
    default_idx = next((i for i, c in enumerate(coins) if c["symbol"] == "BTC"), 0)
    col_coin, col_days = st.columns([2, 1])
    with col_coin:
        choice = st.selectbox("Coin", labels, index=default_idx)
    with col_days:
        days = st.selectbox("History window (days)", list(_DAY_OPTIONS), index=_DAY_OPTIONS.index(30))

    coin = coins[labels.index(choice)]
    evidence = analyze_asset(coin, days)

    st.metric(
        f"{evidence.get('symbol') or coin['symbol']}",
        fmt_usd(evidence.get("price_usd") if evidence.get("price_usd") is not None else coin.get("price_usd")),
        fmt_pct(evidence.get("chg_24h_snapshot")),
    )
    st.write(
        f"**bar_interval:** `{evidence.get('bar_interval')}` · "
        f"**days:** {evidence.get('days')} · **bars:** {evidence.get('bars')} · "
        f"**status:** {evidence.get('status')} · **source:** {evidence.get('source')}"
    )

    if evidence.get("status") != "ok":
        st.warning(evidence.get("reason") or evidence.get("status"))

    rows = [
        ("RSI(14)", _fmt_num(evidence.get("rsi_14")), evidence.get("rsi_state") or "n/a"),
        ("EMA20", _fmt_num(evidence.get("ema_20"), "usd"), "python-calculated"),
        ("EMA50", _fmt_num(evidence.get("ema_50"), "usd"), "python-calculated"),
        ("SMA20", _fmt_num(evidence.get("sma_20"), "usd"), "python-calculated"),
        ("SMA50", _fmt_num(evidence.get("sma_50"), "usd"), "python-calculated"),
        ("MACD line", _fmt_num(evidence.get("macd_line")), f"hist rising={evidence.get('macd_hist_rising')}"),
        ("MACD signal", _fmt_num(evidence.get("macd_signal")), ""),
        ("MACD histogram", _fmt_num(evidence.get("macd_histogram")), ""),
        ("Bollinger upper", _fmt_num(evidence.get("bollinger_upper"), "usd"), ""),
        ("Bollinger middle", _fmt_num(evidence.get("bollinger_middle"), "usd"), ""),
        ("Bollinger lower", _fmt_num(evidence.get("bollinger_lower"), "usd"), ""),
        ("Volatility(14) %/bar", _fmt_num(evidence.get("volatility_14_pct_per_bar"), "pct"), evidence.get("bar_interval")),
        ("Volatility(14) ann.", _fmt_num(evidence.get("volatility_14_annualized_pct"), "pct"), ""),
        ("Momentum(14)", _fmt_num(evidence.get("momentum_14_pct"), "pct"), ""),
        ("Support", ", ".join(_fmt_num(x, "usd") for x in (evidence.get("support") or []) if x is not None) or "n/a", ""),
        ("Resistance", ", ".join(_fmt_num(x, "usd") for x in (evidence.get("resistance") or []) if x is not None) or "n/a", ""),
        ("Trend", evidence.get("trend") or "n/a", evidence.get("trend_notes") or ""),
        ("24h (snapshot)", _fmt_num(evidence.get("chg_24h_snapshot"), "pct"), ""),
        ("7d (snapshot)", _fmt_num(evidence.get("chg_7d_snapshot"), "pct"), ""),
        ("30d (snapshot)", _fmt_num(evidence.get("chg_30d_snapshot"), "pct"), ""),
    ]
    st.dataframe(
        pd.DataFrame(rows, columns=["Indicator", "Value", "Notes"]),
        hide_index=True,
        use_container_width=True,
    )
    if evidence.get("summary"):
        st.subheader("Summary")
        st.text(evidence["summary"])
    missing = evidence.get("insufficient_fields") or []
    if missing:
        st.caption("Insufficient: " + ", ".join(missing))
