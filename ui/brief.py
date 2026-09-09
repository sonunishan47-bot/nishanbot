import streamlit as st

from ui.setup import fmt_pct, fmt_usd, init_session, load_app_data


def _load_osint() -> tuple[dict, dict, dict, dict]:
    news: dict = {"status": "unavailable", "items": [], "digest": "", "errors": []}
    macro: dict = {"status": "not_configured", "items": [], "digest": "", "errors": []}
    onion: dict = {"status": "unavailable", "items": [], "digest": "", "errors": []}
    fng: dict = {"status": "unavailable"}
    try:
        from data.news import fetch_fear_greed, fetch_news

        news = fetch_news(query=None, limit=10)
        fng = fetch_fear_greed()
    except Exception as exc:
        news["errors"] = [str(exc)]
    try:
        from data.macro import fetch_macro

        macro = fetch_macro()
    except Exception as exc:
        macro["errors"] = [str(exc)]
    try:
        from data.onion import fetch_onion_intel

        onion = fetch_onion_intel()
    except Exception as exc:
        onion["errors"] = [str(exc)]
    return news, macro, onion, fng


def _headlines(items: list) -> None:
    if not items:
        st.info("source: unavailable")
        return
    for item in items:
        clock = (item.get("published_at") or "n/a")[:16]
        src = item.get("source") or "unknown"
        headline = item.get("headline") or "(untitled)"
        sent = item.get("sentiment") or item.get("category") or ""
        url = item.get("url") or item.get("onion_url") or ""
        extra = f" [{sent}]" if sent else ""
        line = f"**[{src} {clock}]** {headline}{extra}"
        if url:
            st.markdown(f"{line} — {url}")
        else:
            st.markdown(line)


def render_brief() -> None:
    init_session()
    st.title("Market Brief")
    st.caption("Market snapshot + news + macro + threat intel. Failed sources show unavailable — nothing is invented.")

    try:
        fiat_rates, coins, global_market = load_app_data()
    except Exception:
        fiat_rates, coins, global_market = {}, [], {}

    news, macro, onion, fng = _load_osint()

    st.subheader("Market overview")
    btc = next((c for c in coins if c.get("symbol") == "BTC"), None)
    eth = next((c for c in coins if c.get("symbol") == "ETH"), None)
    cols = st.columns(5)
    cols[0].metric("BTC", fmt_usd(btc["price_usd"]) if btc else "—", fmt_pct(btc["change_24h_pct"] if btc else None))
    cols[1].metric("ETH", fmt_usd(eth["price_usd"]) if eth else "—", fmt_pct(eth["change_24h_pct"] if eth else None))
    btc_d = global_market.get("btc_dominance_pct")
    cols[2].metric("BTC.D", f"{float(btc_d):.2f}%" if btc_d is not None else "—")
    mcap = global_market.get("total_market_cap_usd")
    cols[3].metric("Global mcap", fmt_usd(mcap, 0) if mcap is not None else "—")
    if fng.get("status") == "ok":
        cols[4].metric("Fear & Greed", str(fng.get("value") or "—"), str(fng.get("classification") or ""))
    else:
        cols[4].metric("Fear & Greed", "unavailable")
    if not coins and not global_market:
        st.info("Market snapshot: unavailable this cycle.")

    st.subheader("Top movers (24h)")
    ranked = sorted(coins, key=lambda c: abs(float(c.get("change_24h_pct") or 0.0)), reverse=True)[:8]
    if ranked:
        for coin in ranked:
            st.write(
                f"**{coin.get('symbol')}** {fmt_usd(coin.get('price_usd'))} "
                f"({fmt_pct(coin.get('change_24h_pct'))})"
            )
    else:
        st.info("Top movers: unavailable")

    st.subheader("Top news")
    st.caption(f"Status: {news.get('news') or news.get('status')}")
    _headlines(news.get("items") or [])
    for err in news.get("errors") or []:
        st.caption(f"source: unavailable — {err}")

    st.subheader("Macro")
    st.caption(f"Status: {macro.get('macro') or macro.get('status')}")
    _headlines(macro.get("items") or [])
    for err in macro.get("errors") or []:
        st.caption(f"source: unavailable — {err}")

    st.subheader("Threat intel (Tor)")
    onion_status = onion.get("onion") or onion.get("status")
    st.caption(f"Status: {onion_status}")
    if onion_status == "tor_down":
        st.warning("Tor proxy unreachable (tor_down). App is fine; onion intel is missing.")
    elif onion_status == "not_enabled":
        st.info("Tor layer not enabled (TOR_ENABLED=false).")
    elif onion_status != "ok":
        st.info("Onion intel unavailable. Data is missing — nothing invented.")
    _headlines(onion.get("items") or [])
    for err in onion.get("errors") or []:
        st.caption(f"source: unavailable — {err}")
