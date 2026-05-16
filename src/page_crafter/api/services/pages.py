from fastapi import HTTPException
from sqlalchemy.orm import Session

from page_crafter.shared.models.confluence import ConfluencePage


def get_active_page(session: Session, page_id: int) -> ConfluencePage:
    """Return a non-deleted page or raise HTTP 404."""
    page = session.get(ConfluencePage, page_id)
    if page is None or page.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page
