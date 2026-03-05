"""Reddit post fetcher using PRAW."""

import logging
from datetime import datetime, timezone

import praw
from praw.exceptions import PRAWException

from app.config import settings

logger = logging.getLogger(__name__)


def _build_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )


def fetch_subreddit(subreddit_name: str, reddit: praw.Reddit) -> list[dict]:
    """Fetch top/hot posts from a subreddit and return normalised article dicts."""
    articles = []
    try:
        sub = reddit.subreddit(subreddit_name)
        for post in sub.hot(limit=settings.REDDIT_POST_LIMIT):
            if post.is_self and not post.selftext:
                continue
            articles.append(
                {
                    "title": post.title.strip(),
                    "url": post.url.strip(),
                    "source": f"reddit/r/{subreddit_name}",
                    "summary": post.selftext[:500] if post.selftext else None,
                    "published_at": datetime.fromtimestamp(
                        post.created_utc, tz=timezone.utc
                    ),
                    "reddit_upvotes": post.score,
                }
            )
        logger.info(
            "Fetched %d posts from r/%s", len(articles), subreddit_name
        )
    except PRAWException as exc:
        logger.error(
            "PRAW error fetching r/%s: %s", subreddit_name, exc, exc_info=True
        )
    except Exception as exc:
        logger.error(
            "Unexpected error fetching r/%s: %s", subreddit_name, exc, exc_info=True
        )
    return articles


def fetch_all_subreddits() -> list[dict]:
    """Fetch posts from all configured subreddits."""
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_SECRET:
        logger.warning(
            "Reddit credentials not configured – skipping Reddit fetch."
        )
        return []

    all_articles: list[dict] = []
    try:
        reddit = _build_client()
        for sub in settings.SUBREDDITS:
            all_articles.extend(fetch_subreddit(sub, reddit))
    except Exception as exc:
        logger.error("Failed to initialise Reddit client: %s", exc, exc_info=True)
    return all_articles
