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
    FETCH_INTERVAL_MINUTES: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))

    # Virality threshold (lowered since Reddit is removed – max score without Reddit is ~8)
    VIRALITY_THRESHOLD: float = float(os.getenv("VIRALITY_THRESHOLD", "3.0"))

    # RSS feeds – only trusted mobile/gaming sources
    RSS_FEEDS: list[str] = [
        # Pocket Gamer (consumer)
        "https://www.pocketgamer.com/feed/",
        # Pocket Gamer Biz (industry / B2B)
        "https://www.pocketgamer.biz/rss/",
        # Gamigion
        "https://www.gamigion.com/feed/",
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

    # LinkedIn scraper credentials (unofficial API — use a secondary account)
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")

    # Public base URL of this API (used in OpenAPI docs / Lovable env var)
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


settings = Settings()
