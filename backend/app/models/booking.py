"""
Booking Model - การจองห้องและอุปกรณ์
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.common.constants import BookingStatus
from app.core.database import Base


class Booking(Base, TimestampMixin):
    """
    Booking Model - การจองห้องหรืออุปกรณ์
    
    Notes:
        - ต้องระบุ room_id หรือ equipment_id (อย่างใดอย่างหนึ่งหรือทั้งคู่)
        - มีระบบ Locking เพื่อป้องกัน Double Booking
    
    Relationships:
        - user: ผู้จอง
        - room: ห้องที่จอง (optional)
        - equipment: อุปกรณ์ที่จอง (optional)
    """

    __tablename__ = "bookings"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ผู้จอง",
    )
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ห้องที่จอง",
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="อุปกรณ์ที่จอง",
    )

    # Booking Details
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="หัวข้อการจอง"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="รายละเอียดการจอง/วัตถุประสงค์"
    )
    purpose: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="วัตถุประสงค์"
    )

    # Time Slot (ช่วงเวลาที่จอง)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="เวลาเริ่มต้น"
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="เวลาสิ้นสุด"
    )

    # Status & Approval
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BookingStatus.PENDING.value,
        index=True,
        comment="สถานะการจอง: pending, confirmed, cancelled, completed, rejected",
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ผู้อนุมัติการจอง (Staff/Admin)",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่อนุมัติ"
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="เหตุผลที่ปฏิเสธ"
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="เหตุผลที่ยกเลิก"
    )

    # Contact Information
    contact_person: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="ผู้ติดต่อ"
    )
    contact_phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="เบอร์โทรติดต่อ"
    )

    # Additional Info
    attendees_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="จำนวนผู้เข้าร่วม (สำหรับจองห้อง)"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="หมายเหตุเพิ่มเติม"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bookings")
    room: Mapped["Room"] = relationship("Room", back_populates="bookings")
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="bookings")

    # Constraints
    __table_args__ = (
        # ตรวจสอบว่า end_time > start_time
        CheckConstraint("end_time > start_time", name="check_booking_time_range"),
        # ต้องมี room_id หรือ equipment_id อย่างน้อย 1 อย่าง
        CheckConstraint(
            "room_id IS NOT NULL OR equipment_id IS NOT NULL",
            name="check_booking_target",
        ),
        # Composite Indexes สำหรับ Conflict Detection
        Index("ix_bookings_room_time", "room_id", "start_time", "end_time", "status"),
        Index("ix_bookings_equipment_time", "equipment_id", "start_time", "end_time", "status"),
        Index("ix_bookings_user_status", "user_id", "status"),
        Index("ix_bookings_status_time", "status", "start_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<Booking(id={self.id}, user_id={self.user_id}, "
            f"room_id={self.room_id}, equipment_id={self.equipment_id}, "
            f"status={self.status}, start={self.start_time})>"
        )

    @property
    def is_active(self) -> bool:
        """ตรวจสอบว่าการจองยังใช้งานอยู่หรือไม่"""
        return self.status in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]

    @property
    def is_modifiable(self) -> bool:
        """ตรวจสอบว่าสามารถแก้ไขการจองได้หรือไม่"""
        return self.status == BookingStatus.PENDING.value

    @property
    def duration_hours(self) -> float:
        """คำนวณระยะเวลาการจอง (ชั่วโมง)"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        return 0.0
