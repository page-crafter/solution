from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from page_crafter.api.auth.dependencies import require_admin
from page_crafter.shared.db.session import get_session
from page_crafter.shared.models.confluence import ConfluencePage
from page_crafter.shared.models.page_editor import PageEditRun
from page_crafter.shared.schemas.kpis import SpaceStat

router = APIRouter(tags=["spaces"])


@router.get("/spaces", response_model=list[SpaceStat])
def list_space_stats(
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[SpaceStat]:
    """Return per-space aggregated metrics for the dashboard."""
    rows = session.execute(
        select(
            ConfluencePage.space_key,
            func.max(ConfluencePage.space_name).label("space_name"),
            func.count().label("page_count"),
            func.count(ConfluencePage.id.distinct())
            .filter(ConfluencePage.extracted_text != "")
            .label("indexed_count"),
            func.max(ConfluencePage.last_synced_at).label("last_synced_at"),
        )
        .where(ConfluencePage.deleted_at.is_(None))
        .group_by(ConfluencePage.space_key)
        .order_by(func.count().desc())
    ).all()

    space_keys = [r.space_key for r in rows]
    draft_counts: dict[str, int] = {}
    if space_keys:
        draft_rows = session.execute(
            select(ConfluencePage.space_key, func.count().label("cnt"))
            .join(PageEditRun, PageEditRun.page_id == ConfluencePage.id)
            .where(
                ConfluencePage.space_key.in_(space_keys),
                ConfluencePage.deleted_at.is_(None),
                PageEditRun.status != "published",
            )
            .group_by(ConfluencePage.space_key)
        ).all()
        draft_counts = {r.space_key: r.cnt for r in draft_rows}

    result = []
    for r in rows:
        pct = round(r.indexed_count / r.page_count * 100, 1) if r.page_count else 0.0
        last_sync = r.last_synced_at.isoformat() if r.last_synced_at else ""
        result.append(
            SpaceStat(
                space_key=r.space_key,
                space_name=r.space_name or r.space_key,
                page_count=r.page_count,
                indexed_count=r.indexed_count,
                coverage_pct=pct,
                open_drafts=draft_counts.get(r.space_key, 0),
                last_synced_at=last_sync,
            )
        )
    return result
