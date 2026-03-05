"""Virality scoring and deduplication logic."""

import re
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher

from app.config import settings

logger = logging.getLogger(__name__)

# How many hours back qualifies for max recency bonus
_MAX_RECENCY_HOURS = 24
_SIMILARITY_THRESHOLD = 0.80  # titles this similar are considered duplicates


def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _recency_weight(published_at: datetime) -> float:
    """Return a float 0.0–5.0 based on how recently the article was published."""
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    if age_hours < 0:
        age_hours = 0
    # Linear decay: full score within 1 hour, zero at _MAX_RECENCY_HOURS
    ratio = max(0.0, 1.0 - age_hours / _MAX_RECENCY_HOURS)
    return round(ratio * 5.0, 3)


def _titles_similar(a: str, b: str) -> bool:
    ratio = SequenceMatcher(None, _normalise_title(a), _normalise_title(b)).ratio()
    return ratio >= _SIMILARITY_THRESHOLD


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove duplicate articles based on URL equality or title similarity.

    Returns a list where each surviving article carries an extra key
    ``source_count`` indicating how many sources covered that story.
    """
    unique: list[dict] = []
    seen_urls: set[str] = set()

    for article in articles:
        url = article["url"]

        # URL exact match
        if url in seen_urls:
            # Merge: increment source_count on the existing entry
            for u in unique:
                if u["url"] == url:
                    u["source_count"] = u.get("source_count", 1) + 1
                    u["reddit_upvotes"] = max(
                        u.get("reddit_upvotes", 0), article.get("reddit_upvotes", 0)
                    )
                    break
            continue

        # Title similarity match
        merged = False
        for existing in unique:
            if _titles_similar(existing["title"], article["title"]):
                existing["source_count"] = existing.get("source_count", 1) + 1
                existing["reddit_upvotes"] = max(
                    existing.get("reddit_upvotes", 0),
                    article.get("reddit_upvotes", 0),
                )
                # Prefer the earlier published_at as canonical
                if article.get("published_at") and article["published_at"] < existing.get(
                    "published_at", datetime.now(timezone.utc)
                ):
                    existing["published_at"] = article["published_at"]
                merged = True
                break

        if not merged:
            article = dict(article)  # copy so we don't mutate caller's data
            article.setdefault("source_count", 1)
            unique.append(article)
            seen_urls.add(url)

    logger.debug(
        "Deduplication: %d → %d articles", len(articles), len(unique)
    )
    return unique


def compute_score(article: dict) -> float:
    """Compute the virality score for a single article dict.

    Formula:
        score = source_count * 3 + reddit_upvotes * 0.01 + recency_weight
    """
    source_count: int = article.get("source_count", 1)
    reddit_upvotes: int = article.get("reddit_upvotes", 0)
    published_at: datetime = article.get("published_at", datetime.now(timezone.utc))

    score = (
        source_count * 3
        + reddit_upvotes * 0.01
        + _recency_weight(published_at)
    )
    return round(score, 3)


def score_and_filter(articles: list[dict]) -> list[dict]:
    """Add virality_score to each article; return only those above threshold."""
    scored = []
    for article in articles:
        article["virality_score"] = compute_score(article)
        if article["virality_score"] >= settings.VIRALITY_THRESHOLD:
            scored.append(article)

    logger.info(
        "Virality filter: %d articles → %d viral", len(articles), len(scored)
    )
    return scored
