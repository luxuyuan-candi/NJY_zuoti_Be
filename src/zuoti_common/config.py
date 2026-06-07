from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    service_name: str = "zuoti-service"
    wechat_app_id: str = "wxb88840bf78c6cd4d"
    wechat_app_secret: str = ""
    token_signing_key: str = ""

    mysql_host: str = "zuoti-mysql"
    mysql_port: int = 3306
    mysql_database: str = "zuoti"
    mysql_user: str = ""
    mysql_password: str = ""

    redis_host: str = "zuoti-redis"
    redis_port: int = 6379
    redis_password: str = ""

    mongodb_host: str = "zuoti-mongodb"
    mongodb_port: int = 27017
    mongodb_database: str = "zuoti_questions"
    mongodb_user: str = ""
    mongodb_password: str = ""

    minio_endpoint: str = "zuoti-minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
