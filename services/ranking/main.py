from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.security import require_bearer_token

router = APIRouter()


@router.get("/api/miniapp/ranking/me")
def my_ranking(_: str = Depends(require_bearer_token)):
    return {"success": True, "data": {"total": 128, "weekly": 16, "currentScore": 2680}}


@router.get("/api/miniapp/ranking/leaderboard")
def leaderboard(_: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": [
            {"rank": 1, "name": "学习用户 A", "score": 3120},
            {"rank": 2, "name": "学习用户 B", "score": 2980},
            {"rank": 16, "name": "我", "score": 2680},
        ],
    }


@router.get("/api/miniapp/ranking/medals")
def medals(_: str = Depends(require_bearer_token)):
    return {
        "success": True,
        "data": [
            {"name": "连续学习", "desc": "连续学习 7 天获得"},
            {"name": "考试达人", "desc": "模拟考试达到 90 分获得"},
        ],
    }


app = create_app("ranking-service", [router])
