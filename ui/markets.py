import pandas as pd
import streamlit as st

from ui.setup import (
    CACHE_TTL_SECONDS,
    POPULAR_FIATS,
    STABLECOINS_USD_PEG,
    fmt_pct,
    fmt_usd,
    init_session,
    load_app_data,
)


def render_markets() -> None:
    init_session()
    st.title("📊 Markets")
    st.caption(
        f"Dashboard RSI/SMA/EMA use 7d hourly-sample TA (approximate). "
        f"Cache {CACHE_TTL_SECONDS}s for LAN/mobile."
    )

    fiat_rates, coins, global_market = load_app_data()
    if not fiat_rates:
        st.warning("Fiat rates unavailable this cycle.")
    if not coins:
        st.warning("CoinGecko markets unavailable this cycle.")

    with st.sidebar:
        st.header("Live FX (1 USD)")
        if fiat_rates:
            st.success(f"{len(fiat_rates)} currencies loaded")
            for code in POPULAR_FIATS:
                rate = fiat_rates.get(code)
                st.write(f"**{code}:** n/a" if rate is None else f"**{code}:** {rate:.4f}")
            with st.expander("All global fiat rates"):
                st.dataframe(
                    pd.DataFrame(
                        [{"Currency": k, "Rate per 1 USD": v} for k, v in sorted(fiat_rates.items())]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
        else:
            st.error("Fiat book empty — waiting for API.")

        st.header("USD stablecoins")
        st.write("1 " + " = 1 ".join(STABLECOINS_USD_PEG) + " = 1 USD")
        if fiat_rates.get("INR") is not None:
            st.write(f"1 USDT ≈ {fiat_rates['INR']:.4f} INR (live)")

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    btc = next((c for c in coins if c["symbol"] == "BTC"), None)
    eth = next((c for c in coins if c["symbol"] == "ETH"), None)
    inr = fiat_rates.get("INR")
    eur = fiat_rates.get("EUR")
    btc_dom = global_market.get("btc_dominance_pct")
    col_a.metric("BTC", fmt_usd(btc["price_usd"]) if btc else "—", fmt_pct(btc["change_24h_pct"] if btc else None))
    col_b.metric("ETH", fmt_usd(eth["price_usd"]) if eth else "—", fmt_pct(eth["change_24h_pct"] if eth else None))
    col_c.metric("USD → INR", f"{inr:.4f}" if inr is not None else "—")
    col_d.metric("USD → EUR", f"{eur:.4f}" if eur is not None else "—")
    col_e.metric("BTC.D", f"{float(btc_dom):.2f}%" if btc_dom is not None else "—")

    st.subheader("Live markets + technical signals")
    st.caption("Chat asset questions use CoinGecko history (1h/1d bars). This table is sparkline TA.")
    if global_market.get("total_market_cap_usd") is not None:
        st.caption(
            f"Global: mcap {fmt_usd(global_market.get('total_market_cap_usd'), 0)} · "
            f"24h vol {fmt_usd(global_market.get('total_volume_usd'), 0)} · "
            f"BTC.D {fmt_pct(global_market.get('btc_dominance_pct'))}"
        )
    if coins:
        rows = []
        for coin in coins:
            ta = coin["ta"]
            rows.append(
                {
                    "Coin": coin["name"],
                    "Symbol": coin["symbol"],
                    "Price (USD)": fmt_usd(coin["price_usd"]),
                    "1h": fmt_pct(coin["change_1h_pct"]),
                    "24h": fmt_pct(coin["change_24h_pct"]),
                    "7d": fmt_pct(coin["change_7d_pct"]),
                    "30d": fmt_pct(coin.get("change_30d_pct")),
                    "Volume 24h": fmt_usd(coin["volume_24h_usd"], 0),
                    "Market Cap": fmt_usd(coin["market_cap_usd"], 0),
                    "ATH Δ": fmt_pct(coin["ath_change_pct"]),
                    "ATL Δ": fmt_pct(coin["atl_change_pct"]),
                    "RSI(14)*": f"{ta['rsi_14']:.1f}" if ta["rsi_14"] is not None else "n/a",
                    "RSI": ta["rsi_state"],
                    "Trend": ta["trend"],
                    "Vol": ta["volatility"],
                    "Volume": coin["volume_signal"],
                    "Insight": coin["insight"],
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("*RSI(14) on the dashboard is approximate 7d sparkline samples, not 14 daily/hourly bars.")
    else:
        st.info("No crypto rows yet. The table will fill on the next successful CoinGecko response.")
