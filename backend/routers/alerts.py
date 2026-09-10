from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Alert, Project
from schemas import AlertResponse
from auth.dependencies import get_current_user
from auth.models import User

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _alert_to_response(a: Alert, db: Session) -> dict:
    project = db.query(Project).filter(Project.id == a.project_id).first()
    project_name = project.name if project else "Unknown Project"
    return {
        "id": a.id,
        "projectId": a.project_id,
        "projectName": project_name,
        "type": a.type,
        "severity": a.severity,
        "detectedDate": a.detected_date,
        "description": a.description,
    }


@router.get("", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    alerts = db.query(Alert).all()
    return [_alert_to_response(a, db) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_to_response(alert, db)
