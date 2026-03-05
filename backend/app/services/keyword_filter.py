"""Keyword filtering for gaming news articles."""

KEYWORDS: list[str] = [
    "hybrid casual",
    "mobile gaming",
    "game monetization",
    "iap",
    "in-app purchase",
    "live ops",
    "liveops",
    "user acquisition",
    "mobile game studio",
    "game economy",
]


def matches_keywords(text: str) -> bool:
    """Return True if *text* contains at least one target keyword (case-insensitive)."""
    lowered = text.lower()
    return any(kw in lowered for kw in KEYWORDS)


def filter_articles(articles: list[dict]) -> list[dict]:
    """Filter a list of article dicts, keeping only those that match keywords.

    Each dict is expected to have at least 'title' and optionally 'summary' keys.
    """
    kept = []
    for article in articles:
        combined = " ".join(
            filter(None, [article.get("title", ""), article.get("summary", "")])
        )
        if matches_keywords(combined):
            kept.append(article)
    return kept
