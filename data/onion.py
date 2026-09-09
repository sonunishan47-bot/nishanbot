"""Tor SOCKS OSINT reader. Read-only public bulletins. Never crash or hang."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional
from urllib.parse import urlparse

from data.rss_util import clock_label, http_get, parse_html_headlines, parse_rss_bytes, within_hours

log = logging.getLogger(__name__)

_CATEGORIES = ("breach", "ransomware", "scam", "market", "threat_group")


def _proxy() -> str:
    try:
        from config import TOR_PROXY

        return str(TOR_PROXY or "socks5h://127.0.0.1:9050").strip()
    except Exception:
        return "socks5h://127.0.0.1:9050"


def _timeout() -> int:
    try:
        from config import ONION_HTTP_TIMEOUT

        return int(ONION_HTTP_TIMEOUT)
    except Exception:
        return 15


def _enabled() -> bool:
    try:
        from config import TOR_ENABLED

        return bool(TOR_ENABLED)
    except Exception:
        return True


def _sources() -> tuple:
    try:
        from config import ONION_SOURCES

        return tuple(ONION_SOURCES)
    except Exception:
        return ()


def _proxies() -> dict[str, str]:
    proxy = _proxy()
    return {"http": proxy, "https": proxy}


def _classify(headline: str, source: str, default: str = "threat_group") -> str:
    text = f"{headline} {source}".lower()
    if any(w in text for w in ("ransom", "lockbit", "alphv", "cl0p")):
        return "ransomware"
    if any(w in text for w in ("breach", "leak", "stolen data", "infosteal")):
        return "breach"
    if any(w in text for w in ("scam", "phish", "rug pull", "ponzi")):
        return "scam"
    if any(w in text for w in ("apt", "threat group", "actor", "gang")):
        return "threat_group"
    if any(w in text for w in ("btc", "crypto", "market", "exchange")):
        return "market"
    return default if default in _CATEGORIES else "threat_group"


def tor_proxy_up() -> tuple[bool, str]:
    try:
        import socks  # noqa: F401
    except ImportError:
        return False, "PySocks is not installed"
    parsed = urlparse(_proxy())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9050
    try:
        import socket

        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
        return True, "ok"
    except Exception as exc:
        log.warning("Tor SOCKS not reachable: %s", exc)
        return False, str(exc)


def _pack(status: str, items: list[dict[str, Any]], errors: Optional[list[str]] = None) -> dict[str, Any]:
    errors = errors or []
    if status == "ok" and items:
        lines = ["DARK WEB / THREAT INTEL (verified, via Tor):"]
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. {item.get('headline')} — {item.get('source')} — "
                f"{clock_label(item.get('published_at'))} [{item.get('category')}] "
                f"{item.get('onion_url') or ''}".rstrip()
            )
        digest = "\n".join(lines)
    elif status == "tor_down":
        digest = "DARK WEB / THREAT INTEL: status=tor_down. Data is missing. Do not invent headlines."
    elif status == "not_enabled":
        digest = "DARK WEB / THREAT INTEL: status=not_enabled."
    else:
        digest = "DARK WEB / THREAT INTEL: status=unavailable. Data is missing. Do not invent headlines."
    if errors:
        digest += "\n" + "\n".join(f"- source: unavailable ({e})" for e in errors)
    return {
        "status": status,
        "onion": status,
        "items": items,
        "errors": errors,
        "digest": digest,
    }


def _fetch_source(src: dict[str, str]) -> tuple[list[dict[str, Any]], Optional[str]]:
    name = src.get("name") or "onion"
    url = src.get("url") or ""
    kind = (src.get("kind") or "rss").lower()
    default_cat = src.get("category") or "threat_group"
    try:
        raw = http_get(url, timeout=_timeout(), proxies=_proxies())
        if kind == "html":
            raw_items = parse_html_headlines(raw, name, url, network="tor")
        else:
            raw_items = parse_rss_bytes(raw, name, network="tor")
            if not raw_items:
                raw_items = parse_html_headlines(raw, name, url, network="tor")
        items = []
        for it in raw_items:
            headline = it.get("headline") or ""
            items.append(
                {
                    "source": name,
                    "onion_url": it.get("url") or url,
                    "headline": headline,
                    "published_at": it.get("published_at"),
                    "category": _classify(headline, name, default_cat),
                    "network": "tor",
                    "status": "ok",
                }
            )
        if not items:
            return [], f"{name}: empty"
        return items, None
    except Exception as exc:
        log.warning("Onion source failed: %s (%s)", name, exc)
        return [], f"{name}: {exc}"


def fetch_onion_intel(limit: int = 12) -> dict[str, Any]:
    """Read-only OSINT. status: ok | tor_down | unavailable | not_enabled. Never raises."""
    try:
        if not _enabled():
            return _pack("not_enabled", [])
        up, reason = tor_proxy_up()
        if not up:
            return _pack("tor_down", [], [f"Tor proxy unreachable ({reason})"])
        sources = _sources()
        if not sources:
            return _pack("unavailable", [], ["no ONION_SOURCES configured"])
        errors: list[str] = []
        items: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_fetch_source, src) for src in sources]
            for fut in as_completed(futures):
                try:
                    batch, err = fut.result()
                except Exception as exc:
                    errors.append(str(exc))
                    continue
                if err:
                    errors.append(err)
                items.extend(batch)
        recent = [it for it in items if within_hours(it.get("published_at"), 24.0)]
        recent.sort(key=lambda it: it.get("published_at") or "", reverse=True)
        recent = recent[: max(1, int(limit))]
        if not recent:
            return _pack("unavailable", [], errors or ["no headlines"])
        return _pack("ok", recent, errors)
    except Exception as exc:
        log.warning("fetch_onion_intel failed: %s", exc)
        return _pack("unavailable", [], [str(exc)])


def load_onion() -> dict[str, Any]:
    try:
        import streamlit as st
        from config import ERROR_CACHE_TTL_SECONDS, ONION_CACHE_TTL_SECONDS

        @st.cache_data(ttl=ONION_CACHE_TTL_SECONDS, show_spinner=False)
        def _ok() -> dict[str, Any]:
            payload = fetch_onion_intel()
            if payload.get("status") != "ok" or not payload.get("items"):
                raise RuntimeError("onion_incomplete")
            return payload

        @st.cache_data(ttl=ERROR_CACHE_TTL_SECONDS, show_spinner=False)
        def _retry() -> dict[str, Any]:
            return fetch_onion_intel()

        try:
            return _ok()
        except Exception:
            _ok.clear()
            return _retry()
    except Exception:
        return fetch_onion_intel()
