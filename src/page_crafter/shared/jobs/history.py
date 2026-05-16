from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from page_crafter.shared.models.jobs import TaskExecution

ACTIVE_STATUSES = ("queued", "running")


def record_task_queued(
    session: Session,
    *,
    job_id: str,
    task_name: str,
    task_id: str | None = None,
    actor: str = "system",
    message: str | None = None,
) -> TaskExecution:
    """Create a durable history entry when a worker task is queued."""
    execution = TaskExecution(
        job_id=job_id,
        task_id=task_id,
        task_name=task_name,
        actor=actor,
        status="queued",
        message=message,
    )
    session.add(execution)
    return execution


def start_task_execution(
    session: Session,
    *,
    job_id: str,
    task_name: str,
    task_id: str | None = None,
    message: str | None = None,
) -> TaskExecution:
    """Mark the newest queued task execution as running, creating it if needed."""
    execution = _find_active_execution(session, job_id=job_id, task_name=task_name)
    if execution is None:
        execution = record_task_queued(
            session,
            job_id=job_id,
            task_id=task_id,
            task_name=task_name,
            message=message,
        )

    now = datetime.utcnow()
    execution.status = "running"
    execution.task_id = task_id or execution.task_id
    execution.started_at = execution.started_at or now
    execution.updated_at = now
    if message:
        execution.message = message
    return execution


def finish_task_execution(
    session: Session,
    *,
    job_id: str,
    task_name: str,
    status: str,
    task_id: str | None = None,
    message: str | None = None,
) -> TaskExecution:
    """Mark a task execution as completed, failed, or otherwise terminal."""
    execution = _find_active_execution(session, job_id=job_id, task_name=task_name)
    if execution is None:
        execution = record_task_queued(
            session,
            job_id=job_id,
            task_id=task_id,
            task_name=task_name,
            message=message,
        )

    now = datetime.utcnow()
    execution.status = status
    execution.task_id = task_id or execution.task_id
    execution.started_at = execution.started_at or now
    execution.finished_at = now
    execution.updated_at = now
    if message:
        execution.message = message
    return execution


def cancel_active_task_executions(
    session: Session,
    *,
    job_id: str,
    message: str | None = None,
) -> list[TaskExecution]:
    """Cancel all active task executions for a job or page edit run."""
    now = datetime.utcnow()
    executions = session.scalars(
        select(TaskExecution)
        .where(TaskExecution.job_id == job_id)
        .where(TaskExecution.status.in_(ACTIVE_STATUSES))
        .order_by(TaskExecution.created_at.desc())
    ).all()
    for execution in executions:
        execution.status = "cancelled"
        execution.finished_at = now
        execution.updated_at = now
        if message:
            execution.message = message
    return list(executions)


def _find_active_execution(
    session: Session,
    *,
    job_id: str,
    task_name: str,
) -> TaskExecution | None:
    """Find the latest active execution for a concrete worker task."""
    return session.scalar(
        select(TaskExecution)
        .where(TaskExecution.job_id == job_id)
        .where(TaskExecution.task_name == task_name)
        .where(TaskExecution.status.in_(ACTIVE_STATUSES))
        .order_by(TaskExecution.created_at.desc())
    )
