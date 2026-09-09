"""News providers: keyless RSS + optional CryptoPanic / NewsAPI. Never raise."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from data.rss_util import clock_label, http_get, parse_rss_bytes, within_hours

log = logging.getLogger(__name__)

_POS = (
    "surge", "rally", "gain", "gains", "bull", "bullish", "record", "approval",
    "approved", "partnership", "inflow", "inflows", "adopt", "growth", "soar",
)
_NEG = (
    "hack", "hacked", "crash", "lawsuit", "ban", "exploit", "dump", "plunge",
    "fraud", "sec charge", "outflow", "outflows", "collapse", "stolen", "breach",
)


def headline_sentiment(text: str) -> str:
    blob = f" {(text or '').lower()} "
    pos = sum(1 for w in _POS if w in blob)
    neg = sum(1 for w in _NEG if w in blob)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _attach_sentiment(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    out["sentiment"] = headline_sentiment(str(out.get("headline") or ""))
    out["status"] = "ok"
    return out


def _timeout() -> int:
    try:
        from config import HTTP_TIMEOUT

        return max(int(HTTP_TIMEOUT), 10)
    except Exception:
        return 10


def _feeds() -> tuple:
    try:
        from config import NEWS_RSS_FEEDS

        return tuple(NEWS_RSS_FEEDS)
    except Exception:
        return ()


def _cryptopanic_key() -> str:
    try:
        import config as cfg

        return str(getattr(cfg, "CRYPTOPANIC_API_KEY", None) or getattr(cfg, "CRYPTOPANIC_KEY", "") or "").strip()
    except Exception:
        return ""


def _newsapi_key() -> str:
    try:
        from config import NEWS_API_KEY

        return str(NEWS_API_KEY or "").strip()
    except Exception:
        return ""


def _fetch_one_rss(feed: dict[str, str]) -> tuple[list[dict[str, Any]], Optional[str]]:
    name = feed.get("name") or "rss"
    url = feed.get("url") or ""
    try:
        raw = http_get(url, timeout=_timeout())
        items = [_attach_sentiment(it) for it in parse_rss_bytes(raw, name)]
        if not items:
            return [], f"{name}: empty feed"
        return items, None
    except Exception as exc:
        log.warning("News RSS failed: %s (%s)", name, exc)
        return [], f"{name}: {exc}"


def _fetch_cryptopanic() -> tuple[list[dict[str, Any]], Optional[str]]:
    key = _cryptopanic_key()
    if not key:
        return [], None
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={key}&public=true"
    try:
        import requests

        res = requests.get(url, timeout=_timeout())
        res.raise_for_status()
        items = []
        for row in (res.json() or {}).get("results") or []:
            title = str(row.get("title") or "")
            source = ((row.get("source") or {}).get("title")) or "CryptoPanic"
            items.append(
                _attach_sentiment(
                    {
                        "headline": title or "(untitled)",
                        "source": source,
                        "url": str(row.get("url") or row.get("original_url") or ""),
                        "published_at": row.get("published_at") or row.get("created_at"),
                        "summary": "",
                    }
                )
            )
        if not items:
            return [], "CryptoPanic: empty"
        return items, None
    except Exception as exc:
        log.warning("CryptoPanic failed: %s", exc)
        return [], f"CryptoPanic: {exc}"


def _fetch_newsapi(query: Optional[str]) -> tuple[list[dict[str, Any]], Optional[str]]:
    key = _newsapi_key()
    if not key:
        return [], None
    q = (query or "cryptocurrency").strip() or "cryptocurrency"
    url = "https://newsapi.org/v2/everything"
    try:
        import requests

        res = requests.get(
            url,
            params={"q": q, "pageSize": 10, "sortBy": "publishedAt", "language": "en", "apiKey": key},
            timeout=_timeout(),
        )
        res.raise_for_status()
        items = []
        for row in (res.json() or {}).get("articles") or []:
            items.append(
                _attach_sentiment(
                    {
                        "headline": str(row.get("title") or "(untitled)"),
                        "source": ((row.get("source") or {}).get("name")) or "NewsAPI",
                        "url": str(row.get("url") or ""),
                        "published_at": row.get("publishedAt"),
                        "summary": str(row.get("description") or "")[:400],
                    }
                )
            )
        return items, None if items else "NewsAPI: empty"
    except Exception as exc:
        log.warning("NewsAPI failed: %s", exc)
        return [], f"NewsAPI: {exc}"


def format_verified_news_block(payload: dict[str, Any]) -> str:
    status = payload.get("status") or "unavailable"
    items = payload.get("items") or []
    if status != "ok" or not items:
        return (
            f"News (verified, fetched): status={status}. "
            "Data is missing. Do not invent headlines."
        )
    lines = ["News (verified, fetched):"]
    for i, item in enumerate(items, 1):
        sent = item.get("sentiment") or "neutral"
        lines.append(
            f"{i}. {item.get('headline')} — {item.get('source')} — "
            f"{clock_label(item.get('published_at'))} [{sent}] {item.get('url') or ''}".rstrip()
        )
    for err in payload.get("errors") or []:
        lines.append(f"- source: unavailable ({err})")
    return "\n".join(lines)


def _collect(query: Optional[str], limit: int) -> dict[str, Any]:
    errors: list[str] = []
    items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_fetch_one_rss, feed) for feed in _feeds()]
        futures.append(pool.submit(_fetch_cryptopanic))
        futures.append(pool.submit(_fetch_newsapi, query))
        for fut in as_completed(futures):
            try:
                batch, err = fut.result()
            except Exception as exc:
                errors.append(str(exc))
                continue
            if err:
                errors.append(err)
            items.extend(batch)
    q = (query or "").strip().lower()
    if q:
        tokens = [t for t in q.replace(",", " ").split() if len(t) > 1]
        if tokens:
            items = [it for it in items if any(t in (it.get("headline") or "").lower() for t in tokens)]
    recent = [it for it in items if within_hours(it.get("published_at"), 48.0)]
    recent.sort(key=lambda it: it.get("published_at") or "", reverse=True)
    recent = recent[: max(1, int(limit))]
    if not recent:
        return {
            "status": "unavailable",
            "news": "unavailable",
            "items": [],
            "errors": errors or ["no headlines"],
            "digest": format_verified_news_block({"status": "unavailable", "items": [], "errors": errors}),
        }
    payload = {
        "status": "ok",
        "news": "ok",
        "items": recent,
        "errors": errors,
    }
    payload["digest"] = format_verified_news_block(payload)
    return payload


def fetch_news(query: Optional[str] = None, limit: int = 10) -> dict[str, Any]:
    """Evidence pack. Never raises. Cache 300s on success only."""
    try:
        import streamlit as st
        from config import ERROR_CACHE_TTL_SECONDS, NEWS_CACHE_TTL_SECONDS

        q = query or ""
        lim = int(limit)

        @st.cache_data(ttl=NEWS_CACHE_TTL_SECONDS, show_spinner=False)
        def _ok(cache_q: str, cache_lim: int) -> dict[str, Any]:
            payload = _collect(cache_q or None, cache_lim)
            if payload.get("status") != "ok" or not payload.get("items"):
                raise RuntimeError("news_incomplete")
            return payload

        @st.cache_data(ttl=ERROR_CACHE_TTL_SECONDS, show_spinner=False)
        def _retry(cache_q: str, cache_lim: int) -> dict[str, Any]:
            try:
                return _collect(cache_q or None, cache_lim)
            except Exception as exc:
                return {
                    "status": "unavailable",
                    "news": "unavailable",
                    "items": [],
                    "errors": [str(exc)],
                    "digest": format_verified_news_block({"status": "unavailable", "items": []}),
                }

        try:
            return _ok(q, lim)
        except Exception:
            _ok.clear()
            return _retry(q, lim)
    except Exception:
        try:
            return _collect(query, limit)
        except Exception as exc:
            log.warning("fetch_news failed: %s", exc)
            return {
                "status": "unavailable",
                "news": "unavailable",
                "items": [],
                "errors": [str(exc)],
                "digest": format_verified_news_block({"status": "unavailable", "items": []}),
            }


def load_news() -> dict[str, Any]:
    return fetch_news(limit=10)


def _pull_fear_greed() -> dict[str, Any]:
    import requests
    from config import FEAR_GREED_URL

    res = requests.get(FEAR_GREED_URL, timeout=_timeout())
    res.raise_for_status()
    row = ((res.json() or {}).get("data") or [None])[0]
    if not isinstance(row, dict):
        raise RuntimeError("empty_fng")
    return {
        "status": "ok",
        "value": row.get("value"),
        "classification": row.get("value_classification"),
        "timestamp": row.get("timestamp"),
        "source": "alternative.me",
    }


def fetch_fear_greed() -> dict[str, Any]:
    """alternative.me Fear & Greed, keyless. Cached 600s. Never raises."""
    unavailable = {"status": "unavailable", "source": "alternative.me"}
    try:
        import streamlit as st
        from config import FEAR_GREED_CACHE_TTL_SECONDS

        @st.cache_data(ttl=FEAR_GREED_CACHE_TTL_SECONDS, show_spinner=False)
        def _ok() -> dict[str, Any]:
            return _pull_fear_greed()

        try:
            return _ok()
        except Exception:
            _ok.clear()
            try:
                return _pull_fear_greed()
            except Exception:
                return unavailable
    except Exception:
        try:
            return _pull_fear_greed()
        except Exception as exc:
            log.warning("Fear & Greed unavailable: %s", exc)
            return {**unavailable, "errors": [str(exc)]}
