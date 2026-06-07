from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.config import get_settings
from src.zuoti_common.schemas import LoginByCodeRequest
from src.zuoti_common.security import require_admin_token

router = APIRouter()


@router.post("/api/miniapp/auth/login")
def miniapp_login(payload: LoginByCodeRequest):
    settings = get_settings()
    # The real implementation must call WeChat code2session with AppSecret from Secret.
    demo_openid = f"mock-openid-{payload.code[-6:]}"
    return {
        "success": True,
        "data": {
            "token": f"miniapp-demo-token-{payload.code[-6:]}",
            "user": {
                "id": "u-demo",
                "openid": demo_openid,
                "nickname": payload.nickname or "学习用户",
                "authorized": True,
            },
            "wechatAppId": settings.wechat_app_id,
        },
    }


@router.post("/api/admin/auth/login")
def admin_login():
    return {
        "success": True,
        "data": {
            "token": "admin-demo-token",
            "admin": {"id": "admin-demo", "name": "系统管理员"},
        },
    }


@router.post("/api/admin/auth/logout")
def admin_logout(_: str = Depends(require_admin_token)):
    return {"success": True, "message": "logged out"}


app = create_app("auth-service", [router])
