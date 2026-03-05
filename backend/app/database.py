import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables, run safe migrations, and seed default sources."""
    from app.models import news  # noqa: F401
    from app.models import source  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Safe migrations for the viral_gaming_news table
    with engine.connect() as conn:
        # Add tags column if it doesn't exist yet (first-time deploys)
        conn.execute(text(
            "ALTER TABLE viral_gaming_news ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'"
        ))
        # Convert existing JSON column to JSONB so @> (contains) queries work
        conn.execute(text(
            "ALTER TABLE viral_gaming_news ALTER COLUMN tags TYPE JSONB USING tags::JSONB"
        ))
        conn.commit()

    # Seed default RSS sources if the table is empty
    db = SessionLocal()
    try:
        from app.models.source import RSSSource
        if db.query(RSSSource).count() == 0:
            defaults = [
                RSSSource(name="Pocket Gamer", url="https://www.pocketgamer.com/feed/"),
                RSSSource(name="Pocket Gamer Biz", url="https://www.pocketgamer.biz/rss/"),
                RSSSource(name="Gamigion", url="https://www.gamigion.com/feed/"),
            ]
            for s in defaults:
                db.add(s)
            db.commit()
            logger.info("Seeded %d default RSS sources.", len(defaults))
    finally:
        db.close()

    logger.info("Database tables initialised.")
