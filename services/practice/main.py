from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.zuoti_common.app import create_app
from src.zuoti_common.question_bank import build_practice_questions, verify_answer
from src.zuoti_common.security import require_bearer_token

router = APIRouter()


class StartPracticeRequest(BaseModel):
    bank_id: str = Field(min_length=1)
    chapter_key: str | None = None
    count: int = Field(default=20, ge=1, le=100)
    order: str = "SEQUENTIAL"


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: str


@router.post("/api/miniapp/practice/start")
def start_practice(payload: StartPracticeRequest, _: str = Depends(require_bearer_token)):
    questions = build_practice_questions(
        practice_set_id=payload.bank_id,
        chapter_key=payload.chapter_key,
        count=payload.count,
        order=payload.order,
    )
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no questions found for selection")
    return {
        "success": True,
        "data": {
            "practiceId": f"practice-{uuid4().hex[:12]}",
            "questionCount": len(questions),
            "questions": questions,
        },
    }


@router.post("/api/miniapp/practice/answers")
def submit_answer(payload: SubmitAnswerRequest, _: str = Depends(require_bearer_token)):
    result = verify_answer(payload.question_id, payload.answer)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")
    return {"success": True, "data": result}


@router.get("/api/miniapp/records")
def records(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": []}


@router.get("/api/miniapp/records/mistakes")
def mistakes(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": []}


@router.get("/api/miniapp/records/favorites")
def favorites(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": []}


app = create_app("practice-service", [router])
