import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ViralGamingNews(Base):
    __tablename__ = "viral_gaming_news"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    virality_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ViralGamingNews id={self.id} title={self.title!r} score={self.virality_score}>"
