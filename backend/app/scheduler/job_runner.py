"""Background scheduler that periodically fetches and processes gaming news."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal
from app.models.news import ViralGamingNews
from app.services.rss_fetcher import fetch_all_feeds
from app.services.keyword_filter import filter_articles
from app.services.virality_engine import deduplicate, score_and_filter

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _save_articles(articles: list[dict]) -> int:
    """Persist articles to the database, skipping duplicates. Returns saved count."""
    saved = 0
    db = SessionLocal()
    try:
        for article in articles:
            record = ViralGamingNews(
                title=article["title"],
                source=article["source"],
                url=article["url"],
                summary=article.get("summary"),
                virality_score=article["virality_score"],
                created_at=article.get("published_at", datetime.now(timezone.utc)),
            )
            db.add(record)
            try:
                db.flush()  # flush individually to catch per-row IntegrityError
                saved += 1
            except IntegrityError:
                db.rollback()
                logger.debug("Skipped duplicate URL: %s", article["url"])
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB save error: %s", exc, exc_info=True)
    finally:
        db.close()
    return saved


def run_ingestion_job() -> None:
    """Full pipeline: fetch → filter → deduplicate → score → save."""
    logger.info("--- Ingestion job started ---")

    # 1. Fetch from RSS feeds
    all_articles = fetch_all_feeds()
    logger.info("RSS: %d raw articles", len(all_articles))

    # 2. Filter by keywords
    filtered = filter_articles(all_articles)
    logger.info("After keyword filter: %d articles", len(filtered))

    if not filtered:
        logger.info("No matching articles found. Job done.")
        return

    # 3. Deduplicate
    deduped = deduplicate(filtered)
    logger.info("After deduplication: %d articles", len(deduped))

    # 4. Score and threshold
    viral = score_and_filter(deduped)
    logger.info("Viral articles (score >= %.1f): %d", settings.VIRALITY_THRESHOLD, len(viral))

    # 5. Persist
    saved = _save_articles(viral)
    logger.info("Saved %d new articles to database.", saved)
    logger.info("--- Ingestion job complete ---")


def start_scheduler() -> BackgroundScheduler:
    """Initialise and start the APScheduler background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=run_ingestion_job,
        trigger=IntervalTrigger(minutes=settings.FETCH_INTERVAL_MINUTES),
        id="ingestion_job",
        name="Viral Gaming News Ingestion",
        replace_existing=True,
        misfire_grace_time=60,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started – ingestion every %d minutes.",
        settings.FETCH_INTERVAL_MINUTES,
    )
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
