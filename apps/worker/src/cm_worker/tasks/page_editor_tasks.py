from datetime import datetime

from cm_shared.db.session import SessionLocal
from cm_shared.models.confluence import ConfluencePage
from cm_shared.models.page_editor import DraftArtifact, PageProposal, PageEditRun
from cm_worker.celery_app import celery_app
from cm_worker.confluence.preview import preview_has_rendered_content, render_storage_preview
from cm_worker.confluence.publish import publish_generated_page
from cm_worker.jobs.events import add_event
from cm_worker.page_editor.convert_markdown import convert_markdown_to_storage
from cm_worker.page_editor.diffing import build_markdown_diff, build_storage_diff
from cm_worker.page_editor.generate_markdown import generate_markdown_draft
from cm_worker.page_editor.proposals import propose_markdown_update
from cm_worker.rag.lightrag import sync_pages_to_lightrag
from cm_worker.tasks.history import mark_task_finished, mark_task_running


def get_run_and_page(session, run_id: str) -> tuple[PageEditRun, ConfluencePage] | None:
    """Fetch a page edit run and its target page for worker task execution."""
    run = session.get(PageEditRun, run_id)
    if run is None:
        return None
    page = session.get(ConfluencePage, run.page_id)
    if page is None:
        return None
    return run, page


def get_proposal(session, proposal_id: str) -> PageProposal | None:
    """Fetch an proposal for worker task execution."""
    return session.get(PageProposal, proposal_id)


def render_draft_artifacts(session, run: PageEditRun, page: ConfluencePage) -> None:
    """Convert the current Markdown draft and render its Confluence preview."""
    if not run.markdown_draft:
        raise ValueError("Markdown draft is empty")

    run.diff_text = None
    run.generated_storage_xhtml = None
    run.preview_html = None
    run.preview_status = "not_started"
    run.error_message = None
    run.status = "converting"
    run.draft_status = "Draft generated"
    run.updated_at = datetime.utcnow()
    page.draft_state = "Draft generated"
    session.commit()

    storage = convert_markdown_to_storage(run.markdown_draft)
    run.generated_storage_xhtml = storage
    run.diff_text = build_storage_diff(page.source_storage_xhtml, storage)
    run.status = "previewing"
    run.preview_status = "rendering"
    run.updated_at = datetime.utcnow()
    session.add(DraftArtifact(run_id=run.id, artifact_type="storage_xhtml", content=storage))
    add_event(session, run.id, "Draft converted to Confluence Storage XHTML")
    session.commit()

    preview_html = render_storage_preview(storage, page.confluence_id)
    if not preview_has_rendered_content(preview_html):
        raise ValueError("Confluence preview returned empty rendered content")
    run.preview_html = preview_html
    run.preview_status = "ready"
    run.status = "preview_ready"
    run.draft_status = "Preview ready"
    run.updated_at = datetime.utcnow()
    page.draft_state = "Preview ready"
    session.add(DraftArtifact(run_id=run.id, artifact_type="preview_html", content=preview_html))
    add_event(session, run.id, "Confluence preview is ready")


