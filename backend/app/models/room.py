"""
Room Model - ห้องเรียนและห้องประชุม
"""

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.common.constants import RoomStatus, RoomType
from app.core.database import Base


class Room(Base, TimestampMixin):
    """
    Room Model - เก็บข้อมูลห้องต่าง ๆ
    
    Relationships:
        - bookings: การจองห้อง
    """

    __tablename__ = "rooms"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Room Information
    room_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="เลขห้อง"
    )
    room_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="ชื่อห้อง"
    )
    room_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RoomType.CLASSROOM.value,
        index=True,
        comment="ประเภทห้อง: classroom, meeting_room, laboratory, etc.",
    )

    # Location
    building: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="ชื่ออาคาร"
    )
    floor: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="ชั้น"
    )

    # Capacity & Facilities
    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, comment="จำนวนที่นั่ง"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="รายละเอียดห้อง"
    )
    facilities: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="เครื่องมือและอุปกรณ์ในห้อง (JSON array)"
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL รูปภาพห้อง"
    )

    # Status & Availability
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RoomStatus.AVAILABLE.value,
        index=True,
        comment="สถานะห้อง: available, in_use, maintenance, closed",
    )
    is_bookable: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="สามารถจองได้หรือไม่"
    )

    # Relationships
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="room", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_rooms_status_bookable", "status", "is_bookable"),
        Index("ix_rooms_building_floor", "building", "floor"),
        Index("ix_rooms_type_status", "room_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<Room(id={self.id}, room_number={self.room_number}, status={self.status})>"
