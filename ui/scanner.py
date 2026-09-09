import streamlit as st

from ui.setup import init_session


def render_scanner() -> None:
    init_session()
    st.title("🔭 Scanner")
    st.info("coming in Phase 8")
