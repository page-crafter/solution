from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cm_shared.db.base import Base


def make_uuid() -> str:
    """Create a string UUID for externally visible job and run identifiers."""
    return str(uuid4())


class SyncRun(Base):
    """Track a full-space Confluence synchronization run."""

    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    status: Mapped[str] = mapped_column(String(64), default="queued")
    task_id: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str | None] = mapped_column(Text)


class JobEvent(Base):
    """Append-only progress event emitted by API and worker jobs."""

    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), index=True)
    level: Mapped[str] = mapped_column(String(32), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskExecution(Base):
    """Persist the lifecycle of every queued worker task."""

    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), index=True)
    task_id: Mapped[str | None] = mapped_column(String(128), index=True)
    task_name: Mapped[str] = mapped_column(String(255), index=True)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    status: Mapped[str] = mapped_column(String(64), default="queued", index=True)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class AuditEvent(Base):
    """Record durable user and worker actions for traceability."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    action: Mapped[str] = mapped_column(String(255))
    target_type: Mapped[str] = mapped_column(String(128))
    target_id: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
