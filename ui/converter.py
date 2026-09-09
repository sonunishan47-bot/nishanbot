import streamlit as st

from analytics.converter import convert
from ui.setup import POPULAR_FIATS, STABLECOINS_USD_PEG, init_session, load_app_data


def _from_options(fiat_rates: dict[str, float], coins: list) -> list[str]:
    symbols = [str(c.get("symbol") or "").upper() for c in coins if c.get("symbol")]
    fiats = ["USD"] + [c for c in POPULAR_FIATS if c in fiat_rates]
    extra = sorted(k for k in fiat_rates if k not in fiats and k != "USD")
    seen: list[str] = []
    for code in list(STABLECOINS_USD_PEG) + symbols + fiats + extra:
        if code and code not in seen:
            seen.append(code)
    return seen


def _to_options(fiat_rates: dict[str, float]) -> list[str]:
    ordered = ["USD"] + [c for c in POPULAR_FIATS if c == "USD" or c in fiat_rates]
    rest = sorted(k for k in fiat_rates if k not in ordered)
    return ordered + rest


def render_converter() -> None:
    init_session()
    st.title("💱 Converter")
    st.caption("Python-verified conversion. No LLM. Same convert() used by chat.")

    fiat_rates, coins, _global_market = load_app_data()
    from_codes = _from_options(fiat_rates, coins)
    to_codes = _to_options(fiat_rates)
    if not to_codes:
        to_codes = ["USD"]

    col_amt, col_from, col_to = st.columns([1.2, 1, 1])
    with col_amt:
        amount = st.number_input("Amount", min_value=0.0, value=1.0, step=1.0, format="%.8f")
    with col_from:
        default_from = "USDT" if "USDT" in from_codes else (from_codes[0] if from_codes else "USD")
        base = st.selectbox("From (fiat or coin)", from_codes, index=from_codes.index(default_from) if default_from in from_codes else 0)
    with col_to:
        default_to = "INR" if "INR" in to_codes else to_codes[0]
        target = st.selectbox("To (fiat)", to_codes, index=to_codes.index(default_to) if default_to in to_codes else 0)

    out = convert(amount, base, target, fiat_rates=fiat_rates, coins=coins)
    status = out.get("status")
    if status == "ok":
        st.success(f"{out['amount']:g} {out['base']} = {out['result']:,.8f} {out['target']}")
    elif status == "fx_missing":
        st.error("Target or base FX is missing. No fake rate was used.")
    else:
        st.error("Price missing. No conversion was calculated.")

    st.subheader("Breakdown (python-verified)")
    base_usd = out.get("base_usd_price")
    fx = out.get("fx_rate_used")
    result = out.get("result")
    st.write(
        f"**base_usd_price × fx_rate = result:** "
        f"{base_usd} × {fx} × {out.get('amount')} → **{result}**"
        if result is not None
        else f"**base_usd_price:** {base_usd} · **fx_rate:** {fx} · **result:** n/a"
    )
    st.write(f"**Timestamp (UTC):** {out.get('timestamp')}")
    st.write(f"**Source:** {out.get('source')} · **Status:** {status}")
    if out.get("audit"):
        st.code(out["audit"], language=None)
    with st.expander("Raw convert() payload"):
        st.json(out)
