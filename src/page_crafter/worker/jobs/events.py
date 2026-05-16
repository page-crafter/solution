from sqlalchemy.orm import Session

from page_crafter.shared.models.jobs import JobEvent


def add_event(session: Session, job_id: str, message: str, level: str = "info") -> None:
    """Append a progress event for a worker job."""
    session.add(JobEvent(job_id=job_id, message=message, level=level))
