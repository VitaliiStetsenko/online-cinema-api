"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    database_url: str
    database_sync_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Public URLs
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    # Abuse protection
    auth_rate_limit: str = "5/minute"

    # Email
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str

    # Redis
    redis_url: str

    # Celery
    celery_broker_url: str
    celery_result_backend: str

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "avatars"
    minio_secure: bool = False

    # App
    app_title: str = "Online Cinema"
    app_version: str = "1.0.0"
    debug: bool = False


settings = Settings()  # type: ignore[call-arg]
