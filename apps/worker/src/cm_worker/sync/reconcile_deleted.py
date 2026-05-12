from datetime import datetime

from cm_shared.models.confluence import ConfluencePage, DocumentChunk
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


def mark_missing_pages_deleted(
    session: Session,
    active_confluence_ids: set[str],
) -> list[ConfluencePage]:
    """Delete local vector data and mark pages no longer present in Confluence."""
    missing_pages = session.scalars(
        select(ConfluencePage)
        .where(ConfluencePage.deleted_at.is_(None))
        .where(ConfluencePage.confluence_id.not_in(active_confluence_ids))
    ).all()
    for page in missing_pages:
        session.execute(delete(DocumentChunk).where(DocumentChunk.page_id == page.id))
        page.deleted_at = datetime.utcnow()
    return list(missing_pages)


def remove_missing_pages(session: Session, active_confluence_ids: set[str]) -> int:
    """Delete vector data for pages no longer present in Confluence."""
    return len(mark_missing_pages_deleted(session, active_confluence_ids))
