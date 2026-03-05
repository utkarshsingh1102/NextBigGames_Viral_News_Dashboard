"""Keyword filtering for gaming news articles."""

KEYWORDS: list[str] = [
    # Core mobile / casual gaming
    "mobile game",
    "mobile gaming",
    "casual game",
    "hyper casual",
    "hypercasual",
    "hybrid casual",
    "mobile app",
    # Funding & investment
    "funding",
    "investment",
    "raises",
    "raised",
    "series a",
    "series b",
    "series c",
    "seed round",
    "venture capital",
    "acquisition",
    "acquired",
    "merger",
    "valuation",
    # New launches & releases
    "launch",
    "launched",
    "soft launch",
    "global launch",
    "release",
    "released",
    "new game",
    "debut",
    "early access",
    # Trending & viral
    "trending",
    "viral",
    "top charts",
    "top grossing",
    "chart",
    "milestone",
    "downloads",
    "installs",
    # Monetisation & growth
    "game monetization",
    "iap",
    "in-app purchase",
    "live ops",
    "liveops",
    "user acquisition",
    "game economy",
    "revenue",
    "retention",
    # Industry
    "game studio",
    "game developer",
    "game publisher",
    "esports",
]


TAG_RULES: list[tuple[str, list[str]]] = [
    ("Funding", ["funding", "investment", "raises", "raised", "series a", "series b", "series c", "seed round", "venture capital", "valuation"]),
    ("Acquisition", ["acquisition", "acquired", "merger"]),
    ("Launch", ["launch", "launched", "soft launch", "global launch", "new game", "debut", "early access", "release", "released"]),
    ("Trending", ["trending", "viral", "top charts", "top grossing", "chart", "milestone"]),
    ("Growth", ["downloads", "installs", "revenue", "retention", "user acquisition"]),
    ("Monetization", ["game monetization", "iap", "in-app purchase", "game economy"]),
    ("LiveOps", ["live ops", "liveops"]),
    ("HybridCasual", ["hybrid casual", "hyper casual", "hypercasual", "casual game"]),
    ("MobileGaming", ["mobile game", "mobile gaming", "mobile app"]),
    ("Industry", ["game studio", "game developer", "game publisher", "esports"]),
]


def matches_keywords(text: str) -> bool:
    """Return True if *text* contains at least one target keyword (case-insensitive)."""
    lowered = text.lower()
    return any(kw in lowered for kw in KEYWORDS)


def tag_article(text: str) -> list[str]:
    """Return a list of tags that apply to *text* based on TAG_RULES."""
    lowered = text.lower()
    return [tag for tag, kws in TAG_RULES if any(kw in lowered for kw in kws)]


def filter_articles(articles: list[dict]) -> list[dict]:
    """Filter a list of article dicts, keeping only those that match keywords.

    Each dict is expected to have at least 'title' and optionally 'summary' keys.
    Also attaches auto-generated tags to each kept article.
    """
    kept = []
    for article in articles:
        combined = " ".join(
            filter(None, [article.get("title", ""), article.get("summary", "")])
        )
        if matches_keywords(combined):
            article["tags"] = tag_article(combined)
            kept.append(article)
    return kept
