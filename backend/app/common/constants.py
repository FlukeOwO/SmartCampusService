"""
Application Constants - Enums และค่าคงที่
"""

from enum import Enum


# ============================================================================
# User Roles
# ============================================================================


class UserRole(str, Enum):
    """User roles สำหรับ RBAC"""

    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


# ============================================================================
# Request Status
# ============================================================================


class RequestStatus(str, Enum):
    """สถานะของคำร้อง"""

    PENDING = "pending"  # รอดำเนินการ
    IN_PROGRESS = "in_progress"  # กำลังดำเนินการ
    COMPLETED = "completed"  # เสร็จสิ้น
    REJECTED = "rejected"  # ปฏิเสธ
    CANCELLED = "cancelled"  # ยกเลิก


class RequestType(str, Enum):
    """ประเภทของคำร้อง"""

    MAINTENANCE = "maintenance"  # แจ้งซ่อม
    COMPLAINT = "complaint"  # ร้องเรียน
    INQUIRY = "inquiry"  # สอบถาม
    OTHER = "other"  # อื่นๆ


class RequestPriority(str, Enum):
    """ระดับความสำคัญของคำร้อง"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# Booking Status
# ============================================================================


class BookingStatus(str, Enum):
    """สถานะการจอง"""

    PENDING = "pending"  # รอการอนุมัติ
    CONFIRMED = "confirmed"  # ยืนยันแล้ว
    CANCELLED = "cancelled"  # ยกเลิก
    COMPLETED = "completed"  # เสร็จสิ้น (หลังจากใช้งานแล้ว)
    REJECTED = "rejected"  # ปฏิเสธ


# ============================================================================
# Equipment & Room
# ============================================================================


class EquipmentStatus(str, Enum):
    """สถานะของอุปกรณ์"""

    AVAILABLE = "available"  # พร้อมใช้งาน
    IN_USE = "in_use"  # กำลังใช้งาน
    MAINTENANCE = "maintenance"  # ซ่อมบำรุง
    BROKEN = "broken"  # ชำรุด
    RETIRED = "retired"  # ปลดระวาง


class RoomStatus(str, Enum):
    """สถานะของห้อง"""

    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class RoomType(str, Enum):
    """ประเภทของห้อง"""

    CLASSROOM = "classroom"  # ห้องเรียน
    MEETING_ROOM = "meeting_room"  # ห้องประชุม
    LABORATORY = "laboratory"  # ห้องปฏิบัติการ
    AUDITORIUM = "auditorium"  # หอประชุม
    STUDIO = "studio"  # สตูดิโอ
    OTHER = "other"


# ============================================================================
# Notification
# ============================================================================


class NotificationType(str, Enum):
    """ประเภทการแจ้งเตือน"""

    REQUEST_UPDATE = "request_update"  # อัปเดตสถานะคำร้อง
    BOOKING_CONFIRMED = "booking_confirmed"  # การจองได้รับการยืนยัน
    BOOKING_CANCELLED = "booking_cancelled"  # การจองถูกยกเลิก
    BOOKING_REMINDER = "booking_reminder"  # เตือนการจอง
    SYSTEM_ANNOUNCEMENT = "system_announcement"  # ประกาศระบบ


# ============================================================================
# File Upload
# ============================================================================

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".xls", ".xlsx"]
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS

# Max file sizes (MB)
MAX_IMAGE_SIZE_MB = 5
MAX_DOCUMENT_SIZE_MB = 10


# ============================================================================
# Pagination
# ============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
