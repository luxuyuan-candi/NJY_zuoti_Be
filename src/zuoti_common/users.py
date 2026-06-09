import base64
import json
from io import BytesIO
from urllib.parse import urlparse
from uuid import uuid4

from minio.error import S3Error

from .clients import create_minio_client, create_mysql_connection
from .config import get_settings


PUBLIC_BUCKET = "public-assets"
ROLE_LABELS = {
    "GUEST": "游客",
    "USER": "普通用户",
    "ADMIN": "管理员",
    "SUPER_ADMIN": "超级管理员",
}
MANAGER_ROLES = {"ADMIN", "SUPER_ADMIN"}


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
                INSERT INTO users (id, openid, nickname, avatar_url, role, status)
                VALUES (%s, %s, %s, %s, 'GUEST', 'AUTHORIZED')
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
                SELECT id, openid, nickname, avatar_url, email, role, status, created_at, updated_at
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
    current_user = get_user_by_openid(openid)
    previous_avatar_url = current_user.get("avatarUrl") or ""
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
    updated_user = get_user_by_openid(openid)
    if avatar_base64:
        delete_replaced_avatar(previous_avatar_url, updated_user.get("avatarUrl") or "", openid)
    return updated_user


def list_users_for_manager(manager_openid: str) -> list[dict]:
    manager = get_user_by_openid(manager_openid)
    if manager["role"] not in MANAGER_ROLES:
        raise PermissionError("user role cannot manage users")

    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, openid, nickname, avatar_url, email, role, status, created_at, updated_at
                FROM users
                ORDER BY updated_at DESC, created_at DESC
                """
            )
            users = cursor.fetchall()
    return [format_user(user) for user in users]


def update_user_role(manager_openid: str, target_openid: str, role: str) -> dict:
    manager = get_user_by_openid(manager_openid)
    manager_role = manager["role"]
    normalized_role = normalize_role(role)

    if manager_role not in MANAGER_ROLES:
        raise PermissionError("user role cannot manage users")
    if manager_openid == target_openid:
        raise PermissionError("cannot change current user role")
    if manager_role == "ADMIN" and normalized_role not in {"GUEST", "USER"}:
        raise PermissionError("admin can only assign guest or normal user roles")
    if manager_role == "SUPER_ADMIN" and normalized_role == "SUPER_ADMIN":
        raise PermissionError("super admin role must be maintained out of band")

    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET role = %s
                WHERE openid = %s
                """,
                (normalized_role, target_openid),
            )
    return get_user_by_openid(target_openid)


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


def delete_replaced_avatar(previous_avatar_url: str, current_avatar_url: str, openid: str) -> None:
    if not previous_avatar_url or previous_avatar_url == current_avatar_url:
        return

    object_name = extract_avatar_object_name(previous_avatar_url, openid)
    if not object_name:
        return

    client = create_minio_client()
    try:
        client.remove_object(PUBLIC_BUCKET, object_name)
    except S3Error:
        pass


def extract_avatar_object_name(avatar_url: str, openid: str) -> str | None:
    settings = get_settings()
    public_prefix = f"{settings.minio_public_base_url.rstrip('/')}/{PUBLIC_BUCKET}/"
    if not avatar_url.startswith(public_prefix):
        return None

    object_name = avatar_url.removeprefix(public_prefix).lstrip("/")
    parsed = urlparse(f"https://placeholder/{object_name}")
    normalized_object_name = parsed.path.lstrip("/")
    expected_prefix = f"users/{openid}/avatar-"
    if not normalized_object_name.startswith(expected_prefix):
        return None
    return normalized_object_name


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
    role = normalize_role(user.get("role") or "USER")
    return {
        "id": user["id"],
        "openid": user["openid"],
        "nickname": user.get("nickname") or "",
        "avatarUrl": user.get("avatar_url") or "",
        "email": user.get("email") or "",
        "role": role,
        "roleLabel": ROLE_LABELS[role],
        "status": user.get("status") or "REGISTERED",
        "authorized": True,
        "rank": {"total": 128, "weekly": 16, "currentScore": 2680},
    }


def normalize_role(role: str) -> str:
    normalized = (role or "USER").strip().upper()
    aliases = {
        "VISITOR": "GUEST",
        "NORMAL": "USER",
        "NORMAL_USER": "USER",
        "SUPERADMIN": "SUPER_ADMIN",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in ROLE_LABELS:
        return "USER"
    return normalized
