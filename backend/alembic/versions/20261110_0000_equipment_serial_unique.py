"""Unique constraint on equipments.serial_number

The model already declares serial_number unique. The initial migration did not,
so two pieces of equipment could share a serial.

Revision ID: 003_equipment_serial
Revises: 002_booking_overlap
Create Date: 2026-11-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_equipment_serial"
down_revision: str | None = "002_booking_overlap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL unique allows multiple NULLs, so existing rows without a serial still insert.
    op.create_unique_constraint(
        "equipments_serial_number_key", "equipments", ["serial_number"]
    )


def downgrade() -> None:
    op.drop_constraint("equipments_serial_number_key", "equipments", type_="unique")
