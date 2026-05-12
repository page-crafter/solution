from cm_shared.models.jobs import AuditEvent
from sqlalchemy.orm import Session


def record_audit(
    session: Session,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    detail: str | None = None,
) -> None:
    """Append an audit event for a user or worker action."""
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
