from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from page_crafter.api.auth.dependencies import require_admin
from page_crafter.api.auth.user import CurrentUser
from page_crafter.api.services.audit import record_audit
from page_crafter.api.services.pages import get_active_page
from page_crafter.api.services.queue import enqueue_task_for_job, revoke_task
from page_crafter.shared.db.session import get_session
from page_crafter.shared.jobs.history import cancel_active_task_executions
from page_crafter.shared.models.confluence import ConfluencePage
from page_crafter.shared.models.page_editor import (
    DraftArtifact,
    DraftVersion,
    PageEditRun,
    PageProposal,
)
from page_crafter.shared.schemas.page_editor import (
    ApplyProposalResponse,
    CreatePageEditRunRequest,
    CreateProposalRequest,
    DraftVersionRead,
    PageEditRunRead,
    PageProposalRead,
    UpdateDraftRequest,
)

router = APIRouter(prefix="/editor", tags=["page-editor"])

ACTIVE_DRAFT_STATUSES = {"queued", "generating", "converting", "previewing"}
ACTIVE_PROPOSAL_STATUSES = {"queued", "generating"}


def get_run_or_404(session: Session, run_id: str) -> PageEditRun:
    """Fetch a page edit run or raise an HTTP 404 error."""
    run = session.get(PageEditRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Page edit run not found")
    return run


def get_proposal_or_404(session: Session, proposal_id: str) -> PageProposal:
    """Fetch a proposal or raise an HTTP 404 error."""
    proposal = session.get(PageProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


def newest_active_run(session: Session, page_id: int) -> PageEditRun | None:
    """Return the newest non-terminal run for a page when present."""
    return session.scalar(
        select(PageEditRun)
        .where(PageEditRun.page_id == page_id)
        .where(PageEditRun.status.not_in(["cancelled", "published"]))
        .order_by(PageEditRun.created_at.desc())
    )


def newest_draft_version(session: Session, run_id: str) -> DraftVersion | None:
    """Return the newest validated draft version for a run."""
    return session.scalar(
        select(DraftVersion)
        .where(DraftVersion.run_id == run_id)
        .order_by(DraftVersion.version_number.desc())
    )


def create_draft_version(
    session: Session,
    run: PageEditRun,
    change_source: str,
    actor: str,
    proposal_id: str | None = None,
    restored_from_version_id: int | None = None,
    allow_duplicate_latest: bool = False,
) -> DraftVersion | None:
    """Create a validated draft version unless the latest version has identical Markdown."""
    markdown_draft = run.markdown_draft or ""
    if not markdown_draft.strip():
        return None

    latest = newest_draft_version(session, run.id)
    if latest and latest.markdown_draft == markdown_draft and not allow_duplicate_latest:
        return latest

    version = DraftVersion(
        run_id=run.id,
        version_number=(latest.version_number + 1) if latest else 1,
        markdown_draft=markdown_draft,
        change_source=change_source,
        actor=actor,
        proposal_id=proposal_id,
        restored_from_version_id=restored_from_version_id,
    )
    session.add(version)
    session.flush()
    return version


def ensure_baseline_version(session: Session, run: PageEditRun, actor: str) -> DraftVersion | None:
    """Capture the current draft once before the first validated mutation."""
    if newest_draft_version(session, run.id) or not run.markdown_draft:
        return None
    return create_draft_version(session, run, "baseline", actor)


def reset_run_for_markdown_edit(
    session: Session,
    run: PageEditRun,
    markdown_draft: str,
) -> None:
    """Replace a run draft and clear stale generated artifacts before rendering."""
    if run.task_id and run.status in ACTIVE_DRAFT_STATUSES:
        revoke_task(run.task_id)
        cancel_active_task_executions(session, job_id=run.id, message="Superseded by draft edit")
    run.markdown_draft = markdown_draft
    run.generated_storage_xhtml = None
    run.preview_html = None
    run.diff_text = None
    run.error_message = None
    run.draft_status = "Draft generated"
    run.preview_status = "rendering"
    run.status = "converting"
    run.updated_at = datetime.now(UTC)
    session.execute(delete(DraftArtifact).where(DraftArtifact.run_id == run.id))


def proposal_base(
    session: Session,
    page: ConfluencePage,
    request: CreateProposalRequest,
) -> tuple[str | None, str, str]:
    """Resolve the Markdown base used for the next chat proposal."""
    if request.base_proposal_id:
        base_proposal = get_proposal_or_404(session, request.base_proposal_id)
        if base_proposal.page_id != page.id:
            raise HTTPException(status_code=409, detail="Base proposal belongs to another page")
        if base_proposal.status != "ready" or not base_proposal.proposed_markdown:
            raise HTTPException(status_code=409, detail="Base proposal is not ready")
        return base_proposal.run_id, base_proposal.proposed_markdown, "proposal"

    if request.base_markdown and request.base_markdown.strip():
        base_run_id = request.base_run_id
        if base_run_id:
            base_run = get_run_or_404(session, base_run_id)
            if base_run.page_id != page.id:
                raise HTTPException(status_code=409, detail="Base run belongs to another page")
            if base_run.status in {"cancelled", "published"}:
                raise HTTPException(status_code=409, detail="Base run is no longer editable")
        else:
            base_run = newest_active_run(session, page.id)
            base_run_id = base_run.id if base_run else None
        return base_run_id, request.base_markdown, "draft"

    active_run = newest_active_run(session, page.id)
    if active_run and active_run.markdown_draft:
        return active_run.id, active_run.markdown_draft, "draft"

    return None, page.source_markdown, "page"


@router.post("/runs", response_model=PageEditRunRead)
def create_page_edit_run(
    request: CreatePageEditRunRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Create an app-side draft and queue Markdown generation."""
    page = get_active_page(session, request.page_id)

    run = PageEditRun(
        page_id=page.id,
        instruction=request.instruction,
        source_version=page.version_number,
        status="queued",
        draft_status="Draft in progress",
    )
    page.draft_state = "Draft in progress"
    session.add(run)
    session.flush()
    record_audit(session, user.email, "page_edit.created", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.generate_markdown",
        run.id,
        actor=user.email,
        message="Markdown generation queued",
    )
    session.refresh(run)
    return run


@router.get("/runs/{run_id}", response_model=PageEditRunRead)
def read_page_edit_run(
    run_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> PageEditRunRead:
    """Return a page edit run and all review artifacts stored on it."""
    return get_run_or_404(session, run_id)


@router.get("/runs/{run_id}/draft-versions", response_model=list[DraftVersionRead])
def list_draft_versions(
    run_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> list[DraftVersion]:
    """Return validated Markdown draft versions for a run, newest first."""
    get_run_or_404(session, run_id)
    versions = session.scalars(
        select(DraftVersion)
        .where(DraftVersion.run_id == run_id)
        .order_by(DraftVersion.version_number.desc())
    ).all()
    return list(versions)


@router.get("/pages/{page_id}/active", response_model=PageEditRunRead | None)
def read_active_page_run(
    page_id: int,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> PageEditRun | None:
    """Return the newest active app-side draft for a page when one exists."""
    return newest_active_run(session, page_id)


@router.post("/pages/{page_id}/draft", response_model=PageEditRunRead)
def create_manual_draft(
    page_id: int,
    request: UpdateDraftRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Create an app-side draft from manually edited Markdown and render it."""
    page = get_active_page(session, page_id)
    if not request.markdown_draft.strip():
        raise HTTPException(status_code=400, detail="Markdown draft cannot be empty")

    run = PageEditRun(
        page_id=page.id,
        instruction="Manual Markdown edit",
        source_version=page.version_number,
        status="converting",
        draft_status="Draft generated",
        preview_status="rendering",
    )
    session.add(run)
    session.flush()
    reset_run_for_markdown_edit(session, run, request.markdown_draft)
    create_draft_version(session, run, "manual", user.email)
    page.draft_state = "Draft generated"
    record_audit(session, user.email, "draft.created", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.render_draft",
        run.id,
        actor=user.email,
        message="Manual draft preview rendering queued",
    )
    session.refresh(run)
    return run


@router.patch("/runs/{run_id}/draft", response_model=PageEditRunRead)
def update_draft(
    run_id: str,
    request: UpdateDraftRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Save manual Markdown corrections and queue a fresh preview render."""
    run = get_run_or_404(session, run_id)
    ensure_baseline_version(session, run, user.email)
    reset_run_for_markdown_edit(session, run, request.markdown_draft)
    create_draft_version(session, run, "manual", user.email)
    page = session.get(ConfluencePage, run.page_id)
    if page:
        page.draft_state = "Draft generated"
    record_audit(session, user.email, "draft.updated", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.render_draft",
        run.id,
        actor=user.email,
        message="Draft preview rendering queued",
    )
    session.refresh(run)
    return run


@router.post("/pages/{page_id}/proposals", response_model=PageProposalRead)
def create_proposal(
    page_id: int,
    request: CreateProposalRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageProposalRead:
    """Create an LLM proposal without mutating the current draft."""
    page = get_active_page(session, page_id)
    instruction = request.message.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    base_run_id, base_markdown, base_source = proposal_base(session, page, request)
    proposal = PageProposal(
        page_id=page_id,
        run_id=base_run_id,
        instruction=instruction,
        base_markdown=base_markdown,
        base_source=base_source,
        status="queued",
    )
    session.add(proposal)
    session.flush()
    record_audit(session, user.email, "proposal.created", "proposal", proposal.id)
    enqueue_task_for_job(
        session,
        proposal,
        "page_crafter.propose_markdown_update",
        proposal.id,
        actor=user.email,
        message="Markdown proposal queued",
    )
    session.refresh(proposal)
    return proposal


@router.get("/proposals/{proposal_id}", response_model=PageProposalRead)
def read_proposal(
    proposal_id: str,
    session: Session = Depends(get_session),
    _user=require_admin,
) -> PageProposalRead:
    """Return one Markdown proposal."""
    return get_proposal_or_404(session, proposal_id)


@router.post("/proposals/{proposal_id}/apply", response_model=ApplyProposalResponse)
def apply_proposal(
    proposal_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> ApplyProposalResponse:
    """Apply a ready proposal to a draft and queue preview rendering."""
    proposal = get_proposal_or_404(session, proposal_id)
    if proposal.status != "ready" or not proposal.proposed_markdown:
        raise HTTPException(status_code=409, detail="Proposal is not ready to apply")

    page = get_active_page(session, proposal.page_id)

    run = session.get(PageEditRun, proposal.run_id) if proposal.run_id else None
    if run is None or run.status in {"cancelled", "published"}:
        run = PageEditRun(
            page_id=page.id,
            instruction=proposal.instruction,
            source_version=page.version_number,
            status="converting",
            draft_status="Draft generated",
            preview_status="rendering",
        )
        session.add(run)
        session.flush()
        proposal.run_id = run.id
    else:
        ensure_baseline_version(session, run, user.email)

    reset_run_for_markdown_edit(session, run, proposal.proposed_markdown)
    create_draft_version(session, run, "proposal", user.email, proposal_id=proposal.id)
    page.draft_state = "Draft generated"
    proposal.status = "applied"
    proposal.updated_at = datetime.now(UTC)
    record_audit(session, user.email, "proposal.applied", "proposal", proposal.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.render_draft",
        run.id,
        actor=user.email,
        message="Draft preview rendering queued",
    )
    session.refresh(proposal)
    session.refresh(run)
    return ApplyProposalResponse(
        proposal=PageProposalRead.model_validate(proposal),
        run=PageEditRunRead.model_validate(run),
    )


@router.post("/proposals/{proposal_id}/reject", response_model=PageProposalRead)
def reject_proposal(
    proposal_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageProposalRead:
    """Reject a proposal without modifying any draft."""
    proposal = get_proposal_or_404(session, proposal_id)
    if proposal.status == "applied":
        raise HTTPException(status_code=409, detail="Applied proposals cannot be rejected")
    if proposal.task_id and proposal.status in ACTIVE_PROPOSAL_STATUSES:
        revoke_task(proposal.task_id)
        cancel_active_task_executions(
            session,
            job_id=proposal.id,
            message="Rejected by user",
        )
    proposal.status = "rejected"
    proposal.updated_at = datetime.now(UTC)
    record_audit(session, user.email, "proposal.rejected", "proposal", proposal.id)
    session.commit()
    session.refresh(proposal)
    return proposal


@router.post("/runs/{run_id}/draft-versions/{version_id}/restore", response_model=PageEditRunRead)
def restore_draft_version(
    run_id: str,
    version_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Restore a validated draft version and queue preview rendering."""
    run = get_run_or_404(session, run_id)
    version = session.get(DraftVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Draft version not found")
    if version.run_id != run_id:
        raise HTTPException(status_code=409, detail="Draft version belongs to another run")
    if run.status in {"cancelled", "published"}:
        raise HTTPException(status_code=409, detail="Run is no longer editable")
    if run.markdown_draft == version.markdown_draft:
        raise HTTPException(status_code=409, detail="Draft version is already current")

    reset_run_for_markdown_edit(session, run, version.markdown_draft)
    page = session.get(ConfluencePage, run.page_id)
    if page:
        page.draft_state = "Draft generated"
    create_draft_version(
        session,
        run,
        "restore",
        user.email,
        restored_from_version_id=version.id,
        allow_duplicate_latest=True,
    )
    record_audit(session, user.email, "draft.restored", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.render_draft",
        run.id,
        actor=user.email,
        message="Restored draft preview rendering queued",
    )
    session.refresh(run)
    return run


@router.post("/runs/{run_id}/preview", response_model=PageEditRunRead)
def render_preview(
    run_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Queue Confluence-calculated preview rendering in the worker."""
    run = get_run_or_404(session, run_id)
    if not run.generated_storage_xhtml:
        raise HTTPException(status_code=409, detail="Convert the draft before preview")
    run.status = "previewing"
    run.preview_status = "rendering"
    record_audit(session, user.email, "preview.requested", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.render_preview",
        run.id,
        actor=user.email,
        message="Preview rendering queued",
    )
    session.refresh(run)
    return run


@router.post("/runs/{run_id}/publish", response_model=PageEditRunRead)
def publish_run(
    run_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Queue publication after preview and drift checks have passed."""
    run = get_run_or_404(session, run_id)
    if run.preview_status != "ready":
        raise HTTPException(status_code=409, detail="A successful preview is required")
    run.status = "publishing"
    record_audit(session, user.email, "publish.requested", "page_edit_run", run.id)
    enqueue_task_for_job(
        session,
        run,
        "page_crafter.publish_page",
        run.id,
        actor=user.email,
        message="Publication queued",
    )
    session.refresh(run)
    return run


@router.post("/pages/{page_id}/reset", status_code=204)
def reset_page_draft(
    page_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> None:
    """Cancel all active runs for a page and delete all draft versions and artifacts."""
    page = get_active_page(session, page_id)

    active_runs = session.scalars(
        select(PageEditRun)
        .where(PageEditRun.page_id == page_id)
        .where(PageEditRun.status.not_in(["cancelled", "published"]))
    ).all()

    for run in active_runs:
        if run.task_id and run.status in ACTIVE_DRAFT_STATUSES:
            revoke_task(run.task_id)
            cancel_active_task_executions(session, job_id=run.id, message="Reset by user")
        session.execute(delete(DraftVersion).where(DraftVersion.run_id == run.id))
        session.execute(delete(DraftArtifact).where(DraftArtifact.run_id == run.id))
        run.status = "cancelled"
        run.markdown_draft = None
        run.generated_storage_xhtml = None
        run.preview_html = None
        run.diff_text = None
        run.error_message = None
        run.updated_at = datetime.now(UTC)

    page.draft_state = "Published"
    record_audit(session, user.email, "draft.reset", "confluence_page", str(page_id))
    session.commit()


@router.post("/runs/{run_id}/cancel", response_model=PageEditRunRead)
def cancel_page_edit_run(
    run_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = require_admin,
) -> PageEditRunRead:
    """Cancel an app-side draft and remove generated artifacts."""
    run = get_run_or_404(session, run_id)
    if run.task_id:
        revoke_task(run.task_id)
    run.status = "cancelled"
    cancel_active_task_executions(session, job_id=run.id, message="Cancelled by user")
    run.draft_status = "Published"
    run.preview_status = "not_started"
    run.markdown_draft = None
    run.generated_storage_xhtml = None
    run.preview_html = None
    run.diff_text = None
    session.execute(delete(DraftArtifact).where(DraftArtifact.run_id == run.id))
    page = session.get(ConfluencePage, run.page_id)
    if page:
        page.draft_state = "Published"
    record_audit(session, user.email, "draft.cancelled", "page_edit_run", run.id)
    session.commit()
    session.refresh(run)
    return run
