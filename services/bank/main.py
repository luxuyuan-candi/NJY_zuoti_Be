from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.mock_data import BANKS, CHAPTERS
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/banks")
def list_banks(_: str = Depends(require_bearer_token)):
    authorized_banks = [bank for bank in BANKS if bank["authorized"]]
    return {"success": True, "data": authorized_banks}


@router.get("/api/miniapp/banks/{bank_id}/chapters")
def list_chapters(bank_id: str, _: str = Depends(require_bearer_token)):
    return {"success": True, "data": {"bankId": bank_id, "chapters": CHAPTERS}}


@router.get("/api/admin/banks")
def admin_list_banks(_: str = Depends(require_admin_token)):
    return {"success": True, "data": BANKS}


@router.get("/api/admin/banks/{bank_id}/chapters")
def admin_list_chapters(bank_id: str, _: str = Depends(require_admin_token)):
    return {"success": True, "data": {"bankId": bank_id, "chapters": CHAPTERS}}


app = create_app("bank-service", [router])
