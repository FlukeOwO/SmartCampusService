"""
Configuration - อ่านค่าทั้งหมดจาก Environment Variables (12-factor)
ค่าลับ (POSTGRES_PASSWORD, SECRET_KEY) บน Cloud Run มาจาก Secret Manager
"""

import os
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"
    DEBUG: bool = False
    APP_NAME: str = "Smart Campus Service Platform"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    # None = เปิด Swagger ทุก environment ยกเว้น production
    ENABLE_DOCS: bool | None = None

    # -------------------------------------------------------------------------
    # Security / JWT
    # -------------------------------------------------------------------------
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12
    LOGIN_RATE_LIMIT: str = "5/minute"
    RATE_LIMIT_ENABLED: bool = True

    # -------------------------------------------------------------------------
    # Database (PostgreSQL / Cloud SQL private IP)
    # -------------------------------------------------------------------------
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    # Cloud SQL ตั้ง ssl-mode=ENCRYPTED_ONLY จึงต้องใช้ "require" บน cloud
    DB_SSL: Literal["disable", "require"] = "disable"
    DB_POOL_SIZE: int = 3
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_STATEMENT_TIMEOUT_MS: int = 30000
    DB_ECHO: bool = False

    # -------------------------------------------------------------------------
    # HTTP
    # -------------------------------------------------------------------------
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    # Host ที่ยอมรับ (TrustedHostMiddleware) เช่น campus-api-xxxx.asia-southeast1.run.app
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = ["*"]

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_csv(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # -------------------------------------------------------------------------
    # Storage (local สำหรับ dev, gcs สำหรับ cloud)
    # -------------------------------------------------------------------------
    STORAGE_PROVIDER: Literal["local", "gcs"] = "local"
    LOCAL_STORAGE_PATH: str = "/app/storage"
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_FILES_PER_REQUEST: int = 5
    GCS_BUCKET_NAME: str = ""
    GCS_PROJECT_ID: str = ""
    SIGNED_URL_EXPIRE_MINUTES: int = 15

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "text"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def db_connect_args(self) -> dict:
        args: dict = {
            "server_settings": {
                "timezone": "UTC",
                "statement_timeout": str(self.DB_STATEMENT_TIMEOUT_MS),
            }
        }
        if self.DB_SSL == "require":
            args["ssl"] = "require"
        return args

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return not self.is_production

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_cloud_run(self) -> bool:
        return os.getenv("K_SERVICE") is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
