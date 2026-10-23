"""
Audit event logger — append-only, never update or delete.
"""
from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent, AuditEventType


def log_event(
    db: Session,
    event_type: AuditEventType,
    *,
    actor_id: int | None = None,
    request_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    summary: str | None = None,
    ip_address: str | None = None,
    auto_flush: bool = True,
) -> AuditEvent:
    """Create and persist an audit event. Call before db.commit()."""
    event = AuditEvent(
        actor_id=actor_id,
        request_id=request_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        change_summary=summary,
        ip_address=ip_address,
    )
    db.add(event)
    if auto_flush:
        db.flush()
    return event
