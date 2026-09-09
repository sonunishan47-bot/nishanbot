"""Application configuration. Literal defaults are assigned first so imports never fail."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Phase 3 required defaults (always defined)
# ---------------------------------------------------------------------------
LLM_PROVIDER = "ollama"
LLM_TEMPERATURE = 0.2
MAX_RESPONSE_TOKENS = 1024
CHAT_HISTORY_TURNS = 6

CACHE_TTL_SECONDS = 30
ERROR_CACHE_TTL_SECONDS = 60
STABLECOINS_USD_PEG = ("USDT", "FDUSD", "USDC", "DAI", "BUSD")
DEFAULT_OVERVIEW_COINS = 6
HTTP_TIMEOUT = 8

HISTORY_CACHE_TTL_SECONDS = 300
NEWS_CACHE_TTL_SECONDS = 300
MACRO_CACHE_TTL_SECONDS = 300
ONION_CACHE_TTL_SECONDS = 600
ONION_HTTP_TIMEOUT = 15
TOR_ENABLED = True
TOR_PROXY = "socks5h://127.0.0.1:9050"
NEWS_API_KEY = ""
CRYPTOPANIC_API_KEY = ""
CRYPTOPANIC_KEY = ""
FRED_API_KEY = ""
FEAR_GREED_CACHE_TTL_SECONDS = 600
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

NEWS_RSS_FEEDS = (
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "BBC Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
)

MACRO_RSS_FEEDS = (
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
    {"name": "ECB", "url": "https://www.ecb.europa.eu/rss/press.html"},
)

# Read-only OSINT bulletins fetched via TOR_PROXY (socks5h). Add .onion RSS/HTML URLs here.
ONION_SOURCES = (
    {
        "name": "Ransomware.live",
        "url": "https://www.ransomware.live/rss.xml",
        "kind": "rss",
        "category": "ransomware",
    },
    {
        "name": "The Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "kind": "rss",
        "category": "threat_group",
    },
    {
        "name": "CISA Advisories",
        "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "kind": "rss",
        "category": "breach",
    },
)
COINGECKO_MARKETS_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd"
    "&order=market_cap_desc"
    "&per_page=25"
    "&page=1"
    "&sparkline=true"
    "&price_change_percentage=1h,24h,7d,30d"
)
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
FIAT_RATES_URL = "https://open.er-api.com/v6/latest/USD"

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"
OLLAMA_API_MODE = "generate"
OLLAMA_NUM_CTX = 4096

GROQ_API_KEY = ""
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

OPENAI_API_KEY = ""
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Optional .env overlays (do not remove the literals above)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass


def _overlay_int(name: str, current: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return current
    try:
        return int(raw)
    except (TypeError, ValueError):
        return current


def _overlay_float(name: str, current: float) -> float:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return current
    try:
        return float(raw)
    except (TypeError, ValueError):
        return current


def _overlay_bool(name: str, current: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return current
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _overlay_str(name: str, current: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return current
    stripped = str(raw).strip()
    return stripped if stripped != "" else current


LLM_PROVIDER = _overlay_str("LLM_PROVIDER", LLM_PROVIDER)
LLM_TEMPERATURE = _overlay_float("LLM_TEMPERATURE", LLM_TEMPERATURE)
MAX_RESPONSE_TOKENS = _overlay_int("MAX_RESPONSE_TOKENS", MAX_RESPONSE_TOKENS)
CHAT_HISTORY_TURNS = _overlay_int("CHAT_HISTORY_TURNS", CHAT_HISTORY_TURNS)
ERROR_CACHE_TTL_SECONDS = _overlay_int("ERROR_CACHE_TTL_SECONDS", ERROR_CACHE_TTL_SECONDS)
CACHE_TTL_SECONDS = _overlay_int("CACHE_TTL_SECONDS", CACHE_TTL_SECONDS)

OLLAMA_GENERATE_URL = _overlay_str("OLLAMA_GENERATE_URL", OLLAMA_GENERATE_URL)
OLLAMA_CHAT_URL = _overlay_str("OLLAMA_CHAT_URL", OLLAMA_CHAT_URL)
OLLAMA_MODEL = _overlay_str("OLLAMA_MODEL", OLLAMA_MODEL)
OLLAMA_API_MODE = _overlay_str("OLLAMA_API_MODE", OLLAMA_API_MODE)
OLLAMA_NUM_CTX = _overlay_int("OLLAMA_NUM_CTX", OLLAMA_NUM_CTX)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", GROQ_API_KEY) or ""
GROQ_BASE_URL = _overlay_str("GROQ_BASE_URL", GROQ_BASE_URL)
GROQ_MODEL = _overlay_str("GROQ_MODEL", GROQ_MODEL)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY) or ""
OPENAI_BASE_URL = _overlay_str("OPENAI_BASE_URL", OPENAI_BASE_URL)
OPENAI_MODEL = _overlay_str("OPENAI_MODEL", OPENAI_MODEL)

CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "") or os.getenv("CRYPTOPANIC_KEY", CRYPTOPANIC_API_KEY) or ""
CRYPTOPANIC_KEY = CRYPTOPANIC_API_KEY
NEWS_API_KEY = os.getenv("NEWS_API_KEY", NEWS_API_KEY) or ""
FRED_API_KEY = os.getenv("FRED_API_KEY", FRED_API_KEY) or ""
TOR_PROXY = _overlay_str("TOR_PROXY", TOR_PROXY)
TOR_ENABLED = _overlay_bool("TOR_ENABLED", TOR_ENABLED)
NEWS_CACHE_TTL_SECONDS = _overlay_int("NEWS_CACHE_TTL_SECONDS", NEWS_CACHE_TTL_SECONDS)
MACRO_CACHE_TTL_SECONDS = _overlay_int("MACRO_CACHE_TTL_SECONDS", MACRO_CACHE_TTL_SECONDS)
ONION_CACHE_TTL_SECONDS = _overlay_int("ONION_CACHE_TTL_SECONDS", ONION_CACHE_TTL_SECONDS)
ONION_HTTP_TIMEOUT = _overlay_int("ONION_HTTP_TIMEOUT", ONION_HTTP_TIMEOUT)
FEAR_GREED_CACHE_TTL_SECONDS = _overlay_int("FEAR_GREED_CACHE_TTL_SECONDS", FEAR_GREED_CACHE_TTL_SECONDS)
