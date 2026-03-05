"""LinkedIn post scraper using the unofficial linkedin-api package.

Requires environment variables:
    LINKEDIN_EMAIL    - Your LinkedIn account email
    LINKEDIN_PASSWORD - Your LinkedIn account password

The account credentials are used to authenticate with LinkedIn's unofficial
API. Use a secondary/dedicated LinkedIn account to avoid risking your main
account in case LinkedIn detects automated access.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
_LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")


def _get_client():
    from linkedin_api import Linkedin  # type: ignore[import]
    return Linkedin(_LINKEDIN_EMAIL, _LINKEDIN_PASSWORD)


def _safe_get(d: dict, *keys, default=None):
    """Safely navigate nested dicts."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, {})
    return d if d != {} else default


def _parse_post(raw: dict, account_id, profile_id: str) -> Optional[dict]:
    """Extract a normalised post dict from linkedin-api raw response."""
    try:
        # URN — used as the unique dedup key
        urn = (
            raw.get("entityUrn")
            or raw.get("updateKey")
            or raw.get("*updateMetadata")
            or ""
        )
        if not urn:
            return None

        # Post text
        text = _safe_get(raw, "commentary", "text", "text", default="") or ""

        # Author
        author_name = (
            _safe_get(raw, "actor", "name", "text", default="")
            or profile_id
        )

        # Social counts
        counts = _safe_get(raw, "socialDetail", "totalSocialActivityCounts", default={}) or {}
        likes = counts.get("numLikes", 0) or 0
        comments = counts.get("numComments", 0) or 0
        shares = counts.get("numShares", 0) or 0

        # Timestamp (LinkedIn returns milliseconds)
        created_ms = raw.get("createdAt")
        posted_at: Optional[datetime] = None
        if created_ms:
            try:
                posted_at = datetime.fromtimestamp(int(created_ms) / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        return {
            "account_id": account_id,
            "post_urn": urn,
            "text": text,
            "author_name": author_name,
            "profile_id": profile_id,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "posted_at": posted_at,
        }
    except Exception as exc:
        logger.warning("Failed to parse LinkedIn post: %s", exc)
        return None


def fetch_profile_posts(
    profile_id: str,
    account_id,
    post_count: int = 20,
) -> list[dict]:
    """Fetch posts from a LinkedIn public profile.

    Returns a list of normalised post dicts ready for DB insertion.
    Returns an empty list if credentials are missing or scraping fails.
    """
    if not _LINKEDIN_EMAIL or not _LINKEDIN_PASSWORD:
        logger.warning("LinkedIn credentials not configured — skipping scrape for %s.", profile_id)
        return []

    try:
        client = _get_client()
        raw_posts = client.get_profile_posts(profile_id, post_count=post_count)
    except Exception as exc:
        logger.error("LinkedIn authentication/fetch failed for %s: %s", profile_id, exc, exc_info=True)
        return []

    posts: list[dict] = []
    for raw in (raw_posts or []):
        parsed = _parse_post(raw, account_id, profile_id)
        if parsed:
            posts.append(parsed)

    logger.info("Fetched %d posts from LinkedIn profile: %s", len(posts), profile_id)
    return posts
