from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: str | None,
    user_name: str | None,
    action: str,
    target_type: str,
    target_id: str,
    target_name: str = "",
    changes: list | None = None,
    snapshot_before: dict | None = None,
    snapshot_after: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        user_name=user_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        changes_json=changes,
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
    )
    db.add(entry)
    db.flush()
    return entry
