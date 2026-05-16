from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from page_crafter.api.auth.dependencies import require_admin
from page_crafter.shared.db.session import get_session
from page_crafter.shared.models.confluence import ConfluencePage
from page_crafter.shared.models.jobs import TaskExecution
from page_crafter.shared.models.page_editor import PageEditRun
from page_crafter.shared.schemas.kpis import KpiCard

router = APIRouter(tags=["kpis"])


def _time_ago(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    diff = int((now - dt).total_seconds())
    if diff < 60:
        return f"{diff}s ago"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


@router.get("/kpis", response_model=list[KpiCard])
def list_kpis(
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[KpiCard]:
    """Return enriched dashboard KPI cards backed by current data."""
    total_pages = (
        session.scalar(
            select(func.count())
            .select_from(ConfluencePage)
            .where(ConfluencePage.deleted_at.is_(None))
        )
        or 0
    )

    indexed = (
        session.scalar(
            select(func.count())
            .select_from(ConfluencePage)
            .where(ConfluencePage.deleted_at.is_(None), ConfluencePage.extracted_text != "")
        )
        or 0
    )

    coverage_pct = round(indexed / total_pages * 100, 1) if total_pages else 0.0

    spaces = (
        session.scalar(
            select(func.count(func.distinct(ConfluencePage.space_key)))
            .select_from(ConfluencePage)
            .where(ConfluencePage.deleted_at.is_(None))
        )
        or 0
    )

    open_drafts = (
        session.scalar(
            select(func.count()).select_from(PageEditRun).where(PageEditRun.status != "published")
        )
        or 0
    )

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    published_today = (
        session.scalar(
            select(func.count())
            .select_from(PageEditRun)
            .where(PageEditRun.status == "published", PageEditRun.updated_at >= today_start)
        )
        or 0
    )

    failed_tasks = (
        session.scalar(
            select(func.count())
            .select_from(TaskExecution)
            .where(TaskExecution.status == "failed", TaskExecution.created_at >= today_start)
        )
        or 0
    )

    last_sync_row = session.scalar(
        select(func.max(ConfluencePage.last_synced_at)).select_from(ConfluencePage)
    )

    return [
        KpiCard(label="Spaces", value=str(spaces), trend="Active spaces", tone="blue"),
        KpiCard(label="Synced pages", value=str(total_pages), trend="Full space", tone="blue"),
        KpiCard(label="Indexed", value=str(indexed), trend="Search corpus", tone="green"),
        KpiCard(label="Coverage", value=f"{coverage_pct} %", trend="Indexed / total", tone="green"),
        KpiCard(
            label="Open drafts", value=str(open_drafts), trend="Awaiting review", tone="orange"
        ),
        KpiCard(
            label="Published today",
            value=str(published_today),
            trend="Pages shipped",
            tone="purple",
        ),
        KpiCard(
            label="Failed tasks",
            value=str(failed_tasks),
            trend="Today",
            tone="red" if failed_tasks else "neutral",
        ),
        KpiCard(
            label="Last sync",
            value=_time_ago(last_sync_row),
            trend="Space synchronisation",
            tone="neutral",
        ),
    ]
