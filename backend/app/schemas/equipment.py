"""
Equipment schemas - อุปกรณ์ 1 แถว = 1 ชิ้น (quantity = 1)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.constants import EquipmentStatus


class EquipmentBase(BaseModel):
    equipment_code: str = Field(..., min_length=1, max_length=50)
    equipment_name: str = Field(..., min_length=1, max_length=255)
    equipment_type: str = Field(..., min_length=1, max_length=100)
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    serial_number: str | None = Field(None, max_length=100)
    description: str | None = None
    specifications: str | None = None
    image_url: str | None = Field(None, max_length=500)
    location: str | None = Field(None, max_length=255)
    responsible_staff: str | None = Field(None, max_length=255)
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    is_bookable: bool = True


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    equipment_code: str | None = Field(None, min_length=1, max_length=50)
    equipment_name: str | None = Field(None, min_length=1, max_length=255)
    equipment_type: str | None = Field(None, min_length=1, max_length=100)
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    serial_number: str | None = Field(None, max_length=100)
    description: str | None = None
    specifications: str | None = None
    image_url: str | None = Field(None, max_length=500)
    location: str | None = Field(None, max_length=255)
    responsible_staff: str | None = Field(None, max_length=255)
    status: EquipmentStatus | None = None
    is_bookable: bool | None = None


class EquipmentResponse(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
