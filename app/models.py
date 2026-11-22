from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class MediaSource(Base):
    __tablename__ = "media_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    base_url = Column(String(500), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    # Sumber baru harus menunggu validasi dan persetujuan aktivasi manual.
    is_active = Column(Boolean, default=False, nullable=False)

    validation_status = Column(String(30), default="not_tested", nullable=False)
    validated_at = Column(DateTime, nullable=True)
    validation_config = Column(Text, nullable=True)
    validation_report = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    articles = relationship(
        "NewsArticle",
        back_populates="source",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    __table_args__ = (
        Index(
            "ix_news_articles_source_canonical_url",
            "source_id",
            "canonical_url",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    source_id = Column(
        Integer,
        ForeignKey("media_sources.id"),
        nullable=False,
        index=True,
    )

    url = Column(String(1500), nullable=False)
    canonical_url = Column(String(1500), nullable=True)

    title = Column(String(1000), nullable=False)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    author = Column(String(300), nullable=True)
    published_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    content_hash = Column(String(64), index=True, nullable=True)

    status = Column(String(30), default="collected")
    extra_metadata = Column(Text, nullable=True)

    source = relationship(
        "MediaSource",
        back_populates="articles",
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True, index=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)

    sources_checked = Column(Integer, default=0)
    articles_found = Column(Integer, default=0)
    articles_saved = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    articles_failed = Column(Integer, default=0)

    status = Column(String(30), default="running")
    error_message = Column(Text, nullable=True)


class SourceValidationRun(Base):
    __tablename__ = "source_validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        Integer,
        ForeignKey("media_sources.id"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="running", nullable=False)
    report = Column(Text, nullable=True)
    config = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    source = relationship("MediaSource")
