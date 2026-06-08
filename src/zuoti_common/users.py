import base64
import json
from io import BytesIO
from uuid import uuid4

from minio.error import S3Error

from .clients import create_minio_client, create_mysql_connection
from .config import get_settings


PUBLIC_BUCKET = "public-assets"


def token_for_openid(openid: str) -> str:
    return f"miniapp-openid:{openid}"


def openid_from_token(token: str) -> str:
    if token.startswith("miniapp-openid:"):
        return token.removeprefix("miniapp-openid:")
    if token.startswith("miniapp-demo-token-"):
        return f"mock-openid-{token[-6:]}"
    return token


def public_asset_url(object_name: str) -> str:
    settings = get_settings()
    return f"{settings.minio_public_base_url.rstrip('/')}/{PUBLIC_BUCKET}/{object_name.lstrip('/')}"


def ensure_user(openid: str, nickname: str | None = None, avatar_url: str | None = None) -> dict:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (id, openid, nickname, avatar_url, status)
                VALUES (%s, %s, %s, %s, 'AUTHORIZED')
                ON DUPLICATE KEY UPDATE
                  nickname = COALESCE(NULLIF(VALUES(nickname), ''), nickname),
                  avatar_url = COALESCE(NULLIF(VALUES(avatar_url), ''), avatar_url),
                  status = IF(status = 'REGISTERED', 'AUTHORIZED', status)
                """,
                (openid, openid, nickname or None, avatar_url or None),
            )
    return get_user_by_openid(openid)


def get_user_by_openid(openid: str) -> dict:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, openid, nickname, avatar_url, email, status, created_at, updated_at
                FROM users
                WHERE openid = %s
                """,
                (openid,),
            )
            user = cursor.fetchone()
    if not user:
        return ensure_user(openid)
    return format_user(user)


def update_user_profile(
    openid: str,
    nickname: str | None,
    email: str | None,
    avatar_url: str | None,
    avatar_base64: str | None,
    avatar_content_type: str | None,
    avatar_ext: str | None,
) -> dict:
    saved_avatar_url = avatar_url
    if avatar_base64:
        saved_avatar_url = save_avatar(openid, avatar_base64, avatar_content_type, avatar_ext)

    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET nickname = %s,
                    email = %s,
                    avatar_url = COALESCE(%s, avatar_url)
                WHERE openid = %s
                """,
                (nickname or None, email or None, saved_avatar_url or None, openid),
            )
    return get_user_by_openid(openid)


def save_avatar(openid: str, avatar_base64: str, content_type: str | None, avatar_ext: str | None) -> str:
    clean_base64 = avatar_base64.split(",", 1)[-1]
    data = base64.b64decode(clean_base64)
    ext = (avatar_ext or "jpg").strip(".").lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    resolved_content_type = content_type or ("image/png" if ext == "png" else "image/jpeg")
    object_name = f"users/{openid}/avatar-{uuid4().hex}.{ext}"

    client = create_minio_client()
    ensure_public_bucket(client)
    client.put_object(
        PUBLIC_BUCKET,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=resolved_content_type,
    )
    return public_asset_url(object_name)


def ensure_public_bucket(client) -> None:
    if not client.bucket_exists(PUBLIC_BUCKET):
        client.make_bucket(PUBLIC_BUCKET)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{PUBLIC_BUCKET}/*"],
            }
        ],
    }
    try:
        client.set_bucket_policy(PUBLIC_BUCKET, json.dumps(policy))
    except S3Error:
        pass


def format_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "openid": user["openid"],
        "nickname": user.get("nickname") or "",
        "avatarUrl": user.get("avatar_url") or "",
        "email": user.get("email") or "",
        "status": user.get("status") or "REGISTERED",
        "authorized": True,
        "rank": {"total": 128, "weekly": 16, "currentScore": 2680},
    }
