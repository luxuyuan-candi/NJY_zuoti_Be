from fastapi import APIRouter, Depends, HTTPException, status

from src.zuoti_common.app import create_app
from src.zuoti_common.question_bank import (
    get_practice_set,
    list_chapters as list_bank_chapters,
    list_practice_sets,
)
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/banks")
def list_banks(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": list_practice_sets()}


@router.get("/api/miniapp/banks/{bank_id}/chapters")
def list_chapters(bank_id: str, _: str = Depends(require_bearer_token)):
    bank = get_practice_set(bank_id)
    if not bank:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bank not found")
    return {
        "success": True,
        "data": {
            "bank": bank,
            "chapters": list_bank_chapters(bank_id),
        },
    }


@router.get("/api/admin/banks")
def admin_list_banks(_: str = Depends(require_admin_token)):
    return {"success": True, "data": list_practice_sets()}


@router.get("/api/admin/banks/{bank_id}/chapters")
def admin_list_chapters(bank_id: str, _: str = Depends(require_admin_token)):
    bank = get_practice_set(bank_id)
    if not bank:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bank not found")
    return {
        "success": True,
        "data": {
            "bank": bank,
            "chapters": list_bank_chapters(bank_id),
        },
    }


app = create_app("bank-service", [router])
