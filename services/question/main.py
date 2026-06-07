from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.mock_data import QUESTION
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/questions/{question_id}")
def get_question(question_id: str, _: str = Depends(require_bearer_token)):
    return {"success": True, "data": {**QUESTION, "id": question_id}}


@router.get("/api/miniapp/questions/offline-packages/{bank_id}")
def offline_package(bank_id: str, _: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": {
            "bankId": bank_id,
            "version": "2026.06.07",
            "questions": [QUESTION],
        },
    }


@router.get("/api/admin/questions")
def admin_questions(_: str = Depends(require_admin_token)):
    return {"success": True, "data": [QUESTION]}


app = create_app("question-service", [router])
