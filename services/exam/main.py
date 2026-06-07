from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.mock_data import PAPERS, QUESTION
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/exams/papers")
def papers(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": PAPERS}


@router.get("/api/admin/papers")
def admin_papers(_: str = Depends(require_admin_token)):
    return {"success": True, "data": PAPERS}


@router.post("/api/miniapp/exams/{paper_id}/start")
def start_exam(paper_id: str, _: str = Depends(require_bearer_token)):
    return {"success": True, "data": {"examRecordId": "exam-demo", "paperId": paper_id, "question": QUESTION}}


@router.post("/api/miniapp/exams/{exam_record_id}/submit")
def submit_exam(exam_record_id: str, _: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": {
            "examRecordId": exam_record_id,
            "score": 92,
            "accuracy": 92,
            "rank": {"weekly": 16, "total": 128},
        },
    }


app = create_app("exam-service", [router])
