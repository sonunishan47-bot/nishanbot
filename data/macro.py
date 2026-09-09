"""Macro / policy RSS plus optional FRED snapshot. Never cache empty success."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from data.rss_util import evidence_item, format_digest, http_get, parse_rss_bytes, within_hours

log = logging.getLogger(__name__)


def _feeds() -> tuple:
    try:
        from config import MACRO_RSS_FEEDS

        return tuple(MACRO_RSS_FEEDS)
    except Exception:
        return ()


def _timeout() -> int:
    try:
        from config import HTTP_TIMEOUT

        return max(int(HTTP_TIMEOUT), 10)
    except Exception:
        return 10


def _fred_key() -> str:
    try:
        from config import FRED_API_KEY

        return str(FRED_API_KEY or "").strip()
    except Exception:
        return ""


def _fetch_one_rss(feed: dict[str, str]) -> tuple[str, list[dict[str, Any]], Optional[str]]:
    name = feed.get("name") or "macro"
    url = feed.get("url") or ""
    try:
        raw = http_get(url, timeout=_timeout())
        items = parse_rss_bytes(raw, name)
        if not items:
            return name, [], f"{name}: empty feed"
        return name, items, None
    except Exception as exc:
        log.warning("Macro RSS failed: %s (%s)", name, exc)
        return name, [], f"{name}: {exc}"


def _fetch_fred() -> tuple[str, list[dict[str, Any]], Optional[str]]:
    key = _fred_key()
    if not key:
        return "FRED", [], None
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=CPIAUCSL&api_key={key}&file_type=json&sort_order=desc&limit=1"
    )
    try:
        import requests

        res = requests.get(url, timeout=_timeout())
        res.raise_for_status()
        rows = (res.json() or {}).get("observations") or []
        if not rows:
            return "FRED", [], "FRED: empty"
        last = rows[0]
        value = last.get("value")
        date = last.get("date")
        item = evidence_item(
            headline=f"CPIAUCSL (CPI) last observation: {value} on {date}",
            source="FRED",
            url="https://fred.stlouisfed.org/series/CPIAUCSL",
            published_at=f"{date}T00:00:00+00:00" if date else None,
            summary="python-verified FRED observation; not a forecast",
        )
        return "FRED", [item], None
    except Exception as exc:
        log.warning("FRED failed: %s", exc)
        return "FRED", [], f"FRED: {exc}"


def _collect_macro(limit: int = 12) -> dict[str, Any]:
    hours = 72.0
    errors: list[str] = []
    items: list[dict[str, Any]] = []
    fred_status = "not_configured" if not _fred_key() else "ok"
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(_fetch_one_rss, feed) for feed in _feeds()]
        futures.append(pool.submit(_fetch_fred))
        for fut in as_completed(futures):
            try:
                name, batch, err = fut.result()
            except Exception as exc:
                errors.append(str(exc))
                continue
            if name == "FRED" and not _fred_key():
                fred_status = "not_configured"
            elif name == "FRED" and err:
                fred_status = "unavailable"
            elif name == "FRED" and batch:
                fred_status = "ok"
            if err:
                errors.append(err)
            items.extend(batch)
    recent = [it for it in items if within_hours(it.get("published_at"), hours)]
    recent.sort(key=lambda it: it.get("published_at") or "", reverse=True)
    recent = recent[:limit]
    if not recent:
        status = "not_configured"
        digest = "MACRO: not_configured. Data is missing. Do not invent figures."
        if errors:
            digest += "\n" + "\n".join(f"- source: unavailable ({e})" for e in errors)
        return {
            "macro": status,
            "status": status,
            "fred": fred_status,
            "items": [],
            "errors": errors,
            "digest": digest,
        }
    digest = format_digest("MACRO", recent, hours)
    if errors:
        digest += "\n" + "\n".join(f"- source: unavailable ({e})" for e in errors)
    if fred_status == "not_configured":
        digest += "\n- FRED: not_configured"
    return {
        "macro": "ok",
        "status": "ok",
        "fred": fred_status,
        "items": recent,
        "errors": errors,
        "digest": digest,
    }


def fetch_macro(limit: int = 12) -> dict[str, Any]:
    try:
        return _collect_macro(limit)
    except Exception as exc:
        log.warning("fetch_macro failed: %s", exc)
        return {
            "macro": "not_configured",
            "status": "not_configured",
            "fred": "not_configured" if not _fred_key() else "unavailable",
            "items": [],
            "errors": [str(exc)],
            "digest": "MACRO: not_configured. Data is missing. Do not invent figures.",
        }


def load_macro() -> dict[str, Any]:
    try:
        import streamlit as st
        from config import ERROR_CACHE_TTL_SECONDS, MACRO_CACHE_TTL_SECONDS

        @st.cache_data(ttl=MACRO_CACHE_TTL_SECONDS, show_spinner=False)
        def _ok() -> dict[str, Any]:
            payload = fetch_macro()
            if payload.get("status") != "ok" or not payload.get("items"):
                raise RuntimeError("macro_incomplete")
            return payload

        @st.cache_data(ttl=ERROR_CACHE_TTL_SECONDS, show_spinner=False)
        def _retry() -> dict[str, Any]:
            return fetch_macro()

        try:
            return _ok()
        except Exception:
            _ok.clear()
            return _retry()
    except Exception:
        return fetch_macro()
