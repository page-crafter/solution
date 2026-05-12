from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cm_shared.db.base import Base
from cm_shared.models.jobs import make_uuid


class PageEditRun(Base):
    """Persist one documentation page edit from request through publish."""

    __tablename__ = "page_edit_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    page_id: Mapped[int] = mapped_column(ForeignKey("confluence_pages.id", ondelete="CASCADE"))
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="queued")
    draft_status: Mapped[str] = mapped_column(String(64), default="Draft in progress")
    preview_status: Mapped[str] = mapped_column(String(64), default="not_started")
    source_version: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[Optional[str]] = mapped_column(String(128))
    markdown_draft: Mapped[Optional[str]] = mapped_column(Text)
    generated_storage_xhtml: Mapped[Optional[str]] = mapped_column(Text)
    preview_html: Mapped[Optional[str]] = mapped_column(Text)
    diff_text: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    artifacts: Mapped[list["DraftArtifact"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    versions: Mapped[list["DraftVersion"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class DraftArtifact(Base):
    """Store generated draft artifacts that may be removed on cancellation."""

    __tablename__ = "draft_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("page_edit_runs.id", ondelete="CASCADE"))
    artifact_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[PageEditRun] = relationship(back_populates="artifacts")


class DraftVersion(Base):
    """Store validated Markdown draft versions for restore workflows."""

    __tablename__ = "draft_versions"
    __table_args__ = (
        UniqueConstraint("run_id", "version_number", name="uq_draft_versions_run_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("page_edit_runs.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer)
    markdown_draft: Mapped[str] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255), default="system")
    proposal_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("page_proposals.id", ondelete="SET NULL")
    )
    restored_from_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("draft_versions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[PageEditRun] = relationship(back_populates="versions")


class PageProposal(Base):
    """Store one LLM-proposed Markdown update before it is applied to a draft."""

    __tablename__ = "page_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    page_id: Mapped[int] = mapped_column(ForeignKey("confluence_pages.id", ondelete="CASCADE"))
    run_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("page_edit_runs.id", ondelete="SET NULL")
    )
    instruction: Mapped[str] = mapped_column(Text)
    base_markdown: Mapped[str] = mapped_column(Text, default="")
    base_source: Mapped[str] = mapped_column(String(32), default="page")
    status: Mapped[str] = mapped_column(String(64), default="queued")
    task_id: Mapped[Optional[str]] = mapped_column(String(128))
    proposed_markdown: Mapped[Optional[str]] = mapped_column(Text)
    diff_text: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
