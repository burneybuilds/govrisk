from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth.database import get_auth_db
from auth.audit import log_audit, ACTIONS
from models import Alert, Project
from schemas import AlertResponse, AlertStatusUpdate
from auth.dependencies import get_current_user, require_roles
from auth.models import User

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# Severity is free text on the server, so rank defensively and let anything
# unrecognised sort last rather than first.
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
_UNKNOWN_SEVERITY_RANK = len(_SEVERITY_RANK)


def _severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get((severity or "").strip().upper(), _UNKNOWN_SEVERITY_RANK)


def _is_resolved(alert: Alert) -> bool:
    return (alert.status or "ACTIVE").strip().upper() == "RESOLVED"


def _alert_to_response(a: Alert, project_name: str) -> dict:
    return {
        "id": a.id,
        "projectId": a.project_id,
        "projectName": project_name,
        "type": a.type,
        "severity": a.severity,
        "status": a.status,
        "detectedDate": a.detected_date,
        "description": a.description,
    }


@router.get("", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    alerts = db.query(Alert).all()
    # Resolve every project name in one query instead of one per alert.
    project_ids = {a.project_id for a in alerts}
    names = {
        p.id: p.name
        for p in db.query(Project).filter(Project.id.in_(project_ids)).all()
    } if project_ids else {}

    # An early-warning list is only useful if the most urgent warning is on top.
    # Row order from SQLite is insertion order, which left a MEDIUM alert from
    # July above a CRITICAL one from October. Three stable passes, cheapest
    # key last: unresolved first, then severity, then newest detected_date
    # (ISO strings, so reverse lexicographic is reverse chronological).
    alerts.sort(key=lambda a: a.detected_date or "", reverse=True)
    alerts.sort(key=lambda a: _severity_rank(a.severity))
    alerts.sort(key=lambda a: 1 if _is_resolved(a) else 0)

    return [_alert_to_response(a, names.get(a.project_id, "Unknown Project")) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    project = db.query(Project).filter(Project.id == alert.project_id).first()
    return _alert_to_response(alert, project.name if project else "Unknown Project")


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert_status(
    alert_id: str,
    data: AlertStatusUpdate,
    db: Session = Depends(get_db),
    db_auth: Session = Depends(get_auth_db),
    actor: User = Depends(require_roles("admin", "officer")),
):
    """Acknowledge (resolve) or reopen an early warning.

    Without this the "Resolved" tab was unreachable from the UI: nothing could
    ever move an alert into it, so the tab only ever showed whatever the seed
    script happened to write.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    previous = alert.status or "ACTIVE"
    alert.status = data.status
    db.add(alert)
    db.flush()

    log_audit(
        db_auth,
        actor,
        ACTIONS["ALERT_STATUS_CHANGED"],
        details=(
            f'Alert {alert.id} ({alert.type}, project {alert.project_id}) '
            f"{previous} -> {data.status}"
        ),
    )
    db_auth.commit()
    db.commit()
    db.refresh(alert)

    project = db.query(Project).filter(Project.id == alert.project_id).first()
    return _alert_to_response(alert, project.name if project else "Unknown Project")
