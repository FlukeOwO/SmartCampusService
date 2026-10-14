"""
Request Model - คำร้อง/การแจ้งปัญหา
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.common.constants import RequestPriority, RequestStatus, RequestType
from app.core.database import Base


class Request(Base, TimestampMixin):
    """
    Request Model - คำร้อง/การแจ้งปัญหา

    Relationships:
        - user: ผู้ส่งคำร้อง
        - assigned_staff: เจ้าหน้าที่ที่รับผิดชอบ
        - attachments: ไฟล์แนบ
    """

    __tablename__ = "requests"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ผู้ส่งคำร้อง",
    )
    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="เจ้าหน้าที่ที่รับผิดชอบ",
    )

    # Request Information
    request_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="เลขที่คำร้อง (auto-generated)"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="หัวข้อคำร้อง")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="รายละเอียดคำร้อง")
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default=RequestType.OTHER.value,
        comment="ประเภทคำร้อง: maintenance, complaint, inquiry, other",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RequestPriority.MEDIUM.value,
        index=True,
        comment="ระดับความสำคัญ: low, medium, high, urgent",
    )

    # Location & Contact
    location: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="สถานที่เกิดปัญหา/ที่ตั้ง"
    )
    contact_phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="เบอร์โทรติดต่อ"
    )

    # Status & Progress
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RequestStatus.PENDING.value,
        index=True,
        comment="สถานะ: pending, in_progress, completed, rejected, cancelled",
    )
    status_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="หมายเหตุสถานะ")

    # Timestamps
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่มอบหมายงาน"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่เริ่มดำเนินการ"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่เสร็จสิ้น"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่แก้ไขปัญหาเสร็จ"
    )

    # Resolution
    resolution: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="วิธีการแก้ไข/ผลการดำเนินการ"
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="เหตุผลที่ปฏิเสธ")

    # Rating & Feedback (หลังจากเสร็จสิ้น)
    rating: Mapped[int | None] = mapped_column(nullable=True, comment="คะแนนความพึงพอใจ (1-5)")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="ความคิดเห็นเพิ่มเติม")

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="requests",
    )
    assigned_staff: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_staff_id],
    )
    attachments: Mapped[list["RequestAttachment"]] = relationship(
        "RequestAttachment",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_requests_status_priority", "status", "priority"),
        Index("ix_requests_type_status", "request_type", "status"),
        Index("ix_requests_user_status", "user_id", "status"),
        Index("ix_requests_assigned_status", "assigned_staff_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Request(id={self.id}, number={self.request_number}, "
            f"status={self.status}, priority={self.priority})>"
        )


class RequestAttachment(Base, TimestampMixin):
    """
    Request Attachment Model - ไฟล์แนบของคำร้อง
    """

    __tablename__ = "request_attachments"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Foreign Key
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="คำร้องที่เกี่ยวข้อง",
    )

    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="ชื่อไฟล์")
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Path ของไฟล์ในระบบ storage"
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="URL สำหรับเข้าถึงไฟล์")
    file_size: Mapped[int] = mapped_column(nullable=False, comment="ขนาดไฟล์ (bytes)")
    file_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME type")

    # Relationships
    request: Mapped["Request"] = relationship(
        "Request",
        back_populates="attachments",
    )

    def __repr__(self) -> str:
        return f"<RequestAttachment(id={self.id}, filename={self.filename})>"
