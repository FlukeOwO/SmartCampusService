"""Booking overlap exclusion constraints (btree_gist)

ชั้นที่ 2 ของการกันจองซ้อน: ถ้ามีการจองที่ทับเวลากันหลุดมาถึง DB
PostgreSQL จะปฏิเสธด้วย exclusion_violation (SQLSTATE 23P01) ซึ่ง API แปลงเป็น 409

Revision ID: 002_booking_overlap
Revises: 001_initial
Create Date: 2026-10-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_booking_overlap"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE bookings ADD CONSTRAINT no_overlap_room
          EXCLUDE USING gist (room_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
          WHERE (room_id IS NOT NULL AND status IN ('pending', 'confirmed'))
        """
    )
    op.execute(
        """
        ALTER TABLE bookings ADD CONSTRAINT no_overlap_equipment
          EXCLUDE USING gist (equipment_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
          WHERE (equipment_id IS NOT NULL AND status IN ('pending', 'confirmed'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlap_equipment")
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlap_room")
