"""
Booking schemas - เวลาต้องมี timezone เสมอ (เช่น 2026-10-20T09:00:00+07:00)
"""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.common.constants import BookingStatus


class BookingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = Field(None, max_length=255)
    attendees_count: int | None = Field(None, ge=1)
    contact_person: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    notes: str | None = None


class _BookingTimes(BaseModel):
    start_time: AwareDatetime
    end_time: AwareDatetime

    @model_validator(mode="after")
    def _check_order(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class BookingCreateRoom(BookingBase, _BookingTimes):
    room_id: int


class BookingCreateEquipment(BookingBase, _BookingTimes):
    equipment_id: int


class BookingReject(BaseModel):
    rejection_reason: str = Field(..., min_length=1)


class BookingCancel(BaseModel):
    cancellation_reason: str = Field(..., min_length=1)


class BookingResponse(BookingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    room_id: int | None = None
    equipment_id: int | None = None
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityResponse(BaseModel):
    available: bool
    resource_type: str
    resource_id: int
    start_time: datetime
    end_time: datetime
    busy_slots: list[TimeSlot]
