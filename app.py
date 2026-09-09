import streamlit as st

# Entrypoint: navigation + shared session only.

from ui.asset import render_asset
from ui.brief import render_brief
from ui.chat import render_chat
from ui.converter import render_converter
from ui.markets import render_markets
from ui.scanner import render_scanner
from ui.setup import init_session

st.set_page_config(
    page_title="Crypto & Fiat Intelligence Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

pg = st.navigation(
    {
        "Assistant": [
            st.Page(render_chat, title="Chat", icon="💬", default=True, url_path="chat"),
        ],
        "Markets": [
            st.Page(render_markets, title="Markets", icon="📊", url_path="markets"),
            st.Page(render_converter, title="Converter", icon="💱", url_path="converter"),
            st.Page(render_asset, title="Asset", icon="📈", url_path="asset"),
        ],
        "Later": [
            st.Page(render_scanner, title="Scanner", icon="🔭", url_path="scanner"),
            st.Page(render_brief, title="Brief", icon="🗞️", url_path="brief"),
        ],
    }
)
pg.run()
