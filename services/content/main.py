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
PROMOTION_EBOOKS = [
    {
        "id": "ebook-01",
        "title": "医药商品购销员基础知识",
        "desc": "基础理论电子教材，适合入门复习与概念梳理。",
        "tag": "电子教材",
        "fileName": "1_医药商品购销员-基础知识.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-01-basic-knowledge.pdf",
    },
    {
        "id": "ebook-02",
        "title": "医药商品购销员初级",
        "desc": "初级岗位电子教材，覆盖基础业务知识与实务内容。",
        "tag": "电子教材",
        "fileName": "1_医药商品购销员-初级.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-02-primary.pdf",
    },
    {
        "id": "ebook-03",
        "title": "医药商品购销员综合训练习题集",
        "desc": "配套习题教材，适合章节练习后的巩固训练。",
        "tag": "习题教材",
        "fileName": "1_医药商品购销员职业资格知识与技能综合训练-习题集.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-03-workbook.pdf",
    },
    {
        "id": "ebook-04",
        "title": "医药商品购销员中级",
        "desc": "中级电子教材，适合进阶业务学习与考前梳理。",
        "tag": "电子教材",
        "fileName": "医药商品购销员（中级）.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-04-intermediate.pdf",
    },
    {
        "id": "ebook-05",
        "title": "医药商品购销员指南包课程包",
        "desc": "配套课程指南教材，便于按模块进行系统化学习。",
        "tag": "课程资料",
        "fileName": "医药商品购销员（指南包 课程包）.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-05-guide-course-pack.pdf",
    },
    {
        "id": "ebook-06",
        "title": "医药商品购销员高级",
        "desc": "高级电子教材，适合高阶岗位知识学习和综合复盘。",
        "tag": "电子教材",
        "fileName": "医药商品购销员（高级）.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-06-advanced.pdf",
    },
    {
        "id": "ebook-07",
        "title": "药品购销技术",
        "desc": "面向药品购销场景的专题教材，可作为业务拓展阅读。",
        "tag": "专题教材",
        "fileName": "药品购销技术.pdf",
        "objectName": "public-assets/docs/ebooks/ebook-07-pharma-sales-technique.pdf",
    },
]
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


def build_ebook_promotions() -> list[dict]:
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "desc": item["desc"],
            "tag": item["tag"],
            "fileName": item["fileName"],
            "fileType": "pdf",
            "fileUrl": asset_url(item["objectName"]),
        }
        for item in PROMOTION_EBOOKS
    ]


def build_home_videos() -> list[dict]:
    return [
        {
            "id": "video-01",
            "title": "首页与功能总览",
            "desc": "概览小程序首页入口、公告区和学习内容布局。",
            "duration": "00:16",
            "url": asset_url("public-assets/video/home-video-01-guide.mp4"),
            "coverUrl": asset_url("public-assets/images/home-video-01-guide.jpg"),
        },
        {
            "id": "video-02",
            "title": "题库练习与结果查看",
            "desc": "浏览题库入口、做题流程和练习结果页面内容。",
            "duration": "00:16",
            "url": asset_url("public-assets/video/home-video-02-practice.mp4"),
            "coverUrl": asset_url("public-assets/images/home-video-02-practice.jpg"),
        },
        {
            "id": "video-03",
            "title": "教材入口与学习资料",
            "desc": "查看首页电子教材入口和资料浏览方式。",
            "duration": "00:15",
            "url": asset_url("public-assets/video/home-video-03-ebook.mp4"),
            "coverUrl": asset_url("public-assets/images/home-video-03-ebook.jpg"),
        },
    ]


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
    videos = build_home_videos()
    return {
        "success": True,
        "data": {
            "video": videos[0],
            "videos": videos,
            "promotions": build_ebook_promotions(),
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
