from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from cm_api.auth.dependencies import require_admin
from cm_api.services.queue import revoke_task
from cm_shared.db.session import get_session
from cm_shared.jobs.history import cancel_active_task_executions
from cm_shared.models.jobs import JobEvent, SyncRun, TaskExecution
from cm_shared.models.page_editor import PageEditRun
from cm_shared.schemas.common import JobEventRead, JobRead, TaskExecutionRead

router = APIRouter(tags=["jobs"])


def find_job(session: Session, job_id: str) -> SyncRun | PageEditRun | None:
    """Find a sync or page edit job by its external identifier."""
    return session.get(SyncRun, job_id) or session.get(PageEditRun, job_id)


@router.get("/jobs/history", response_model=list[TaskExecutionRead])
def list_task_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[TaskExecutionRead]:
    """Return recent worker task executions across sync, page editing, and chat."""
    executions = session.scalars(
        select(TaskExecution)
        .order_by(TaskExecution.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(executions)


@router.get("/jobs/{job_id}", response_model=JobRead)
def read_job(
    job_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> JobRead:
    """Return the current status of a sync or page edit job."""
    job = find_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead(
        id=job.id,
        status=job.status,
        task_id=job.task_id,
        message=getattr(job, "message", None) or getattr(job, "error_message", None),
    )


@router.get("/jobs/{job_id}/events", response_model=list[JobEventRead])
def list_job_events(
    job_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[JobEventRead]:
    """Return chronological progress events for a worker job."""
    events = session.scalars(
        select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)
    ).all()
    return list(events)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
def cancel_job(
    job_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> JobRead:
    """Cancel a queued or running job when Celery can revoke it."""
    job = find_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.task_id:
        revoke_task(job.task_id)
    job.status = "cancelled"
    cancel_active_task_executions(session, job_id=job_id, message="Cancelled by user")
    if isinstance(job, PageEditRun):
        job.draft_status = "Published"
        job.markdown_draft = None
        job.generated_storage_xhtml = None
        job.preview_html = None
        job.preview_status = "not_started"
    session.commit()
    return JobRead(id=job.id, status=job.status, task_id=job.task_id)
