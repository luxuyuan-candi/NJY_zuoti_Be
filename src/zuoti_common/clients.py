from .config import get_settings


def create_mysql_connection():
    import pymysql

    settings = get_settings()
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def create_redis_client():
    import redis

    settings = get_settings()
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )


def create_mongodb_client():
    from pymongo import MongoClient

    settings = get_settings()
    auth = ""
    if settings.mongodb_user:
        auth = f"{settings.mongodb_user}:{settings.mongodb_password}@"
    uri = f"mongodb://{auth}{settings.mongodb_host}:{settings.mongodb_port}/{settings.mongodb_database}"
    return MongoClient(uri)


def create_minio_client():
    from minio import Minio

    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )
