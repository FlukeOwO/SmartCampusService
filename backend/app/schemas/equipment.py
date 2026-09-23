from pydantic import BaseModel
from typing import Optional

class EquipmentBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    status: Optional[str] = "AVAILABLE"

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentResponse(EquipmentBase):
    id: int

    class Config:
        from_attributes = True