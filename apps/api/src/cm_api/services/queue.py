from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from celery import Celery
from cm_shared.jobs.history import record_task_queued
from cm_shared.settings.app import get_settings
from sqlalchemy.orm import Session


def create_queue_client() -> Celery:
    """Create a Celery client used by the API to enqueue worker tasks."""
    settings = get_settings()
    return Celery("cm_api_queue", broker=settings.redis_url, backend=settings.redis_url)


queue_client = create_queue_client()


def enqueue_task(name: str, *args, celery_task_id: str | None = None, **kwargs) -> str:
    """Send a named task to the worker and return the Celery task id."""
    result = queue_client.send_task(name, args=args, kwargs=kwargs, task_id=celery_task_id)
    return str(result.id)


def enqueue_task_for_job(
    session: Session,
    job: Any,
    task_name: str,
    *task_args: Any,
    actor: str = "system",
    message: str | None = None,
    task_kwargs: dict[str, Any] | None = None,
) -> str:
    """Commit job/task metadata before dispatching so workers never race the API transaction."""
    task_id = str(uuid4())
    job.task_id = task_id
    execution = record_task_queued(
        session,
        job_id=job.id,
        task_id=task_id,
        task_name=task_name,
        actor=actor,
        message=message,
    )
    session.flush()
    session.commit()
    try:
        enqueue_task(task_name, *task_args, celery_task_id=task_id, **(task_kwargs or {}))
    except Exception as exc:  # noqa: BLE001
        error_message = f"Failed to enqueue worker task: {exc}"
        if hasattr(job, "status"):
            job.status = "failed"
        if hasattr(job, "message"):
            job.message = error_message
        if hasattr(job, "error_message"):
            job.error_message = error_message
        now = datetime.now(UTC)
        execution.status = "failed"
        execution.message = error_message
        execution.finished_at = now
        execution.updated_at = now
        session.commit()
        raise
    return task_id


def revoke_task(task_id: str) -> None:
    """Ask Celery to revoke a queued or running task."""
    queue_client.control.revoke(task_id, terminate=True)
