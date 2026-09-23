"""
User Model - ผู้ใช้งานระบบ (Student, Staff, Admin)
"""

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_models import TimestampMixin
from app.common.constants import UserRole
from app.core.database import Base


class User(Base, TimestampMixin):
    """
    User Model - เก็บข้อมูลผู้ใช้งานระบบ
    
    Relationships:
        - bookings: การจองของผู้ใช้
        - requests: คำร้องของผู้ใช้
        - notifications: การแจ้งเตือนของผู้ใช้
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, comment="อีเมล (ใช้สำหรับ login)"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="รหัสผ่านที่ Hash แล้ว"
    )

    # Profile Information
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="ชื่อ-นามสกุล"
    )
    student_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, index=True, nullable=True, comment="รหัสนักศึกษา (สำหรับ Student)"
    )
    staff_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, index=True, nullable=True, comment="รหัสพนักงาน (สำหรับ Staff/Admin)"
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="เบอร์โทรศัพท์"
    )
    department: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="ภาควิชา/แผนก"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL รูปโปรไฟล์"
    )

    # Role & Status
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.STUDENT.value,
        index=True,
        comment="บทบาท: student, staff, admin",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="สถานะการใช้งาน"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="ยืนยันอีเมลแล้วหรือไม่"
    )

    # Relationships (Lazy Loading)
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )
    requests: Mapped[list["Request"]] = relationship(
        "Request", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes สำหรับ Performance
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
