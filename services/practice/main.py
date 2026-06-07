from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.zuoti_common.app import create_app
from src.zuoti_common.mock_data import FAVORITES, MISTAKES, QUESTION, RECORDS
from src.zuoti_common.security import require_bearer_token

router = APIRouter()


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: str


@router.post("/api/miniapp/practice/start")
def start_practice(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": {"practiceId": "practice-demo", "question": QUESTION}}


@router.post("/api/miniapp/practice/answers")
def submit_answer(payload: SubmitAnswerRequest, _: str = Depends(require_bearer_token)):
    correct = payload.answer == QUESTION["answer"]
    return {
        "success": True,
        "data": {
            "questionId": payload.question_id,
            "correct": correct,
            "answer": QUESTION["answer"],
            "analysis": QUESTION["analysis"],
        },
    }


@router.get("/api/miniapp/records")
def records(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": RECORDS}


@router.get("/api/miniapp/records/mistakes")
def mistakes(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": MISTAKES}


@router.get("/api/miniapp/records/favorites")
def favorites(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": FAVORITES}


app = create_app("practice-service", [router])
