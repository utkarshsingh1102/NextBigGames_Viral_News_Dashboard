"""FastAPI routes for LinkedIn scraping management and post retrieval."""

import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.linkedin import LinkedInAccount, LinkedInPost

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AccountIn(BaseModel):
    profile_id: str          # e.g. "john-doe" from linkedin.com/in/john-doe
    display_name: Optional[str] = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: str
    display_name: Optional[str]
    active: bool
    created_at: datetime


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    post_urn: str
    text: Optional[str]
    author_name: Optional[str]
    profile_id: str
    likes: int
    comments: int
    shares: int
    tags: Optional[list[str]] = []
    posted_at: Optional[datetime]
    scraped_at: datetime


class PostList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PostOut]


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------

@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    """Return all configured LinkedIn accounts."""
    return db.query(LinkedInAccount).order_by(LinkedInAccount.created_at.desc()).all()


@router.post("/accounts", response_model=AccountOut, status_code=201)
def add_account(body: AccountIn, db: Session = Depends(get_db)):
    """Add a LinkedIn profile to track.

    Send the public profile identifier — e.g. for linkedin.com/in/john-doe
    the profile_id is "john-doe".
    """
    # Normalise: strip trailing slashes or full URL if user pastes it
    profile_id = body.profile_id.strip().rstrip("/")
    if "/in/" in profile_id:
        profile_id = profile_id.split("/in/")[-1].rstrip("/")

    account = LinkedInAccount(
        profile_id=profile_id,
        display_name=body.display_name or profile_id,
    )
    db.add(account)
    try:
        db.commit()
        db.refresh(account)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Profile already being tracked.")
    logger.info("Added LinkedIn account: %s", profile_id)
    return account


@router.patch("/accounts/{account_id}/toggle", response_model=AccountOut)
def toggle_account(account_id: uuid.UUID, db: Session = Depends(get_db)):
    """Toggle active/inactive status for a LinkedIn account."""
    account = db.query(LinkedInAccount).filter(LinkedInAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    account.active = not account.active
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: uuid.UUID, db: Session = Depends(get_db)):
    """Remove a LinkedIn account (and all its scraped posts) from tracking."""
    account = db.query(LinkedInAccount).filter(LinkedInAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    db.delete(account)
    db.commit()
    logger.info("Deleted LinkedIn account: %s", account.profile_id)


# ---------------------------------------------------------------------------
# Post retrieval
# ---------------------------------------------------------------------------

@router.get("/posts", response_model=PostList)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    profile_id: Optional[str] = Query(None, description="Filter by LinkedIn profile_id"),
    db: Session = Depends(get_db),
):
    """Return scraped LinkedIn posts, newest first."""
    offset = (page - 1) * page_size
    query = db.query(LinkedInPost).order_by(LinkedInPost.posted_at.desc().nullslast())
    if profile_id:
        query = query.filter(LinkedInPost.profile_id == profile_id)
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return PostList(total=total, page=page, page_size=page_size, items=items)


# ---------------------------------------------------------------------------
# Manual scrape trigger
# ---------------------------------------------------------------------------

def _run_linkedin_scrape():
    """Background thread target: scrape all active LinkedIn accounts."""
    from app.database import SessionLocal
    from app.services.linkedin_scraper import fetch_profile_posts

    db = SessionLocal()
    try:
        accounts = (
            db.query(LinkedInAccount)
            .filter(LinkedInAccount.active.is_(True))
            .all()
        )
    finally:
        db.close()

    if not accounts:
        logger.info("No active LinkedIn accounts to scrape.")
        return

    for account in accounts:
        _scrape_account(account.id, account.profile_id)


def _scrape_account(account_id, profile_id: str) -> int:
    """Scrape one account and persist new posts. Returns count of new posts saved."""
    from app.database import SessionLocal
    from app.services.linkedin_scraper import fetch_profile_posts

    posts = fetch_profile_posts(profile_id, account_id)
    if not posts:
        return 0

    db = SessionLocal()
    saved = 0
    try:
        for post_data in posts:
            # tag posts using the same keyword filter used for news articles
            try:
                from app.services.keyword_filter import tag_article
                post_data["tags"] = tag_article(post_data.get("text", ""))
            except Exception:
                post_data["tags"] = []

            record = LinkedInPost(**post_data)
            db.add(record)
            try:
                db.flush()
                saved += 1
            except IntegrityError:
                db.rollback()
                logger.debug("Skipped duplicate LinkedIn post URN: %s", post_data.get("post_urn"))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("LinkedIn DB save error for %s: %s", profile_id, exc, exc_info=True)
    finally:
        db.close()

    logger.info("Saved %d new LinkedIn posts for profile: %s", saved, profile_id)
    return saved


@router.post("/trigger", status_code=202)
def trigger_linkedin_scrape():
    """Manually trigger a LinkedIn scraping run for all active accounts."""
    thread = threading.Thread(target=_run_linkedin_scrape, daemon=True)
    thread.start()
    return {"message": "LinkedIn scrape started."}
