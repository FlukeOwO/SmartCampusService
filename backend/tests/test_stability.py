"""Regression tests for the review findings that are enforceable in-process."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import TimeoutError as SATimeout

from app.common.storage import content_disposition
from app.core.config import Settings, settings
from app.core.database import AsyncSessionLocal, get_db
from app.main import app
from app.models import Equipment
from seed import assert_demo_seed_allowed
from tests.conftest import API, auth

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_default_upload_limits_fit_under_cloud_run():
    fields = Settings.model_fields
    per_file = fields["MAX_UPLOAD_SIZE_MB"].default
    files = fields["MAX_FILES_PER_REQUEST"].default
    total = fields["MAX_UPLOAD_TOTAL_MB"].default
    assert files * per_file <= total
    assert total < 32
    assert settings.max_upload_total_bytes < 32 * 1024 * 1024


def test_content_disposition_escapes_filename():
    header = content_disposition('รายงาน "ปลายภาค".png\r\nX-Evil: 1')
    assert "\r" not in header
    assert "\n" not in header
    assert header.startswith("inline; ")
    # The quoted ASCII fallback cannot close the header early, and Thai text is percent-encoded.
    assert header.count('"') == 2
    assert "filename*=UTF-8''" in header
    assert "%E0" in header


def test_demo_seed_refused_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    with pytest.raises(SystemExit):
        assert_demo_seed_allowed()


def test_demo_seed_allowed_for_local_dev(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    assert assert_demo_seed_allowed() is True


async def test_pool_timeout_is_503(client, student):
    async def boom():
        raise SATimeout("QueuePool limit reached, connection timed out")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = boom
    try:
        resp = await client.get(f"{API}/auth/me", headers=auth(student))
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 503, resp.text
    assert resp.headers.get("retry-after") == "3"
    assert "busy" in resp.json()["message"].lower()


async def test_duplicate_equipment_serial_rejected():
    async with AsyncSessionLocal() as db:
        db.add(
            Equipment(
                equipment_code="SN-A",
                equipment_name="Camera A",
                equipment_type="camera",
                status="available",
                is_bookable=True,
                quantity=1,
                serial_number="SN-SHARED",
            )
        )
        db.add(
            Equipment(
                equipment_code="SN-B",
                equipment_name="Camera B",
                equipment_type="camera",
                status="available",
                is_bookable=True,
                quantity=1,
                serial_number="SN-SHARED",
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()


async def test_null_serial_numbers_are_allowed():
    async with AsyncSessionLocal() as db:
        db.add(
            Equipment(
                equipment_code="SN-C",
                equipment_name="Camera C",
                equipment_type="camera",
                status="available",
                is_bookable=True,
                quantity=1,
                serial_number=None,
            )
        )
        db.add(
            Equipment(
                equipment_code="SN-D",
                equipment_name="Camera D",
                equipment_type="camera",
                status="available",
                is_bookable=True,
                quantity=1,
                serial_number=None,
            )
        )
        await db.commit()