@celery_app.task(name="cm_worker.generate_markdown")
def generate_markdown(run_id: str) -> None:
    """Generate a Markdown draft and render its Confluence preview."""
    task_name = "cm_worker.generate_markdown"
    with SessionLocal() as session:
        result = get_run_and_page(session, run_id)
        if result is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Page edit run or source page not found",
            )
            session.commit()
            return
        run, page = result
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Generating Markdown draft",
        )
        run.status = "generating"
        add_event(session, run_id, "Generating Markdown draft")
        session.commit()
        try:
            markdown = generate_markdown_draft(session, run, page)
            run.markdown_draft = markdown
            session.add(DraftArtifact(run_id=run.id, artifact_type="markdown", content=markdown))
            add_event(session, run_id, "Markdown draft generated")
            render_draft_artifacts(session, run, page)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message="Markdown draft generated and preview rendered",
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.draft_status = "Publish blocked"
            run.preview_status = "failed"
            run.error_message = str(exc)
            page.draft_state = "Publish blocked"
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.render_draft")
def render_draft(run_id: str) -> None:
    """Render the current Markdown draft after manual edits."""
    task_name = "cm_worker.render_draft"
    with SessionLocal() as session:
        result = get_run_and_page(session, run_id)
        if result is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Page edit run or source page not found",
            )
            session.commit()
            return
        run, page = result
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Rendering draft preview",
        )
        add_event(session, run_id, "Rendering draft preview")
        session.commit()
        try:
            render_draft_artifacts(session, run, page)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message="Draft preview rendered",
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.preview_status = "failed"
            run.draft_status = "Publish blocked"
            run.error_message = str(exc)
            page.draft_state = "Publish blocked"
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.propose_markdown_update")
def propose_markdown_update_task(proposal_id: str) -> None:
    """Generate a Markdown proposal without changing the draft."""
    task_name = "cm_worker.propose_markdown_update"
    with SessionLocal() as session:
        proposal = get_proposal(session, proposal_id)
        if proposal is None:
            mark_task_finished(
                session,
                job_id=proposal_id,
                task_name=task_name,
                status="failed",
                message="Proposal not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=proposal_id,
            task_name=task_name,
            message="Generating Markdown proposal",
        )
        proposal.status = "generating"
        proposal.error_message = None
        proposal.updated_at = datetime.utcnow()
        add_event(session, proposal_id, "Generating Markdown proposal")
        session.commit()
        try:
            proposal_draft = propose_markdown_update(proposal.base_markdown, proposal.instruction)
            proposal.proposed_markdown = proposal_draft["markdown"]
            proposal.summary = proposal_draft["summary"]
            proposal.diff_text = build_markdown_diff(
                proposal.base_markdown,
                proposal_draft["markdown"],
            )
            proposal.status = "ready"
            proposal.updated_at = datetime.utcnow()
            add_event(session, proposal_id, "Markdown proposal is ready")
            mark_task_finished(
                session,
                job_id=proposal_id,
                task_name=task_name,
                status="completed",
                message="Markdown proposal generated",
            )
        except Exception as exc:  # noqa: BLE001
            proposal.status = "failed"
            proposal.error_message = str(exc)
            proposal.updated_at = datetime.utcnow()
            add_event(session, proposal_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=proposal_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.convert_markdown")
def convert_markdown(run_id: str) -> None:
    """Convert a Markdown draft to Confluence Storage XHTML."""
    task_name = "cm_worker.convert_markdown"
    with SessionLocal() as session:
        result = get_run_and_page(session, run_id)
        if result is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Page edit run or source page not found",
            )
            session.commit()
            return
        run, page = result
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Converting Markdown draft",
        )
        run.status = "converting"
        session.commit()
        try:
            if not run.markdown_draft:
                raise ValueError("Markdown draft is empty")
            storage = convert_markdown_to_storage(run.markdown_draft)
            run.generated_storage_xhtml = storage
            run.diff_text = build_storage_diff(page.source_storage_xhtml, storage)
            run.status = "converted"
            run.error_message = None
            run.updated_at = datetime.utcnow()
            page.draft_state = "Draft generated"
            session.add(
                DraftArtifact(run_id=run.id, artifact_type="storage_xhtml", content=storage)
            )
            add_event(session, run_id, "Draft converted to Confluence Storage XHTML")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message="Draft converted to Confluence Storage XHTML",
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.draft_status = "Publish blocked"
            run.error_message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.render_preview")
def render_preview(run_id: str) -> None:
    """Render a Confluence-calculated preview for generated Storage XHTML."""
    task_name = "cm_worker.render_preview"
    with SessionLocal() as session:
        result = get_run_and_page(session, run_id)
        if result is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Page edit run or source page not found",
            )
            session.commit()
            return
        run, page = result
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Rendering Confluence preview",
        )
        run.status = "previewing"
        run.preview_status = "rendering"
        session.commit()
        try:
            if not run.generated_storage_xhtml:
                raise ValueError("Generated XHTML is empty")
            preview_html = render_storage_preview(run.generated_storage_xhtml, page.confluence_id)
            if not preview_has_rendered_content(preview_html):
                raise ValueError("Confluence preview returned empty rendered content")
            run.preview_html = preview_html
            run.preview_status = "ready"
            run.status = "preview_ready"
            run.draft_status = "Preview ready"
            run.error_message = None
            run.updated_at = datetime.utcnow()
            page.draft_state = "Preview ready"
            session.add(
                DraftArtifact(run_id=run.id, artifact_type="preview_html", content=preview_html)
            )
            add_event(session, run_id, "Confluence preview is ready")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message="Confluence preview is ready",
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.preview_status = "failed"
            run.draft_status = "Publish blocked"
            run.error_message = str(exc)
            page.draft_state = "Publish blocked"
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.publish_page")
def publish_page(run_id: str) -> None:
    """Publish the reviewed draft to Confluence after final checks."""
    task_name = "cm_worker.publish_page"
    with SessionLocal() as session:
        result = get_run_and_page(session, run_id)
        if result is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Page edit run or source page not found",
            )
            session.commit()
            return
        run, page = result
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Publishing generated page",
        )
        run.status = "publishing"
        session.commit()
        try:
            publish_generated_page(session, run, page)
            run.updated_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.draft_status = "Publish blocked"
            run.error_message = str(exc)
            page.draft_state = "Publish blocked"
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
            session.commit()
            return

        task_status = "completed"
        event_level = "info"
        if run.status == "published":
            try:
                add_event(session, run_id, "Submitting published page to LightRAG")
                lightrag_result = sync_pages_to_lightrag([page], clear_existing=False)
                run.error_message = None
                message = (
                    f"Published page and submitted {lightrag_result.submitted_count} "
                    f"LightRAG document"
                )
                if lightrag_result.skipped_count:
                    message = f"{message}, skipped {lightrag_result.skipped_count}"
            except Exception as exc:  # noqa: BLE001
                task_status = "failed"
                event_level = "error"
                message = f"Published page, but LightRAG sync failed: {exc}"
                run.error_message = message
        else:
            message = f"Publish finished with status {run.status}"

        add_event(session, run_id, message, level=event_level)
        mark_task_finished(
            session,
            job_id=run_id,
            task_name=task_name,
            status=task_status,
            message=message,
        )
        session.commit()
