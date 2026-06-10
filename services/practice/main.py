from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.zuoti_common.app import create_app
from src.zuoti_common.practice_records import (
    dismiss_mistake,
    ensure_practice_schema,
    get_global_mistake_detail,
    get_practice_record,
    get_record_mistake_detail,
    get_record_dashboard,
    list_global_mistakes,
    list_practice_trends,
    list_record_mistakes,
    save_practice_record,
)
from src.zuoti_common.question_bank import build_practice_questions, verify_answer
from src.zuoti_common.security import require_bearer_token
from src.zuoti_common.users import openid_from_token

router = APIRouter()


class StartPracticeRequest(BaseModel):
    bank_id: str = Field(min_length=1)
    chapter_key: str | None = None
    count: int = Field(default=20, ge=1, le=100)
    order: str = "SEQUENTIAL"


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: str


class CompletedQuestionPayload(BaseModel):
    questionId: str
    stem: str = ""
    chapter: str = ""
    selected: str = ""
    answer: str = ""
    correct: bool = False
    analysis: str = ""
    type: str = ""
    typeLabel: str = ""


class SavePracticeRecordRequest(BaseModel):
    type: str = "练习"
    title: str = "练习结果"
    bankId: str | None = None
    chapterKey: str | None = None
    answeredCount: int = Field(default=0, ge=0)
    correctCount: int = Field(default=0, ge=0)
    wrongCount: int = Field(default=0, ge=0)
    accuracy: int = Field(default=0, ge=0, le=100)
    details: list[dict] = Field(default_factory=list)
    retryConfig: dict | None = None
    questions: list[CompletedQuestionPayload] = Field(default_factory=list)


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


@router.post("/api/miniapp/records")
def save_record(payload: SavePracticeRecordRequest, token: str = Depends(require_bearer_token)):
    record = save_practice_record(openid_from_token(token), payload.model_dump())
    return {"success": True, "data": record}


@router.get("/api/miniapp/records")
def records(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": get_record_dashboard(openid_from_token(token))}


@router.get("/api/miniapp/records/mistakes")
def mistakes(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": list_global_mistakes(openid_from_token(token))}


@router.delete("/api/miniapp/records/mistakes/{mistake_id}")
def remove_mistake(mistake_id: str, token: str = Depends(require_bearer_token)):
    dismiss_mistake(openid_from_token(token), mistake_id)
    return {"success": True, "data": {"removed": True}}


@router.get("/api/miniapp/records/mistakes/{mistake_id}")
def mistake_detail(mistake_id: str, token: str = Depends(require_bearer_token)):
    detail = get_global_mistake_detail(openid_from_token(token), mistake_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mistake not found")
    return {"success": True, "data": detail}


@router.get("/api/miniapp/records/trends")
def trends(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": list_practice_trends(openid_from_token(token))}


@router.get("/api/miniapp/records/favorites")
def favorites(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": []}


@router.get("/api/miniapp/records/{record_id}")
def record_detail(record_id: str, token: str = Depends(require_bearer_token)):
    record = get_practice_record(openid_from_token(token), record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")
    return {"success": True, "data": record}


@router.get("/api/miniapp/records/{record_id}/mistakes")
def record_mistakes(record_id: str, token: str = Depends(require_bearer_token)):
    return {"success": True, "data": list_record_mistakes(openid_from_token(token), record_id)}


@router.get("/api/miniapp/records/mistake-items/{item_id}")
def record_mistake_detail(item_id: str, token: str = Depends(require_bearer_token)):
    detail = get_record_mistake_detail(openid_from_token(token), item_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record mistake not found")
    return {"success": True, "data": detail}


ensure_practice_schema()
app = create_app("practice-service", [router])
