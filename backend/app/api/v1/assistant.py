"""Grounded AI assistant endpoints."""
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.request import Request
from app.services.request_service import assert_can_view
from app.services.assistant.service import answer_question, get_suggested_questions

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AskBody(BaseModel):
    request_id: int
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v.strip()


@router.post("/ask", summary="Ask a grounded question about a request")
def ask(
    body: AskBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return answer_question(db, user, body.request_id, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied.")


@router.get("/suggested-questions", summary="Get role-specific suggested questions for a request")
def suggested_questions(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = db.get(Request, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    assert_can_view(user, req)

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    questions = get_suggested_questions(db, req, role_str)
    return {
        "questions": questions,
        "role": role_str,
        "request_id": request_id,
    }
