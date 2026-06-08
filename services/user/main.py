from fastapi import APIRouter, Depends, HTTPException, status

from src.zuoti_common.app import create_app
from src.zuoti_common.schemas import AuthorizationRequest, UpdateUserProfileRequest, UpdateUserRoleRequest
from src.zuoti_common.security import require_admin_token, require_bearer_token
from src.zuoti_common.users import get_user_by_openid, list_users_for_manager, openid_from_token, update_user_profile, update_user_role

router = APIRouter()


@router.get("/api/miniapp/user/me")
def me(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": get_user_by_openid(openid_from_token(token))}


@router.put("/api/miniapp/user/me")
def update_me(payload: UpdateUserProfileRequest, token: str = Depends(require_bearer_token)):
    user = update_user_profile(
        openid=openid_from_token(token),
        nickname=payload.nickname,
        email=payload.email,
        avatar_url=payload.avatar_url,
        avatar_base64=payload.avatar_base64,
        avatar_content_type=payload.avatar_content_type,
        avatar_ext=payload.avatar_ext,
    )
    return {"success": True, "data": user}


@router.get("/api/miniapp/users")
def list_miniapp_users(token: str = Depends(require_bearer_token)):
    try:
        users = list_users_for_manager(openid_from_token(token))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return {"success": True, "data": users}


@router.put("/api/miniapp/users/{openid}/role")
def update_miniapp_user_role(
    openid: str,
    payload: UpdateUserRoleRequest,
    token: str = Depends(require_bearer_token),
):
    try:
        user = update_user_role(openid_from_token(token), openid, payload.role)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return {"success": True, "data": user}


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
