from datetime import datetime

from cm_shared.models.confluence import ConfluencePage
from sqlalchemy import select
from sqlalchemy.orm import Session


def mark_missing_pages_deleted(
    session: Session,
    active_confluence_ids: set[str],
) -> list[ConfluencePage]:
    """Mark pages no longer present in Confluence as deleted."""
    missing_pages = session.scalars(
        select(ConfluencePage)
        .where(ConfluencePage.deleted_at.is_(None))
        .where(ConfluencePage.confluence_id.not_in(active_confluence_ids))
    ).all()
    for page in missing_pages:
        page.deleted_at = datetime.utcnow()
    return list(missing_pages)


def remove_missing_pages(session: Session, active_confluence_ids: set[str]) -> int:
    """Mark pages no longer present in Confluence as deleted."""
    return len(mark_missing_pages_deleted(session, active_confluence_ids))
