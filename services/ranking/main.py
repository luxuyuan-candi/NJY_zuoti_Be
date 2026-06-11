from fastapi import APIRouter, Depends, Query

from src.zuoti_common.app import create_app
from src.zuoti_common.ranking import ensure_ranking_schema, get_ranking_summary, list_leaderboard
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
def medals(_: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": [
            {"name": "连续学习", "desc": "连续学习 7 天获得"},
            {"name": "考试达人", "desc": "模拟考试达到 90 分获得"},
        ],
    }


ensure_ranking_schema()
app = create_app("ranking-service", [router])
