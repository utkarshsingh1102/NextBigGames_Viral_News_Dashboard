"""FastAPI routes for managing RSS sources."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, HttpUrl
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.source import RSSSource

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    url: str
    active: bool
    created_at: datetime


class SourceCreate(BaseModel):
    name: str
    url: str


@router.get("", response_model=list[SourceItem])
def list_sources(db: Session = Depends(get_db)):
    """Return all RSS sources (active and inactive)."""
    return db.query(RSSSource).order_by(RSSSource.created_at.asc()).all()


@router.post("", response_model=SourceItem, status_code=201)
def add_source(body: SourceCreate, db: Session = Depends(get_db)):
    """Add a new RSS source."""
    existing = db.query(RSSSource).filter(RSSSource.url == body.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source URL already exists.")
    source = RSSSource(name=body.name, url=body.url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}/toggle", response_model=SourceItem)
def toggle_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    """Toggle a source active/inactive."""
    source = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    source.active = not source.active
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete an RSS source permanently."""
    source = db.query(RSSSource).filter(RSSSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    db.delete(source)
    db.commit()
