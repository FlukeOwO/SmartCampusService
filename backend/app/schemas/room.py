"""
Room schemas
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.constants import RoomStatus, RoomType


class RoomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=50)
    room_name: str = Field(..., min_length=1, max_length=255)
    room_type: RoomType = RoomType.CLASSROOM
    building: str = Field(..., min_length=1, max_length=100)
    floor: int = Field(..., ge=-5, le=200)
    capacity: int = Field(30, ge=1, le=10000)
    description: str | None = None
    facilities: str | None = None
    image_url: str | None = Field(None, max_length=500)
    status: RoomStatus = RoomStatus.AVAILABLE
    is_bookable: bool = True


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_number: str | None = Field(None, min_length=1, max_length=50)
    room_name: str | None = Field(None, min_length=1, max_length=255)
    room_type: RoomType | None = None
    building: str | None = Field(None, min_length=1, max_length=100)
    floor: int | None = Field(None, ge=-5, le=200)
    capacity: int | None = Field(None, ge=1, le=10000)
    description: str | None = None
    facilities: str | None = None
    image_url: str | None = Field(None, max_length=500)
    status: RoomStatus | None = None
    is_bookable: bool | None = None


class RoomResponse(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
