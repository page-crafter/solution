from datetime import datetime

from cm_shared.confluence.move_validation import ensure_move_stays_in_space
from cm_shared.db.session import SessionLocal
from cm_shared.models.confluence import ConfluencePage, DocumentChunk
from cm_shared.models.jobs import SyncRun
from sqlalchemy import delete, select

from cm_worker.celery_app import celery_app
from cm_worker.confluence.client import ConfluenceClient
from cm_worker.jobs.events import add_event
from cm_worker.rag.lightrag import (
    LightRagClient,
    delete_pages_from_lightrag,
    lightrag_file_source,
    pages_missing_from_lightrag,
    sync_pages_to_lightrag,
)
from cm_worker.sync.fetch_pages import (
    index_page,
    sync_space_pages,
    upsert_page,
    upsert_page_with_status,
)
from cm_worker.tasks.history import mark_task_finished, mark_task_running


def refresh_tree_metadata(session, client: ConfluenceClient) -> None:
    """Refresh parent/order metadata without rebuilding page embeddings."""
    tree = client.scan_space_page_tree()
    pages = session.scalars(
        select(ConfluencePage).where(ConfluencePage.deleted_at.is_(None))
    ).all()
    for page in pages:
        node = tree.get(page.confluence_id)
        if node is None:
            continue
        parent_id, sort_order = node
        page.parent_confluence_id = parent_id
        page.sort_order = sort_order


@celery_app.task(name="cm_worker.scheduled_sync")
def scheduled_sync() -> str:
    """Create and execute a scheduled full-space sync run."""
    task_name = "cm_worker.scheduled_sync"
    with SessionLocal() as session:
        run = SyncRun(status="queued")
        session.add(run)
        session.flush()
        mark_task_running(
            session,
            job_id=run.id,
            task_name=task_name,
            message="Starting scheduled full-space sync",
        )
        session.commit()
        sync_space(run.id)
        mark_task_finished(
            session,
            job_id=run.id,
            task_name=task_name,
            status="completed",
            message=f"Scheduled sync created run {run.id}",
        )
        session.commit()
        return run.id


@celery_app.task(name="cm_worker.sync_space")
def sync_space(run_id: str) -> None:
    """Sync the configured Confluence space and submit documents to LightRAG."""
    task_name = "cm_worker.sync_space"
    with SessionLocal() as session:
        run = session.get(SyncRun, run_id)
        if run is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Sync run not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message="Starting Confluence space sync",
        )
        run.status = "running"
        run.started_at = datetime.utcnow()
        add_event(session, run_id, "Starting Confluence space sync")
        session.commit()
        try:
            sync_result = sync_space_pages(session)
            lightrag_client = LightRagClient()
            existing_sources = lightrag_client.file_sources()
            missing_pages = pages_missing_from_lightrag(
                sync_result.unchanged_pages,
                existing_sources,
            )
            pages_to_submit = [*sync_result.changed_pages, *missing_pages]
            deleted_lightrag_docs = delete_pages_from_lightrag(
                sync_result.deleted_pages,
                client=lightrag_client,
            )
            add_event(
                session,
                run_id,
                "Submitting changed or missing pages to LightRAG",
            )
            lightrag_result = sync_pages_to_lightrag(
                pages_to_submit,
                clear_existing=False,
                client=lightrag_client,
            )
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.message = (
                f"Synced {sync_result.page_count} pages, skipped "
                f"{len(sync_result.unchanged_pages) - len(missing_pages)} unchanged "
                f"LightRAG documents, submitted {lightrag_result.submitted_count}, "
                f"and deleted {deleted_lightrag_docs}"
            )
            add_event(session, run_id, run.message)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message=run.message,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.refresh_page")
