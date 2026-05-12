from cm_shared.db.session import get_session
from cm_shared.confluence.move_validation import (
    PageMoveOutsideSpaceError,
    ensure_move_stays_in_space,
)
from cm_shared.models.confluence import ConfluencePage
from cm_shared.models.jobs import SyncRun
from cm_shared.schemas.common import JobRead
from cm_shared.schemas.confluence import CreatePageRequest, MovePageRequest, PageDetail, PageRead
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from cm_api.auth.dependencies import require_admin
from cm_api.auth.user import CurrentUser
from cm_api.services.audit import record_audit
from cm_api.services.pages import get_active_page
from cm_api.services.queue import enqueue_task_for_job

router = APIRouter(prefix="/confluence", tags=["confluence"])


@router.get("/pages", response_model=list[PageRead])
def list_pages(
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[PageRead]:
    """Return all non-deleted synced Confluence pages."""
    pages = session.scalars(
        select(ConfluencePage)
        .where(ConfluencePage.deleted_at.is_(None))
        .order_by(
            ConfluencePage.parent_confluence_id,
            ConfluencePage.sort_order,
            ConfluencePage.title,
        )
    ).all()
    return list(pages)


@router.get("/pages/{page_id}", response_model=PageDetail)
def read_page(
    page_id: int,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> PageDetail:
    """Return one synced page with source XHTML and extracted text."""
    return get_active_page(session, page_id)


def create_page_job(
    session: Session,
    task_name: str,
    page_id: int,
    *,
    actor: str,
    message: str,
) -> SyncRun:
    """Create a sync-style job for a page-level Confluence action."""
    run = SyncRun(status="queued")
    session.add(run)
    session.flush()
    enqueue_task_for_job(
        session,
        run,
        task_name,
        run.id,
        page_id,
        actor=actor,
        message=message,
    )
    return run


@router.post("/pages", response_model=JobRead)
def create_empty_page(
    request: CreatePageRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> JobRead:
    """Queue creation of an empty Confluence page for later processing."""
    run = SyncRun(status="queued")
    session.add(run)
    session.flush()
    record_audit(session, user.email, "page.create_empty.requested", "page", request.title)
    enqueue_task_for_job(
        session,
        run,
        "cm_worker.create_empty_page",
        run.id,
        request.title,
        request.parent_id,
        actor=user.email,
        message=f"Empty page creation queued for {request.title}",
    )
    return JobRead(id=run.id, status=run.status, task_id=run.task_id)


@router.post("/pages/{page_id}/refresh", response_model=JobRead)
def refresh_page(
    page_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> JobRead:
    """Queue a worker refresh for a single Confluence page."""
    run = create_page_job(
        session,
        "cm_worker.refresh_page",
        page_id,
        actor=user.email,
        message=f"Page refresh queued for page {page_id}",
    )
    record_audit(session, user.email, "page.refresh.requested", "page", str(page_id))
    session.commit()
    return JobRead(id=run.id, status=run.status, task_id=run.task_id)


@router.post("/pages/{page_id}/move", response_model=JobRead)
def move_page(
    page_id: int,
    request: MovePageRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> JobRead:
    """Queue a worker move operation for a Confluence page."""
    page = get_active_page(session, page_id)

    target = session.scalar(
        select(ConfluencePage)
        .where(ConfluencePage.confluence_id == request.target_id)
        .where(ConfluencePage.deleted_at.is_(None))
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Target page not found")
    try:
        ensure_move_stays_in_space(page, target)
    except PageMoveOutsideSpaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run = SyncRun(status="queued")
    session.add(run)
    session.flush()
    record_audit(session, user.email, "page.move.requested", "page", str(page_id))
    enqueue_task_for_job(
        session,
        run,
        "cm_worker.move_page",
        run.id,
        page_id,
        request.target_id,
        request.position,
        actor=user.email,
        message=f"Page move queued for page {page_id}",
    )
    return JobRead(id=run.id, status=run.status, task_id=run.task_id)


@router.delete("/pages/{page_id}", response_model=JobRead)
def delete_page(
    page_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> JobRead:
    """Queue a worker delete operation for a Confluence page."""
    run = create_page_job(
        session,
        "cm_worker.delete_page",
        page_id,
        actor=user.email,
        message=f"Page deletion queued for page {page_id}",
    )
    record_audit(session, user.email, "page.delete.requested", "page", str(page_id))
    session.commit()
    return JobRead(id=run.id, status=run.status, task_id=run.task_id)
