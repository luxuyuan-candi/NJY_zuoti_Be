from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.zuoti_common.app import create_app
from src.zuoti_common.clients import create_mysql_connection
from src.zuoti_common.schemas import FeedbackRequest
from src.zuoti_common.security import require_admin_token, require_bearer_token
from src.zuoti_common.users import get_user_by_openid, openid_from_token


router = APIRouter()
STATUS_LABELS = {
    "PENDING": "待处理",
    "RESOLVED": "已处理",
}


def require_super_admin_user(token: str) -> dict:
    user = get_user_by_openid(openid_from_token(token))
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin required")
    return user


def ensure_feedback_schema() -> None:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedbacks (
                  id VARCHAR(64) PRIMARY KEY,
                  user_id VARCHAR(64),
                  category VARCHAR(64) NOT NULL DEFAULT 'general',
                  content VARCHAR(500) NOT NULL,
                  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_feedback_user_id (user_id),
                  INDEX idx_feedback_created_at (created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )


def save_feedback(user_openid: str, payload: FeedbackRequest) -> dict:
    ensure_feedback_schema()
    feedback_id = f"feedback-{uuid4().hex[:16]}"
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feedbacks (id, user_id, category, content, status)
                VALUES (%s, %s, %s, %s, 'PENDING')
                """,
                (feedback_id, user_openid, payload.category, payload.content.strip()),
            )
    return get_feedback_by_id(feedback_id)


def get_feedback_by_id(feedback_id: str) -> dict:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, category, content, status, created_at
                FROM feedbacks f
                WHERE id = %s
                """,
                (feedback_id,),
            )
            row = cursor.fetchone()
    return format_feedback(row) if row else {}


def list_feedback_items() -> list[dict]:
    ensure_feedback_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, category, content, status, created_at
                FROM feedbacks
                ORDER BY created_at DESC, id DESC
                LIMIT 200
                """
            )
            rows = cursor.fetchall()
    return [format_feedback(row) for row in rows]


def format_feedback(row: dict) -> dict:
    status_code = (row.get("status") or "PENDING").upper()
    user_openid = row.get("user_id") or ""
    user = get_user_by_openid(user_openid) if user_openid else {}
    return {
        "id": row["id"],
        "userId": user_openid,
        "nickname": user.get("nickname") or "",
        "avatarUrl": user.get("avatarUrl") or "",
        "category": row.get("category") or "general",
        "content": row.get("content") or "",
        "status": status_code,
        "statusLabel": STATUS_LABELS.get(status_code, status_code),
        "createdAt": row.get("created_at").strftime("%Y-%m-%d %H:%M") if row.get("created_at") else "",
    }


@router.post("/api/miniapp/feedback")
def submit_feedback(payload: FeedbackRequest, token: str = Depends(require_bearer_token)):
    feedback = save_feedback(openid_from_token(token), payload)
    return {"success": True, "data": feedback}


@router.get("/api/miniapp/admin/feedback")
def list_miniapp_feedback(token: str = Depends(require_bearer_token)):
    require_super_admin_user(token)
    return {"success": True, "data": list_feedback_items()}


@router.get("/api/admin/feedback")
def list_feedback(_: str = Depends(require_admin_token)):
    return {"success": True, "data": list_feedback_items()}


ensure_feedback_schema()
app = create_app("feedback-service", [router])
