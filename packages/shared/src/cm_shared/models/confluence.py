from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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
