"""Helper untuk mencatat ActivityLog dari router manapun."""

from sqlalchemy.orm import Session
from ..models import ActivityLog


def log_activity(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    description: str,
) -> None:
    db.add(ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    ))
