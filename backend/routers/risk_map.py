from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Project
from auth.dependencies import get_current_user
from auth.models import User

router = APIRouter(prefix="/api/risk-map", tags=["risk-map"])


@router.get("")
def get_risk_map_data(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    projects = db.query(Project).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "state": p.state,
            "riskScore": p.risk_score,
            "riskLevel": p.risk_level,
            "costOverrunProbability": p.cost_overrun_probability,
            "delayProbability": p.delay_probability,
            "lat": p.lat,
            "lng": p.lng,
        }
        for p in projects
        if p.lat is not None and p.lng is not None and not (p.lat == 0 and p.lng == 0)
    ]
