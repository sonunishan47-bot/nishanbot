"""Data package UI helpers — Chat page (behavior identical to pre-Phase-6 chat)."""

import streamlit as st

from ai.context import build_system_prompt, trim_llm_context
from ai.intent import INTENT_FX_CONVERT, classify_intent
from ai.providers.factory import get_provider
from ui.setup import CACHE_TTL_SECONDS, CHAT_HISTORY_TURNS, init_session, load_app_data


def _history_for_provider(conversion_only: bool) -> list[dict[str, str]] | None:
    if conversion_only or CHAT_HISTORY_TURNS <= 0:
        return None
    prior = st.session_state.messages[:-1]
    if not prior:
        return None
    trimmed = prior[-CHAT_HISTORY_TURNS:]
    history: list[dict[str, str]] = []
    for msg in trimmed:
        role = str(msg.get("role") or "")
        if role not in ("user", "assistant"):
            continue
        history.append({"role": role, "content": str(msg.get("content") or "")})
    return history or None


def render_chat() -> None:
    init_session()
    st.title("Research assistant")
    st.caption(
        "Open knowledge: crypto, trading, forensics, cybersecurity, OSINT, Dark Web threat intel. "
        f"Live numbers only from verified data. Cache {CACHE_TTL_SECONDS}s."
    )

    fiat_rates, coins, global_market = load_app_data()
    if not fiat_rates:
        st.warning("Fiat rates unavailable this cycle.")
    if not coins:
        st.warning("CoinGecko markets unavailable this cycle.")

    st.subheader("Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask: USDT to INR, BTC in SAR, RSI outlook, volume spikes...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        context = trim_llm_context(user_input, fiat_rates, coins, global_market=global_market)
        intent = context.get("intent") or classify_intent(user_input, coins, fiat_rates)
        system_prompt = build_system_prompt(context)

        with st.chat_message("assistant"):
            with st.spinner("Quant desk: live rates + TA..."):
                try:
                    provider = get_provider()
                    bot_reply = provider.generate(
                        system_prompt,
                        user_input,
                        history=_history_for_provider(intent == INTENT_FX_CONVERT),
                    )
                except Exception as exc:
                    bot_reply = f"Could not reach the LLM provider: {exc}"
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
