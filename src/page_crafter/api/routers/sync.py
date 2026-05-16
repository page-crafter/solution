from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from page_crafter.api.auth.dependencies import require_admin
from page_crafter.api.auth.user import CurrentUser
from page_crafter.api.services.audit import record_audit
from page_crafter.api.services.queue import enqueue_task_for_job
from page_crafter.shared.db.session import get_session
from page_crafter.shared.models.jobs import SyncRun
from page_crafter.shared.schemas.common import JobRead

router = APIRouter(tags=["sync"])


@router.post("/sync/runs", response_model=JobRead)
def create_sync_run(
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> JobRead:
    """Queue a full-space Confluence sync in the dedicated worker."""
    run = SyncRun(status="queued")
    session.add(run)
    session.flush()
    record_audit(session, user.email, "sync.requested", "sync_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.sync_space",
        run.id,
        actor=user.email,
        message="Full-space sync queued",
    )
    return JobRead(id=run.id, status=run.status, task_id=run.task_id, message=run.message)
