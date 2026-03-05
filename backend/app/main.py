"""FastAPI application entry point."""

import logging
import logging.config
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.linkedin import router as linkedin_router
from app.routes.news import router as news_router
from app.routes.sources import router as sources_router
from app.routes.whatsapp import router as whatsapp_router
from app.scheduler.job_runner import run_ingestion_job, start_scheduler, stop_scheduler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Viral Gaming News service...")
    try:
        init_db()
        logger.info("Database initialised successfully.")
    except Exception as exc:
        logger.critical(
            "DATABASE INIT FAILED – check DATABASE_URL is set: %s", exc, exc_info=True
        )
        # Don't raise – let the server start so /health returns a degraded status
        # and Railway logs show the real error instead of a silent crash.
    else:
        # Only start ingestion if DB is available
        threading.Thread(target=run_ingestion_job, daemon=True).start()
        start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Viral Gaming News API",
    description="Detects and surfaces viral hybrid-casual & mobile gaming news.",
    version="1.0.0",
    lifespan=lifespan,
    # OpenAPI docs served at /docs – useful when building the Lovable frontend
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# All routes live under /api/v1 so Lovable can point to a stable base URL
app.include_router(news_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api/v1")
app.include_router(linkedin_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    """Liveness probe – also used by Lovable to verify the backend is reachable."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/v1/trigger", tags=["admin"], status_code=202)
def trigger_ingestion():
    """Manually trigger an ingestion run (useful during Lovable development)."""
    thread = threading.Thread(target=run_ingestion_job, daemon=True)
    thread.start()
    return {"message": "Ingestion job started."}
