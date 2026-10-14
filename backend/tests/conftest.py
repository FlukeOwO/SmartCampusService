"""
Test fixtures - ต้องมี PostgreSQL จริง (exclusion constraint / FOR UPDATE ใช้ SQLite ไม่ได้)
CI ใช้ service container postgres:15, เครื่อง dev ใช้ docker compose up db
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
# ใช้ DB แยกเสมอ: fixture ด้านล่าง DROP SCHEMA ทิ้งทั้งก้อน ห้ามชี้ไปที่ DB ใช้งานจริง
os.environ["POSTGRES_DB"] = os.environ.get("TEST_POSTGRES_DB", "test")
if "test" not in os.environ["POSTGRES_DB"]:
    raise RuntimeError("TEST_POSTGRES_DB must contain 'test' - the test suite wipes the schema")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("LOCAL_STORAGE_PATH", "/tmp/smart-campus-test-storage")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.common.constants import UserRole  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Equipment, Room, User  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
API = settings.API_PREFIX
TABLES = "notifications, request_attachments, requests, bookings, equipments, rooms, users"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """ล้าง schema แล้วรัน alembic upgrade head ครั้งเดียว (ทดสอบ migration ไปด้วย)"""
    import asyncio

    async def reset():
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset())
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    # connection ผูกกับ event loop ของแต่ละ test จึงคืน pool ทุกครั้ง
    await engine.dispose()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def make_user(role: UserRole = UserRole.STUDENT, email: str | None = None) -> User:
    async with AsyncSessionLocal() as db:
        user = User(
            email=email or f"{role.value}-{os.urandom(4).hex()}@test.dev",
            hashed_password=get_password_hash("password123"),
            full_name=f"Test {role.value}",
            role=role.value,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


@pytest.fixture
async def student():
    return await make_user(UserRole.STUDENT)


@pytest.fixture
async def student2():
    return await make_user(UserRole.STUDENT)


@pytest.fixture
async def staff():
    return await make_user(UserRole.STAFF)


@pytest.fixture
async def admin():
    return await make_user(UserRole.ADMIN)


@pytest.fixture
async def room():
    async with AsyncSessionLocal() as db:
        obj = Room(
            room_number="T101",
            room_name="Test room",
            room_type="classroom",
            building="T",
            floor=1,
            capacity=30,
            status="available",
            is_bookable=True,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj


@pytest.fixture
async def equipment():
    async with AsyncSessionLocal() as db:
        obj = Equipment(
            equipment_code="EQ001",
            equipment_name="Projector",
            equipment_type="projector",
            status="available",
            is_bookable=True,
            quantity=1,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj
