from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.risk_service import get_project_analytics
from auth.dependencies import get_current_user
from auth.models import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return get_project_analytics(db)
