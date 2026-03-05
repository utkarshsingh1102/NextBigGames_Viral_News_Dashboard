import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(Text, nullable=False, unique=True)  # e.g. "john-doe" from linkedin.com/in/john-doe
    display_name = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LinkedInAccount profile_id={self.profile_id!r} active={self.active}>"


class LinkedInPost(Base):
    __tablename__ = "linkedin_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False)
    post_urn = Column(Text, nullable=False, unique=True)  # LinkedIn's internal URN (dedup key)
    text = Column(Text, nullable=True)
    author_name = Column(Text, nullable=True)
    profile_id = Column(Text, nullable=False)  # denormalised for easy querying
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    tags = Column(JSONB, nullable=True, default=list)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    scraped_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LinkedInPost urn={self.post_urn!r} likes={self.likes}>"
