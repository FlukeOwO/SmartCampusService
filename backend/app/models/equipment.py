"""
Equipment Model - อุปกรณ์ที่สามารถจองได้
"""

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.common.constants import EquipmentStatus
from app.core.database import Base


class Equipment(Base, TimestampMixin):
    """
    Equipment Model - เก็บข้อมูลอุปกรณ์
    
    Relationships:
        - bookings: การจองอุปกรณ์
    """

    __tablename__ = "equipments"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Equipment Information
    equipment_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="รหัสอุปกรณ์"
    )
    equipment_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="ชื่ออุปกรณ์"
    )
    equipment_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="ประเภทอุปกรณ์: projector, laptop, camera, etc.",
    )
    brand: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="ยี่ห้อ"
    )
    model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="รุ่น"
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, comment="Serial Number"
    )

    # Details
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="รายละเอียดอุปกรณ์"
    )
    specifications: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="สเปค (JSON object)"
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL รูปภาพอุปกรณ์"
    )

    # Location & Storage
    location: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="สถานที่เก็บอุปกรณ์"
    )
    responsible_staff: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="เจ้าหน้าที่ผู้ดูแล"
    )

    # Status & Availability
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EquipmentStatus.AVAILABLE.value,
        index=True,
        comment="สถานะอุปกรณ์: available, in_use, maintenance, broken, retired",
    )
    is_bookable: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="สามารถจองได้หรือไม่"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="จำนวนอุปกรณ์ (ถ้ามีหลายชิ้น)"
    )

    # Maintenance
    last_maintenance_date: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="วันที่ซ่อมบำรุงล่าสุด"
    )
    next_maintenance_date: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="วันที่ซ่อมบำรุงครั้งถัดไป"
    )

    # Relationships
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="equipment", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_equipments_status_bookable", "status", "is_bookable"),
        Index("ix_equipments_type_status", "equipment_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<Equipment(id={self.id}, code={self.equipment_code}, status={self.status})>"
