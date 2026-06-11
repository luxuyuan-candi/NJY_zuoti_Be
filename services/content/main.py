import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.zuoti_common.app import create_app
from src.zuoti_common.clients import create_mysql_connection
from src.zuoti_common.config import get_settings
from src.zuoti_common.security import require_admin_token, require_bearer_token
from src.zuoti_common.users import get_user_by_openid, openid_from_token


router = APIRouter()
HOME_NOTICE_KEY = "home_notice"
DEFAULT_NOTICE = {
    "title": "题库授权说明",
    "content": "用户完成微信登录后，需要由管理员授权题库后才可进行练习、考试和离线缓存。",
}


class NoticePayload(BaseModel):
    title: str
    content: str


def asset_url(path: str) -> str:
    settings = get_settings()
    return f"{settings.minio_public_base_url.rstrip('/')}/{path.lstrip('/')}"


def ensure_content_schema() -> None:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS home_contents (
                  content_key VARCHAR(64) PRIMARY KEY,
                  title VARCHAR(255) NOT NULL,
                  content TEXT NOT NULL,
                  updated_by VARCHAR(64),
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                INSERT INTO home_contents (content_key, title, content)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  title = title
                """,
                (HOME_NOTICE_KEY, DEFAULT_NOTICE["title"], DEFAULT_NOTICE["content"]),
            )


def get_notice_config() -> dict:
    ensure_content_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT content_key, title, content, updated_by, updated_at
                FROM home_contents
                WHERE content_key = %s
                """,
                (HOME_NOTICE_KEY,),
            )
            row = cursor.fetchone()
    if not row:
        return {
            "id": "notice-1",
            "title": DEFAULT_NOTICE["title"],
            "content": DEFAULT_NOTICE["content"],
            "marqueeText": f"{DEFAULT_NOTICE['title']}：{DEFAULT_NOTICE['content']}",
        }
    title = row.get("title") or DEFAULT_NOTICE["title"]
    content = row.get("content") or DEFAULT_NOTICE["content"]
    return {
        "id": "notice-1",
        "title": title,
        "content": content,
        "marqueeText": f"{title}：{content}",
        "updatedBy": row.get("updated_by") or "",
        "updatedAt": row.get("updated_at").strftime("%Y-%m-%d %H:%M") if row.get("updated_at") else "",
    }


def save_notice_config(openid: str, payload: NoticePayload) -> dict:
    ensure_content_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE home_contents
                SET title = %s,
                    content = %s,
                    updated_by = %s
                WHERE content_key = %s
                """,
                (payload.title.strip(), payload.content.strip(), openid, HOME_NOTICE_KEY),
            )
    return get_notice_config()


def require_super_admin_user(token: str) -> dict:
    user = get_user_by_openid(openid_from_token(token))
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin required")
    return user


@router.get("/api/miniapp/content/home")
def home_content():
    notice = get_notice_config()
    return {
        "success": True,
        "data": {
            "video": {
                "title": "南检院学习导览",
                "duration": "08:32",
                "url": asset_url("public-assets/video/zuoti-guide.mp4"),
                "coverUrl": asset_url("public-assets/images/video-cover.png"),
            },
            "promotions": [
                {
                    "id": "promo-1",
                    "title": "考前高效复习指南",
                    "tag": "备考方法",
                    "imageUrl": asset_url("public-assets/images/promo-review.png"),
                },
                {
                    "id": "promo-2",
                    "title": "课程学习巩固计划",
                    "tag": "课程学习",
                    "imageUrl": asset_url("public-assets/images/promo-course.png"),
                },
            ],
            "notices": [notice],
        },
    }


@router.get("/api/miniapp/content/notices/current")
def current_notice():
    return {"success": True, "data": get_notice_config()}


@router.get("/api/miniapp/admin/content/notice")
def admin_notice(token: str = Depends(require_bearer_token)):
    require_super_admin_user(token)
    return {"success": True, "data": get_notice_config()}


@router.put("/api/miniapp/admin/content/notice")
def update_notice(payload: NoticePayload, token: str = Depends(require_bearer_token)):
    user = require_super_admin_user(token)
    return {"success": True, "data": save_notice_config(user["openid"], payload)}


@router.get("/api/admin/content/home")
def admin_home_content(_: str = Depends(require_admin_token)):
    return home_content()


@router.get("/api/miniapp/files/{file_id}")
def miniapp_file(file_id: str):
    return {"success": True, "data": {"fileId": file_id, "url": asset_url(f"public-assets/files/{file_id}")}}


@router.post("/api/admin/files")
def admin_file_upload(_: str = Depends(require_admin_token)):
    return {"success": True, "data": {"fileId": "file-demo", "status": "uploaded"}}


ensure_content_schema()
app = create_app("content-service", [router])
