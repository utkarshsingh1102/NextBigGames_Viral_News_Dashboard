"""RSS feed fetcher – returns normalised article dicts."""

import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional
import feedparser

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_url(url: str) -> str:
    """Follow redirects to get the real article URL.

    Google News RSS wraps every link in a news.google.com redirect that
    browsers block with ERR_BLOCKED_BY_RESPONSE. We follow the redirect
    at ingest time so the stored URL is always the real article page.
    Only applied to news.google.com URLs to avoid slowing other feeds.
    """
    if "news.google.com" not in url:
        return url
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; viral-news-bot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.url
    except Exception as exc:
        logger.debug("Could not resolve redirect for %s: %s", url, exc)
        return url


def _parse_published(entry) -> datetime:
    """Return a timezone-aware datetime from a feedparser entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _extract_summary(entry) -> Optional[str]:
    """Best-effort summary extraction from a feedparser entry."""
    for attr in ("summary", "description", "content"):
        value = getattr(entry, attr, None)
        if value:
            if isinstance(value, list):
                return value[0].get("value", "")
            return str(value)
    return None


def fetch_feed(url: str) -> list[dict]:
    """Fetch a single RSS feed and return a list of article dicts."""
    try:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            logger.warning("Feed parse error for %s: %s", url, parsed.bozo_exception)
            return []

        articles = []
        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            resolved_url = _resolve_url(link)
            articles.append(
                {
                    "title": title,
                    "url": resolved_url,
                    "source": parsed.feed.get("title", url),
                    "summary": _extract_summary(entry),
                    "published_at": _parse_published(entry),
                    "reddit_upvotes": 0,
                }
            )

        logger.info("Fetched %d entries from %s", len(articles), url)
        return articles

    except Exception as exc:
        logger.error("Failed to fetch feed %s: %s", url, exc, exc_info=True)
        return []


def fetch_all_feeds() -> list[dict]:
    """Fetch all configured RSS feeds and return merged article list."""
    all_articles: list[dict] = []
    for url in settings.RSS_FEEDS:
        all_articles.extend(fetch_feed(url))
    return all_articles
