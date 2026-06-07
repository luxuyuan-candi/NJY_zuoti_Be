from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.security import require_admin_token

router = APIRouter()


@router.get("/api/admin/dashboard")
def dashboard(_: str = Depends(require_admin_token)):
    return {
        "success": True,
        "data": {
            "bankCount": 2,
            "registeredUsers": 1,
            "authorizedUsers": 1,
            "todayQuestions": 126,
            "examCount": 3,
            "pendingFeedback": 1,
        },
    }


@router.get("/api/admin/settings")
def settings(_: str = Depends(require_admin_token)):
    return {
        "success": True,
        "data": {
            "mistakeAutoRemoveCorrectTimes": 3,
            "offlineCacheEnabled": True,
            "defaultAuthorizationScope": "BANK",
        },
    }


@router.get("/api/admin/statistics")
def statistics(_: str = Depends(require_admin_token)):
    return {
        "success": True,
        "data": {
            "questionTrend": [64, 72, 76, 81, 84],
            "examScoreTrend": [82, 86, 92],
            "mistakeCount": 2,
        },
    }


app = create_app("admin-service", [router])
