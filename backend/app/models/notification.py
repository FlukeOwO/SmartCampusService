"""
Notification Model - การแจ้งเตือนภายในระบบ
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.core.database import Base


class Notification(Base, TimestampMixin):
    """
    Notification Model - การแจ้งเตือนใน Application

    Relationships:
        - user: ผู้รับการแจ้งเตือน
    """

    __tablename__ = "notifications"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Foreign Key
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ผู้รับการแจ้งเตือน",
    )

    # Notification Information
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="ประเภทการแจ้งเตือน: request_update, booking_confirmed, etc.",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="หัวข้อการแจ้งเตือน")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="เนื้อหาการแจ้งเตือน")

    # Related Resource (Optional)
    related_resource_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="ประเภท Resource ที่เกี่ยวข้อง: request, booking"
    )
    related_resource_id: Mapped[int | None] = mapped_column(
        nullable=True, comment="ID ของ Resource ที่เกี่ยวข้อง"
    )
    action_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL สำหรับ Action (เช่น ดูคำร้อง)"
    )

    # Status
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="อ่านแล้วหรือไม่"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="เวลาที่อ่าน"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    # Indexes
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_type_read", "notification_type", "is_read"),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type}, is_read={self.is_read})>"
        )

    def mark_as_read(self) -> None:
        """ทำเครื่องหมายว่าอ่านแล้ว"""
        self.is_read = True
        self.read_at = datetime.now(UTC)
