from celery import current_task
from sqlalchemy.orm import Session

from page_crafter.shared.jobs.history import finish_task_execution, start_task_execution
from page_crafter.shared.models.jobs import TaskExecution


def current_task_id() -> str | None:
    """Return the Celery task id when the code is running inside a worker task."""
    request = getattr(current_task, "request", None)
    task_id = getattr(request, "id", None)
    return str(task_id) if task_id else None


def mark_task_running(
    session: Session,
    *,
    job_id: str,
    task_name: str,
    message: str | None = None,
) -> TaskExecution:
    """Mark a worker task as running using the current Celery request id."""
    return start_task_execution(
        session,
        job_id=job_id,
        task_name=task_name,
        task_id=current_task_id(),
        message=message,
    )


def mark_task_finished(
    session: Session,
    *,
    job_id: str,
    task_name: str,
    status: str,
    message: str | None = None,
) -> TaskExecution:
    """Mark a worker task as terminal using the current Celery request id."""
    return finish_task_execution(
        session,
        job_id=job_id,
        task_name=task_name,
        task_id=current_task_id(),
        status=status,
        message=message,
    )
