from fastapi import APIRouter, Depends, HTTPException, status

from src.zuoti_common.app import create_app
from src.zuoti_common.question_bank import (
    get_question_by_id,
    list_questions,
    serialize_question_detail,
    serialize_question_for_practice,
)
from src.zuoti_common.security import require_admin_token, require_bearer_token
from src.zuoti_common.users import require_learning_access

router = APIRouter()


@router.get("/api/miniapp/questions/{question_id}")
def get_question(question_id: str, token: str = Depends(require_bearer_token)):
    require_learning_access(token)
    row = get_question_by_id(question_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")
    return {"success": True, "data": serialize_question_detail(row)}


@router.get("/api/miniapp/questions/offline-packages/{bank_id}")
def offline_package(bank_id: str, token: str = Depends(require_bearer_token)):
    require_learning_access(token)
    return {
        "success": True,
        "data": {
            "bankId": bank_id,
            "version": "2026.06.09",
            "questions": [],
        },
    }


@router.get("/api/admin/questions")
def admin_questions(_: str = Depends(require_admin_token)):
    return {"success": True, "data": list_questions()}


app = create_app("question-service", [router])
