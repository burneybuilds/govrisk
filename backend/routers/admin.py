from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from auth.database import get_auth_db
from auth.models import AuditLog, User
from auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _log_to_response(log: AuditLog, db: Session) -> dict:
    actor = None
    if log.user_id:
        actor = db.query(User).filter(User.user_id == log.user_id).first()
    return {
        "id": log.id,
        "actorUserId": log.user_id,
        "actorName": actor.full_name if actor else log.user_id or "System",
        "action": log.action,
        "targetUserId": log.target_user_id,
        "details": log.details,
        "timestamp": log.timestamp.isoformat() if log.timestamp else "",
    }


@router.get("/audit-logs")
def get_audit_logs(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(
            (AuditLog.user_id == user_id) | (AuditLog.target_user_id == user_id)
        )

    total = query.count()
    total_pages = (total + limit - 1) // limit if total else 0
    logs = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [_log_to_response(l, db) for l in logs],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
    }