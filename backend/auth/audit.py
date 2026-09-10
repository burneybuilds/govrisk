from datetime import datetime, timezone
from sqlalchemy.orm import Session
from auth.models import AuditLog, User
from auth.security import generate_id


ACTIONS = {
    "USER_CREATED": "USER_CREATED",
    "USER_UPDATED": "USER_UPDATED",
    "ROLE_CHANGED": "ROLE_CHANGED",
    "USER_ACTIVATED": "USER_ACTIVATED",
    "USER_DEACTIVATED": "USER_DEACTIVATED",
    "PASSWORD_RESET": "PASSWORD_RESET",
    "PASSWORD_CHANGED": "PASSWORD_CHANGED",
    "LOGIN_SUCCESS": "LOGIN_SUCCESS",
    "LOGIN_FAILED": "LOGIN_FAILED",
    "LOGOUT": "LOGOUT",
    "REGISTERED": "REGISTERED",
    "PROJECT_CREATED": "PROJECT_CREATED",
    "PROJECT_UPDATED": "PROJECT_UPDATED",
    "PROJECT_UPDATE_ADDED": "PROJECT_UPDATE_ADDED",
}


def log_audit(
    db: Session,
    actor: User,
    action: str,
    target_user_id: str = None,
    details: str = None,
):
    entry = AuditLog(
        id=generate_id(),
        user_id=actor.user_id if actor else None,
        action=action,
        target_user_id=target_user_id,
        details=details,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry


def next_user_id(db: Session) -> str:
    highest = 0
    for u in db.query(User.user_id).all():
        uid = u[0] or ""
        if uid.startswith("USR-"):
            try:
                n = int(uid.split("-")[1])
                if n > highest:
                    highest = n
            except (ValueError, IndexError):
                continue
    return f"USR-{highest + 1:04d}"