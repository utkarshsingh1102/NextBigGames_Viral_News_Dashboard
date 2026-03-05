import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Float, DateTime, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ArticleStatus(str, enum.Enum):
    NOT_POSTED = "NOT_POSTED"
    IN_QUEUE = "IN_QUEUE"
    PUBLISHED = "PUBLISHED"
    DISCARDED = "DISCARDED"


class ViralGamingNews(Base):
    __tablename__ = "viral_gaming_news"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    virality_score = Column(Float, nullable=False, default=0.0)
    tags = Column(JSONB, nullable=True, default=list)
    status = Column(String, nullable=False, default=ArticleStatus.NOT_POSTED)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ViralGamingNews id={self.id} title={self.title!r} score={self.virality_score}>"
