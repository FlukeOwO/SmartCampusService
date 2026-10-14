"""
Database - SQLAlchemy 2.0 async engine + session ต่อ request

กติกา transaction:
- get_db เปิด session หนึ่งตัวต่อหนึ่ง request และ rollback ถ้ามี error
- Service commit ครั้งเดียวตอนจบ use case (ห้ามเปิด session.begin() ซ้อน)
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Cloud Run ต่อ Cloud SQL ผ่าน private IP ตรง ๆ (ไม่มี proxy คอย pool ให้)
# จึงใช้ pool เล็ก ๆ ต่อ instance: pool_size + max_overflow คือเพดาน connection ต่อ instance
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args=settings.db_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db_connection() -> None:
    await engine.dispose()
