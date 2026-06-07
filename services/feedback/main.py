from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.schemas import FeedbackRequest
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.post("/api/miniapp/feedback")
def submit_feedback(payload: FeedbackRequest, _: str = Depends(require_bearer_token)):
    return {"success": True, "data": {"id": "feedback-demo", **payload.model_dump(), "status": "PENDING"}}


@router.get("/api/admin/feedback")
def list_feedback(_: str = Depends(require_admin_token)):
    return {
        "success": True,
        "data": [
            {"id": "feedback-demo", "content": "希望增加更多练习题", "category": "general", "status": "PENDING"}
        ],
    }


app = create_app("feedback-service", [router])
