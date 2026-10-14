"""
Inventory service - ห้อง (Room) และอุปกรณ์ (Equipment)
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import PageParams
from app.common.exceptions import ConflictException, NotFoundException
from app.models import Booking, Equipment, Room
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.schemas.room import RoomCreate, RoomUpdate


def _enum_values(data: dict[str, Any]) -> dict[str, Any]:
    return {k: getattr(v, "value", v) for k, v in data.items()}


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _page(self, query, order_by, params: PageParams):
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.scalars(
            query.order_by(order_by).offset(params.offset).limit(params.page_size)
        )
        return list(rows), total or 0

    async def _save(self, obj, label: str):
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictException(f"{label} with the same code/number already exists") from exc
        await self.db.refresh(obj)
        return obj

    async def _ensure_no_bookings(self, column, resource_id: int) -> None:
        # ลบแล้วประวัติการจองจะหายตาม (cascade) จึงยอมลบเฉพาะที่ไม่เคยถูกจอง
        has_bookings = await self.db.scalar(
            select(select(Booking.id).where(column == resource_id).exists())
        )
        if has_bookings:
            raise ConflictException(
                "Resource has booking history; set status or is_bookable=false instead"
            )

    # ------------------------------------------------------------------ rooms
    async def list_rooms(
        self,
        params: PageParams,
        building: str | None = None,
        room_type: str | None = None,
        status: str | None = None,
        bookable: bool | None = None,
        min_capacity: int | None = None,
        search: str | None = None,
    ) -> tuple[list[Room], int]:
        query = select(Room)
        if building:
            query = query.where(Room.building == building)
        if room_type:
            query = query.where(Room.room_type == room_type)
        if status:
            query = query.where(Room.status == status)
        if bookable is not None:
            query = query.where(Room.is_bookable.is_(bookable))
        if min_capacity:
            query = query.where(Room.capacity >= min_capacity)
        if search:
            pattern = f"%{search}%"
            query = query.where(Room.room_name.ilike(pattern) | Room.room_number.ilike(pattern))
        return await self._page(query, Room.room_number, params)

    async def get_room(self, room_id: int) -> Room:
        room = await self.db.get(Room, room_id)
        if room is None:
            raise NotFoundException("Room not found")
        return room

    async def create_room(self, data: RoomCreate) -> Room:
        room = Room(**_enum_values(data.model_dump()))
        self.db.add(room)
        return await self._save(room, "Room")

    async def update_room(self, room_id: int, data: RoomUpdate) -> Room:
        room = await self.get_room(room_id)
        for field, value in _enum_values(data.model_dump(exclude_unset=True)).items():
            setattr(room, field, value)
        return await self._save(room, "Room")

    async def delete_room(self, room_id: int) -> None:
        room = await self.get_room(room_id)
        await self._ensure_no_bookings(Booking.room_id, room_id)
        await self.db.delete(room)
        await self.db.commit()

    # ------------------------------------------------------------- equipment
    async def list_equipments(
        self,
        params: PageParams,
        equipment_type: str | None = None,
        status: str | None = None,
        bookable: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Equipment], int]:
        query = select(Equipment)
        if equipment_type:
            query = query.where(Equipment.equipment_type == equipment_type)
        if status:
            query = query.where(Equipment.status == status)
        if bookable is not None:
            query = query.where(Equipment.is_bookable.is_(bookable))
        if search:
            pattern = f"%{search}%"
            query = query.where(
                Equipment.equipment_name.ilike(pattern) | Equipment.equipment_code.ilike(pattern)
            )
        return await self._page(query, Equipment.equipment_code, params)

    async def get_equipment(self, equipment_id: int) -> Equipment:
        equipment = await self.db.get(Equipment, equipment_id)
        if equipment is None:
            raise NotFoundException("Equipment not found")
        return equipment

    async def create_equipment(self, data: EquipmentCreate) -> Equipment:
        equipment = Equipment(**_enum_values(data.model_dump()), quantity=1)
        self.db.add(equipment)
        return await self._save(equipment, "Equipment")

    async def update_equipment(self, equipment_id: int, data: EquipmentUpdate) -> Equipment:
        equipment = await self.get_equipment(equipment_id)
        for field, value in _enum_values(data.model_dump(exclude_unset=True)).items():
            setattr(equipment, field, value)
        return await self._save(equipment, "Equipment")

    async def delete_equipment(self, equipment_id: int) -> None:
        equipment = await self.get_equipment(equipment_id)
        await self._ensure_no_bookings(Booking.equipment_id, equipment_id)
        await self.db.delete(equipment)
        await self.db.commit()
