import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/viral_news"
    )
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_SECRET: str = os.getenv("REDDIT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv(
        "REDDIT_USER_AGENT", "viral-news-bot/1.0 (by /u/viralbot)"
    )

    # Scheduler
    FETCH_INTERVAL_MINUTES: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "10"))

    # Virality threshold
    VIRALITY_THRESHOLD: float = float(os.getenv("VIRALITY_THRESHOLD", "7.0"))

    # RSS feeds
    RSS_FEEDS: list[str] = [
        "https://www.pocketgamer.biz/rss/",
        "https://venturebeat.com/games/feed/",
        "https://www.gamesindustry.biz/feed",
        "https://news.google.com/rss/search?q=hybrid+casual+games",
        "https://news.google.com/rss/search?q=mobile+game+monetization",
        "https://news.google.com/rss/search?q=mobile+gaming+2024",
    ]

    # Subreddits
    SUBREDDITS: list[str] = ["gamedev", "gaming", "mobilegaming", "gamingnews"]
    REDDIT_POST_LIMIT: int = int(os.getenv("REDDIT_POST_LIMIT", "25"))

    # CORS – comma-separated list of allowed origins.
    # In production set this to your Lovable app URL, e.g.:
    #   CORS_ORIGINS=https://your-app.lovable.app
    # Use * only in local development.
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # Public base URL of this API (used in OpenAPI docs / Lovable env var)
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


settings = Settings()
