from pydantic import BaseModel
from typing import Optional

class RoomBase(BaseModel):
    name: str
    building: str
    capacity: int
    status: Optional[str] = "AVAILABLE"

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int

    class Config:
        from_attributes = True