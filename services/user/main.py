from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.schemas import AuthorizationRequest
from src.zuoti_common.security import require_admin_token, require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/user/me")
def me(_: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": {
            "id": "u-demo",
            "openid": "mock-openid",
            "nickname": "学习用户",
            "status": "AUTHORIZED",
            "authorized": True,
            "rank": {"total": 128, "weekly": 16, "currentScore": 2680},
        },
    }


@router.get("/api/admin/users")
def list_users(_: str = Depends(require_admin_token)):
    return {
        "success": True,
        "data": [
            {
                "id": "u-demo",
                "nickname": "学习用户",
                "openid": "mock-openid",
                "status": "AUTHORIZED",
                "authorizedBanks": ["bank-exam-1", "bank-course-1"],
            }
        ],
    }


@router.post("/api/admin/users/authorizations")
def upsert_authorization(payload: AuthorizationRequest, _: str = Depends(require_admin_token)):
    return {"success": True, "data": payload.model_dump()}


app = create_app("user-service", [router])
