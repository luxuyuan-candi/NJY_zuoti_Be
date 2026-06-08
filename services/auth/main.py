import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from src.zuoti_common.app import create_app
from src.zuoti_common.config import get_settings
from src.zuoti_common.schemas import LoginByCodeRequest
from src.zuoti_common.security import require_admin_token
from src.zuoti_common.users import ensure_user, token_for_openid

router = APIRouter()


@router.post("/api/miniapp/auth/login")
def miniapp_login(payload: LoginByCodeRequest):
    settings = get_settings()
    openid = code_to_openid(payload.code)
    user = ensure_user(openid, payload.nickname, payload.avatar_url)
    return {
        "success": True,
        "data": {
            "token": token_for_openid(openid),
            "user": user,
            "wechatAppId": settings.wechat_app_id,
        },
    }


def code_to_openid(code: str) -> str:
    settings = get_settings()
    if settings.app_env == "local" and not settings.wechat_app_secret:
        return f"mock-openid-{code[-6:]}"

    response = httpx.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params={
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=8,
    )
    data = response.json()
    if data.get("errcode") or not data.get("openid"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=data.get("errmsg") or "failed to get wechat openid",
        )
    return data["openid"]


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
