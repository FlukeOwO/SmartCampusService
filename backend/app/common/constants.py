"""
Enums และค่าคงที่ของระบบ
"""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


STAFF_ROLES = {UserRole.STAFF.value, UserRole.ADMIN.value}


class RequestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# สถานะที่เปลี่ยนต่อได้ (staff) - สถานะอื่นถือว่าจบแล้ว
REQUEST_STATUS_TRANSITIONS: dict[str, set[str]] = {
    RequestStatus.PENDING.value: {RequestStatus.IN_PROGRESS.value, RequestStatus.REJECTED.value},
    RequestStatus.IN_PROGRESS.value: {RequestStatus.COMPLETED.value, RequestStatus.REJECTED.value},
}


class RequestType(str, Enum):
    MAINTENANCE = "maintenance"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    OTHER = "other"


class RequestPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REJECTED = "rejected"


# การจองที่ยัง "ถือ" ช่วงเวลาอยู่ (ใช้ทั้งใน conflict check และ exclusion constraint)
ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value)


class EquipmentStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"
    RETIRED = "retired"


class RoomStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class RoomType(str, Enum):
    CLASSROOM = "classroom"
    MEETING_ROOM = "meeting_room"
    LABORATORY = "laboratory"
    AUDITORIUM = "auditorium"
    STUDIO = "studio"
    OTHER = "other"


class NotificationType(str, Enum):
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATE = "request_update"
    REQUEST_ASSIGNED = "request_assigned"
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_REJECTED = "booking_rejected"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_REMINDER = "booking_reminder"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


# -----------------------------------------------------------------------------
# Booking rules
# -----------------------------------------------------------------------------
BOOKING_MIN_MINUTES = 15
ROOM_BOOKING_MAX_HOURS = 24
EQUIPMENT_BOOKING_MAX_DAYS = 7
BOOKING_MAX_ADVANCE_DAYS = 90

# -----------------------------------------------------------------------------
# File upload: นามสกุล -> (MIME type, magic bytes ที่ยอมรับ)
# -----------------------------------------------------------------------------
ALLOWED_UPLOADS: dict[str, tuple[str, tuple[bytes, ...]]] = {
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".gif": ("image/gif", (b"GIF87a", b"GIF89a")),
    ".webp": ("image/webp", (b"RIFF",)),
    ".pdf": ("application/pdf", (b"%PDF-",)),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        (b"PK\x03\x04",),
    ),
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        (b"PK\x03\x04",),
    ),
}

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
