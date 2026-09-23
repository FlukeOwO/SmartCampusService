"""
Booking Schemas - Pydantic Models สำหรับ API Request/Response
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.common.constants import BookingStatus


# ============================================================================
# Base Schemas
# ============================================================================


class BookingBase(BaseModel):
    """Base Booking Schema"""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = Field(None, max_length=255)
    start_time: datetime
    end_time: datetime
    attendees_count: int | None = Field(None, ge=1)
    contact_person: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    notes: str | None = None

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """ตรวจสอบว่า end_time > start_time"""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


# ============================================================================
# Request Schemas
# ============================================================================


class BookingCreateRoom(BookingBase):
    """Schema สำหรับจองห้อง"""

    room_id: int


class BookingCreateEquipment(BookingBase):
    """Schema สำหรับจองอุปกรณ์"""

    equipment_id: int


class BookingUpdate(BaseModel):
    """Schema สำหรับอัปเดตการจอง"""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    attendees_count: int | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class BookingApprove(BaseModel):
    """Schema สำหรับอนุมัติการจอง"""

    notes: str | None = None


class BookingReject(BaseModel):
    """Schema สำหรับปฏิเสธการจอง"""

    rejection_reason: str = Field(..., min_length=1)


class BookingCancel(BaseModel):
    """Schema สำหรับยกเลิกการจอง"""

    cancellation_reason: str = Field(..., min_length=1)


# ============================================================================
# Response Schemas
# ============================================================================


class BookingResponse(BookingBase):
    """Schema สำหรับ Response"""

    id: int
    user_id: int
    room_id: int | None = None
    equipment_id: int | None = None
    status: BookingStatus
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingWithDetails(BookingResponse):
    """Schema สำหรับ Response พร้อมข้อมูลเพิ่มเติม"""

    user: dict | None = None  # จะ populate ด้วย UserResponse
    room: dict | None = None  # จะ populate ด้วย RoomResponse
    equipment: dict | None = None  # จะ populate ด้วย EquipmentResponse
