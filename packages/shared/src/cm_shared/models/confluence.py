from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cm_shared.db.base import Base


class ConfluencePage(Base):
    """Persist the latest synced Confluence page and its draft/index state."""

    __tablename__ = "confluence_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    confluence_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    space_key: Mapped[str] = mapped_column(String(64), index=True)
    space_name: Mapped[Optional[str]] = mapped_column(String(255))
    parent_confluence_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(64), default="current")
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    source_storage_xhtml: Mapped[str] = mapped_column(Text, default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    web_url: Mapped[Optional[str]] = mapped_column(String(1000))
    edit_url: Mapped[Optional[str]] = mapped_column(String(1000))
    tiny_url: Mapped[Optional[str]] = mapped_column(String(1000))
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    draft_state: Mapped[str] = mapped_column(String(64), default="Published")
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """Store text chunks and pgvector embeddings linked to a Confluence page."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("page_id", "chunk_index", "page_version", name="uq_chunk_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("confluence_pages.id", ondelete="CASCADE"))
    confluence_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    page: Mapped[ConfluencePage] = relationship(back_populates="chunks")