def refresh_page(run_id: str, page_id: int) -> None:
    """Refresh a single local page from Confluence and submit it to LightRAG."""
    task_name = "cm_worker.refresh_page"
    with SessionLocal() as session:
        run = session.get(SyncRun, run_id)
        page = session.get(ConfluencePage, page_id)
        if run is None or page is None or page.deleted_at is not None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Refresh run or page not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message=f"Refreshing page {page.title}",
        )
        run.status = "running"
        add_event(session, run_id, f"Refreshing page {page.title}")
        session.commit()
        try:
            client = ConfluenceClient()
            payload = client.get_page(page.confluence_id)
            result = upsert_page_with_status(
                session,
                payload,
            )
            refreshed = result.page
            lightrag_client = LightRagClient()
            source_exists = lightrag_file_source(refreshed) in lightrag_client.file_sources()
            _chunk_count = index_page(session, refreshed)
            pages_to_submit = [refreshed] if result.content_changed or not source_exists else []
            lightrag_result = sync_pages_to_lightrag(
                pages_to_submit,
                clear_existing=False,
                client=lightrag_client,
            )
            run.status = "completed"
            run.message = (
                f"Refreshed page and submitted "
                f"{lightrag_result.submitted_count} LightRAG document"
            )
            add_event(session, run_id, run.message)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message=run.message,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.create_empty_page")
def create_empty_page(run_id: str, title: str, parent_id: str | None = None) -> None:
    """Create a blank Confluence page and sync its local placeholder record."""
    task_name = "cm_worker.create_empty_page"
    with SessionLocal() as session:
        run = session.get(SyncRun, run_id)
        if run is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Create page run not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message=f"Creating empty page {title}",
        )
        run.status = "running"
        add_event(session, run_id, f"Creating empty page {title}")
        session.commit()
        try:
            client = ConfluenceClient()
            created = client.create_empty_page(title, parent_id)
            payload = client.get_page(str(created["id"]))
            page = upsert_page(session, payload)
            page.is_placeholder = True
            refresh_tree_metadata(session, client)
            _chunk_count = index_page(session, page)
            lightrag_result = sync_pages_to_lightrag([page], clear_existing=False)
            run.status = "completed"
            run.message = (
                f"Created empty page and submitted "
                f"{lightrag_result.submitted_count} LightRAG document"
            )
            add_event(session, run_id, run.message)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message=run.message,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.delete_page")
def delete_page(run_id: str, page_id: int) -> None:
    """Delete a page from Confluence and remove local vector data."""
    task_name = "cm_worker.delete_page"
    with SessionLocal() as session:
        run = session.get(SyncRun, run_id)
        page = session.get(ConfluencePage, page_id)
        if run is None or page is None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Delete run or page not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message=f"Deleting page {page.title}",
        )
        run.status = "running"
        session.commit()
        try:
            client = ConfluenceClient()
            client.delete_page(page.confluence_id)
            session.execute(delete(DocumentChunk).where(DocumentChunk.page_id == page.id))
            deleted_lightrag_docs = delete_pages_from_lightrag([page])
            page.deleted_at = datetime.utcnow()
            refresh_tree_metadata(session, client)
            run.status = "completed"
            run.message = (
                "Deleted page, removed local vector data, "
                f"and deleted {deleted_lightrag_docs} LightRAG document"
            )
            add_event(session, run_id, run.message)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message=run.message,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()


@celery_app.task(name="cm_worker.move_page")
def move_page(run_id: str, page_id: int, target_id: str, position: str = "append") -> None:
    """Move a Confluence page under, before, or after another page."""
    task_name = "cm_worker.move_page"
    with SessionLocal() as session:
        run = session.get(SyncRun, run_id)
        page = session.get(ConfluencePage, page_id)
        if run is None or page is None or page.deleted_at is not None:
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message="Move run or page not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=run_id,
            task_name=task_name,
            message=f"Moving page {page.title}",
        )
        run.status = "running"
        session.commit()
        try:
            target = session.scalar(
                select(ConfluencePage)
                .where(ConfluencePage.confluence_id == target_id)
                .where(ConfluencePage.deleted_at.is_(None))
            )
            ensure_move_stays_in_space(page, target)
            client = ConfluenceClient()
            client.move_page(page.confluence_id, target_id, position)
            upsert_page(
                session,
                client.get_page(page.confluence_id),
            )
            refresh_tree_metadata(session, client)
            run.status = "completed"
            run.message = "Moved page"
            add_event(session, run_id, run.message)
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="completed",
                message=run.message,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.message = str(exc)
            add_event(session, run_id, str(exc), level="error")
            mark_task_finished(
                session,
                job_id=run_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
        session.commit()
