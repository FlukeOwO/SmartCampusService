"""
Configuration Management - Cloud-Ready Settings
ใช้ Pydantic Settings เพื่อโหลดค่าจาก Environment Variables
รองรับทั้ง Local Development และ Production บน GCP
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings - ดึงค่าจาก Environment Variables
    ใช้ 12-Factor App Principles เพื่อให้ Config แยกออกจาก Code
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    APP_NAME: str = "Smart Campus Service Platform"
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api/v1"

    # -------------------------------------------------------------------------
    # Server Settings
    # -------------------------------------------------------------------------
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="JWT Secret Key - ต้องมีความยาวอย่างน้อย 32 ตัวอักษร",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # -------------------------------------------------------------------------
    # Database Settings (PostgreSQL)
    # -------------------------------------------------------------------------
    POSTGRES_SERVER: str = Field(..., description="PostgreSQL Host")
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = Field(..., description="PostgreSQL Username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL Password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL Database Name")

    # Connection Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    @property
    def database_url(self) -> str:
        """
        สร้าง Database URL สำหรับ Async SQLAlchemy
        Format: postgresql+asyncpg://user:pass@host:port/db
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """
        Database URL สำหรับ Alembic Migrations (Sync)
        Format: postgresql://user:pass@host:port/db
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -------------------------------------------------------------------------
    # CORS Settings
    # -------------------------------------------------------------------------
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS Origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """แปลง comma-separated string เป็น list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # -------------------------------------------------------------------------
    # Storage Settings (Local vs Google Cloud Storage)
    # -------------------------------------------------------------------------
    STORAGE_PROVIDER: Literal["local", "gcs"] = "local"
    LOCAL_STORAGE_PATH: str = "/app/storage"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Google Cloud Storage Settings
    GCS_BUCKET_NAME: str = ""
    GCS_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    @property
    def max_upload_size_bytes(self) -> int:
        """แปลง MB เป็น Bytes"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # -------------------------------------------------------------------------
    # Logging Settings
    # -------------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "text"
    ENABLE_CLOUD_LOGGING: bool = False

    # -------------------------------------------------------------------------
    # Rate Limiting & Security
    # -------------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60
    ENABLE_SECURITY_HEADERS: bool = True

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    ENABLE_NOTIFICATIONS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = False

    # -------------------------------------------------------------------------
    # Cloud Run Specific Settings
    # -------------------------------------------------------------------------
    @property
    def is_cloud_run(self) -> bool:
        """ตรวจสอบว่ากำลังรันบน Google Cloud Run หรือไม่"""
        import os

        return os.getenv("K_SERVICE") is not None

    @property
    def is_production(self) -> bool:
        """ตรวจสอบว่าเป็น Production environment หรือไม่"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """ตรวจสอบว่าเป็น Development environment หรือไม่"""
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    """
    สร้าง Settings Instance (Singleton Pattern)
    ใช้ lru_cache เพื่อให้สร้างครั้งเดียวตลอดทั้ง Application Lifecycle
    """
    return Settings()


# Export settings instance
settings = get_settings()
