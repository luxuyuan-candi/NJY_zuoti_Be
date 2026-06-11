from fastapi import APIRouter, Depends, Query

from src.zuoti_common.app import create_app
from src.zuoti_common.ranking import ensure_ranking_schema, get_ranking_summary, list_leaderboard, list_user_medals
from src.zuoti_common.security import require_bearer_token
from src.zuoti_common.users import openid_from_token


router = APIRouter()


@router.get("/api/miniapp/ranking/me")
def my_ranking(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": get_ranking_summary(openid_from_token(token))}


@router.get("/api/miniapp/ranking/leaderboard")
def leaderboard(
    scope: str = Query(default="total", pattern="^(total|weekly)$"),
    token: str = Depends(require_bearer_token),
):
    return {"success": True, "data": list_leaderboard(scope, openid_from_token(token))}


@router.get("/api/miniapp/ranking/medals")
def medals(token: str = Depends(require_bearer_token)):
    return {"success": True, "data": list_user_medals(openid_from_token(token))}


ensure_ranking_schema()
app = create_app("ranking-service", [router])
