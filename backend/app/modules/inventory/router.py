"""
Inventory router - /api/v1/inventory
อ่านได้ทุกคน (ต้อง login), สร้าง/แก้/ลบ เฉพาะ staff/admin
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import Page, PageParams
from app.common.constants import EquipmentStatus, RoomStatus, RoomType
from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser, StaffUser
from app.modules.inventory.service import InventoryService
from app.schemas.equipment import EquipmentCreate, EquipmentResponse, EquipmentUpdate
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PageParams, Depends()]


# ---------------------------------------------------------------------- rooms
@router.get("/rooms", response_model=Page[RoomResponse])
async def list_rooms(
    _: CurrentUser,
    db: DB,
    params: Pagination,
    building: str | None = None,
    room_type: RoomType | None = None,
    status_filter: RoomStatus | None = Query(None, alias="status"),
    bookable: bool | None = None,
    min_capacity: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=100),
):
    items, total = await InventoryService(db).list_rooms(
        params,
        building=building,
        room_type=room_type.value if room_type else None,
        status=status_filter.value if status_filter else None,
        bookable=bookable,
        min_capacity=min_capacity,
        search=search,
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: int, _: CurrentUser, db: DB):
    return await InventoryService(db).get_room(room_id)


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(data: RoomCreate, _: StaffUser, db: DB):
    return await InventoryService(db).create_room(data)


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, data: RoomUpdate, _: StaffUser, db: DB):
    return await InventoryService(db).update_room(room_id, data)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: int, _: StaffUser, db: DB):
    await InventoryService(db).delete_room(room_id)


# ------------------------------------------------------------------ equipment
@router.get("/equipments", response_model=Page[EquipmentResponse])
async def list_equipments(
    _: CurrentUser,
    db: DB,
    params: Pagination,
    equipment_type: str | None = None,
    status_filter: EquipmentStatus | None = Query(None, alias="status"),
    bookable: bool | None = None,
    search: str | None = Query(None, max_length=100),
):
    items, total = await InventoryService(db).list_equipments(
        params,
        equipment_type=equipment_type,
        status=status_filter.value if status_filter else None,
        bookable=bookable,
        search=search,
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/equipments/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(equipment_id: int, _: CurrentUser, db: DB):
    return await InventoryService(db).get_equipment(equipment_id)


@router.post("/equipments", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(data: EquipmentCreate, _: StaffUser, db: DB):
    return await InventoryService(db).create_equipment(data)


@router.patch("/equipments/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(equipment_id: int, data: EquipmentUpdate, _: StaffUser, db: DB):
    return await InventoryService(db).update_equipment(equipment_id, data)


@router.delete("/equipments/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(equipment_id: int, _: StaffUser, db: DB):
    await InventoryService(db).delete_equipment(equipment_id)
