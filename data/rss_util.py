"""Shared RSS/HTML evidence parsing. No Streamlit cache here."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)

USER_AGENT = "crypto-bot-osint/1.0 (+local research)"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    text = str(value).strip()
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        cleaned = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def iso_or_none(value: Any) -> Optional[str]:
    dt = parse_datetime(value)
    return dt.isoformat() if dt else None


def clock_label(published_at: Optional[str]) -> str:
    dt = parse_datetime(published_at)
    if dt is None:
        return "n/a"
    return dt.strftime("%H:%M")


def within_hours(published_at: Optional[str], hours: float) -> bool:
    dt = parse_datetime(published_at)
    if dt is None:
        return True
    age = utc_now() - dt
    return age.total_seconds() <= hours * 3600


def evidence_item(
    *,
    headline: str,
    source: str,
    url: str = "",
    published_at: Optional[str] = None,
    summary: str = "",
    network: Optional[str] = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "headline": (headline or "").strip() or "(untitled)",
        "source": source,
        "url": url or "",
        "published_at": published_at,
        "summary": (summary or "").strip()[:400],
    }
    if network:
        item["network"] = network
    return item


def format_digest(title: str, items: list[dict[str, Any]], hours: Optional[float] = None) -> str:
    window = f" (last {int(hours)}h)" if hours else ""
    lines = [f"{title}{window}:"]
    if not items:
        lines.append("- (no items)")
        return "\n".join(lines)
    for item in items:
        src = item.get("source") or "unknown"
        clock = clock_label(item.get("published_at"))
        headline = item.get("headline") or "(untitled)"
        url = item.get("url") or ""
        suffix = f" ({url})" if url else ""
        lines.append(f"- [{src} {clock}] {headline}{suffix}")
    return "\n".join(lines)


def http_get(url: str, timeout: int, proxies: Optional[dict[str, str]] = None) -> bytes:
    res = requests.get(
        url,
        timeout=timeout,
        proxies=proxies,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*"},
        allow_redirects=True,
    )
    res.raise_for_status()
    return res.content


def parse_rss_bytes(content: bytes, source: str, network: Optional[str] = None) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ImportError:
        log.exception("feedparser is not installed")
        return []
    parsed = feedparser.parse(content)
    items: list[dict[str, Any]] = []
    for entry in parsed.entries or []:
        title = str(getattr(entry, "title", "") or "")
        link = str(getattr(entry, "link", "") or "")
        summary = str(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
        summary = re.sub(r"<[^>]+>", " ", summary)
        published = getattr(entry, "published", None) or getattr(entry, "updated", None)
        items.append(
            evidence_item(
                headline=title,
                source=source,
                url=link,
                published_at=iso_or_none(published),
                summary=summary,
                network=network,
            )
        )
    return items


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title = ""
        self.headings: list[str] = []
        self._in_h = False
        self._buf = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "h3"}:
            self._in_h = True
            self._buf = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"h1", "h2", "h3"} and self._in_h:
            text = re.sub(r"\s+", " ", self._buf).strip()
            if text:
                self.headings.append(text)
            self._in_h = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_h:
            self._buf += data


def parse_html_headlines(content: bytes, source: str, url: str, network: Optional[str] = None) -> list[dict[str, Any]]:
    parser = _TitleParser()
    try:
        parser.feed(content.decode("utf-8", errors="ignore"))
    except Exception:
        log.exception("HTML parse failed for %s", source)
        return []
    items: list[dict[str, Any]] = []
    if parser.title.strip():
        items.append(
            evidence_item(
                headline=parser.title.strip(),
                source=source,
                url=url,
                published_at=None,
                network=network,
            )
        )
    for heading in parser.headings[:12]:
        if heading == parser.title.strip():
            continue
        items.append(
            evidence_item(
                headline=heading,
                source=source,
                url=url,
                published_at=None,
                network=network,
            )
        )
    return items
