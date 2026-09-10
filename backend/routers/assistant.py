from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import AssistantRequest, AssistantResponse
from services.risk_service import generate_assistant_response
from auth.dependencies import get_current_user
from auth.models import User

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("", response_model=AssistantResponse)
def query_assistant(request: AssistantRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    reply = generate_assistant_response(request.query, db)
    return AssistantResponse(reply=reply)
