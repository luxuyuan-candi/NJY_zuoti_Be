from fastapi import APIRouter, Depends

from src.zuoti_common.app import create_app
from src.zuoti_common.security import require_admin_token

router = APIRouter()


@router.get("/api/miniapp/content/home")
def home_content():
    return {
        "success": True,
        "data": {
            "video": {
                "title": "南检院学习导览",
                "duration": "08:32",
                "coverUrl": "/api/miniapp/files/demo/video-cover",
            },
            "promotions": [
                {"id": "promo-1", "title": "考前高效复习指南", "tag": "备考方法"},
                {"id": "promo-2", "title": "课程学习巩固计划", "tag": "课程学习"},
            ],
            "notices": [{"id": "notice-1", "title": "题库授权说明"}],
        },
    }


@router.get("/api/admin/content/home")
def admin_home_content(_: str = Depends(require_admin_token)):
    return home_content()


@router.get("/api/miniapp/files/{file_id}")
def miniapp_file(file_id: str):
    return {"success": True, "data": {"fileId": file_id, "url": f"/api/miniapp/files/{file_id}"}}


@router.post("/api/admin/files")
def admin_file_upload(_: str = Depends(require_admin_token)):
    return {"success": True, "data": {"fileId": "file-demo", "status": "uploaded"}}


app = create_app("content-service", [router])
