"""FastAPI routes for viral gaming news."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.news import ViralGamingNews

router = APIRouter(prefix="/news", tags=["news"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class NewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source: str
    url: str
    summary: Optional[str]
    virality_score: float
    tags: Optional[list[str]] = []
    created_at: datetime


class NewsList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NewsItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=NewsList)
def list_news(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    min_score: float = Query(0.0, ge=0.0, description="Minimum virality score filter"),
    tag: Optional[str] = Query(None, description="Filter by tag (e.g. Funding, Launch, Trending)"),
    db: Session = Depends(get_db),
):
    """Return paginated viral gaming news, newest first. Optionally filter by tag."""
    offset = (page - 1) * page_size
    query = (
        db.query(ViralGamingNews)
        .filter(ViralGamingNews.virality_score >= min_score)
        .order_by(ViralGamingNews.created_at.desc())
    )
    if tag:
        query = query.filter(ViralGamingNews.tags.contains([tag]))
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return NewsList(total=total, page=page, page_size=page_size, items=items)


@router.get("/tags/list", response_model=list[str])
def list_tags():
    """Return all available tag names."""
    from app.services.keyword_filter import TAG_RULES
    return [tag for tag, _ in TAG_RULES]


@router.get("/{item_id}", response_model=NewsItem)
def get_news_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return a single news article by UUID."""
    record = db.query(ViralGamingNews).filter(ViralGamingNews.id == item_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Article not found.")
    return record
