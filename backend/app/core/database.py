"""
Database Configuration - Async SQLAlchemy 2.0 Setup
ใช้ Async Engine เพื่อประสิทธิภาพสูงสุด พร้อมรองรับ Cloud SQL
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ============================================================================
# SQLAlchemy Base Class
# ============================================================================


class Base(DeclarativeBase):
    """
    Base class สำหรับ SQLAlchemy Models
    ใช้ DeclarativeBase จาก SQLAlchemy 2.0
    """

    pass


# ============================================================================
# Database Engine Configuration
# ============================================================================


def get_engine_config() -> dict[str, Any]:
    """
    สร้าง Engine Configuration ตาม Environment
    
    Returns:
        Dictionary ของ Engine configuration parameters
    """
    config = {
        "url": settings.database_url,
        "echo": settings.DB_ECHO,  # แสดง SQL queries ใน log (สำหรับ debug)
        "pool_pre_ping": True,  # ตรวจสอบ connection ก่อนใช้งาน
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,  # Recycle connections ทุก 1 ชั่วโมง
    }

    # สำหรับ Cloud SQL บน GCP ใช้ NullPool (Cloud SQL Proxy จัดการ pooling เอง)
    if settings.is_cloud_run:
        config["poolclass"] = pool.NullPool

    return config


# สร้าง Async Engine
engine: AsyncEngine = create_async_engine(**get_engine_config())


# ============================================================================
# Session Factory
# ============================================================================

# สร้าง Session Maker สำหรับ Async Sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ไม่ expire objects หลัง commit
    autoflush=False,  # ไม่ auto flush ก่อน query
    autocommit=False,  # ต้อง commit manual
)


# ============================================================================
# Database Session Dependency
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency สำหรับ Database Session
    ใช้ context manager เพื่อจัดการ lifecycle ของ Session
    
    Yields:
        AsyncSession: Database session
    
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Auto commit ถ้าไม่มี error
        except Exception:
            await session.rollback()  # Rollback ถ้ามี error
            raise
        finally:
            await session.close()


# ============================================================================
# Database Initialization & Health Check
# ============================================================================


async def init_db() -> None:
    """
    สร้าง Database Tables (ใช้สำหรับ Development/Testing)
    ใน Production ควรใช้ Alembic Migration แทน
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """
    ตรวจสอบ Database Connection สำหรับ Health Check Endpoint
    
    Returns:
        True ถ้า connection สำเร็จ, False ถ้าล้มเหลว
    """
    try:
        from sqlalchemy import text
        
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def close_db_connection() -> None:
    """
    ปิด Database Engine (Graceful Shutdown)
    ควรเรียกใน Application Shutdown Event
    """
    await engine.dispose()


# ============================================================================
# Database Events (PostgreSQL Optimizations)
# ============================================================================


@event.listens_for(engine.sync_engine, "connect")
def set_postgresql_pragma(dbapi_conn, connection_record):
    """
    ตั้งค่า PostgreSQL Connection Parameters
    เพิ่ม Performance และ Reliability
    """
    cursor = dbapi_conn.cursor()
    # ตั้งค่า statement timeout (30 วินาที)
    cursor.execute("SET statement_timeout = '30s'")
    # ตั้งค่า timezone เป็น UTC
    cursor.execute("SET timezone = 'UTC'")
    cursor.close()


# ============================================================================
# Transaction Helper Functions
# ============================================================================


async def execute_in_transaction(session: AsyncSession, func, *args, **kwargs):
    """
    Execute function ภายใน Transaction
    Auto rollback ถ้ามี error
    
    Args:
        session: AsyncSession
        func: Async function ที่จะรัน
        *args, **kwargs: Arguments สำหรับ function
    
    Returns:
        ผลลัพธ์จาก function
    
    Example:
        result = await execute_in_transaction(
            db, 
            create_booking,
            booking_data=data
        )
    """
    try:
        async with session.begin():
            result = await func(*args, **kwargs)
        return result
    except Exception as e:
        await session.rollback()
        raise e
