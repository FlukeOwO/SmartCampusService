"""
Inventory Router - API Endpoints สำหรับ Rooms และ Equipment
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import EquipmentStatus, RoomStatus, RoomType
from app.core.database import get_db
from app.models import Equipment, Room, User
from app.modules.auth.dependencies import get_current_active_user, require_staff

router = APIRouter()


# =============================================================================
# Rooms
# =============================================================================


@router.get("/rooms", response_model=list[dict])
async def list_rooms(
    db: Annotated[AsyncSession, Depends(get_db)],
    building: str | None = Query(None, description="กรองตามอาคาร"),
    room_type: RoomType | None = Query(None, description="กรองตามประเภทห้อง"),
    status: RoomStatus | None = Query(None, description="กรองตามสถานะ"),
    is_bookable: bool | None = Query(None, description="กรองตามความสามารถจอง"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    ดูรายการห้องทั้งหมด
    
    Query Parameters:
        - building: ชื่ออาคาร
        - room_type: ประเภทห้อง (classroom, meeting_room, laboratory, etc.)
        - status: สถานะห้อง (available, in_use, maintenance, closed)
        - is_bookable: สามารถจองได้หรือไม่
        - limit: จำนวนรายการสูงสุด
        - offset: เริ่มต้นจากรายการที่
    """
    query = select(Room)

    # Filters
    if building:
        query = query.where(Room.building == building)
    if room_type:
        query = query.where(Room.room_type == room_type.value)
    if status:
        query = query.where(Room.status == status.value)
    if is_bookable is not None:
        query = query.where(Room.is_bookable == is_bookable)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    rooms = result.scalars().all()

    return [
        {
            "id": room.id,
            "room_number": room.room_number,
            "room_name": room.room_name,
            "room_type": room.room_type,
            "building": room.building,
            "floor": room.floor,
            "capacity": room.capacity,
            "status": room.status,
            "is_bookable": room.is_bookable,
            "image_url": room.image_url,
        }
        for room in rooms
    ]


@router.get("/rooms/{room_id}", response_model=dict)
async def get_room(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ดูรายละเอียดห้อง"""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    import json

    return {
        "id": room.id,
        "room_number": room.room_number,
        "room_name": room.room_name,
        "room_type": room.room_type,
        "building": room.building,
        "floor": room.floor,
        "capacity": room.capacity,
        "description": room.description,
        "facilities": json.loads(room.facilities) if room.facilities else [],
        "image_url": room.image_url,
        "status": room.status,
        "is_bookable": room.is_bookable,
        "created_at": room.created_at,
    }


# =============================================================================
# Equipment
# =============================================================================


@router.get("/equipments", response_model=list[dict])
async def list_equipments(
    db: Annotated[AsyncSession, Depends(get_db)],
    equipment_type: str | None = Query(None, description="กรองตามประเภทอุปกรณ์"),
    status: EquipmentStatus | None = Query(None, description="กรองตามสถานะ"),
    is_bookable: bool | None = Query(None, description="กรองตามความสามารถจอง"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    ดูรายการอุปกรณ์ทั้งหมด
    
    Query Parameters:
        - equipment_type: ประเภทอุปกรณ์ (projector, laptop, camera, etc.)
        - status: สถานะอุปกรณ์ (available, in_use, maintenance, broken, retired)
        - is_bookable: สามารถจองได้หรือไม่
        - limit: จำนวนรายการสูงสุด
        - offset: เริ่มต้นจากรายการที่
    """
    query = select(Equipment)

    # Filters
    if equipment_type:
        query = query.where(Equipment.equipment_type == equipment_type)
    if status:
        query = query.where(Equipment.status == status.value)
    if is_bookable is not None:
        query = query.where(Equipment.is_bookable == is_bookable)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    equipments = result.scalars().all()

    return [
        {
            "id": eq.id,
            "equipment_code": eq.equipment_code,
            "equipment_name": eq.equipment_name,
            "equipment_type": eq.equipment_type,
            "brand": eq.brand,
            "model": eq.model,
            "status": eq.status,
            "is_bookable": eq.is_bookable,
            "quantity": eq.quantity,
            "location": eq.location,
            "image_url": eq.image_url,
        }
        for eq in equipments
    ]


@router.get("/equipments/{equipment_id}", response_model=dict)
async def get_equipment(
    equipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ดูรายละเอียดอุปกรณ์"""
    equipment = await db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found"
        )

    import json

    return {
        "id": equipment.id,
        "equipment_code": equipment.equipment_code,
        "equipment_name": equipment.equipment_name,
        "equipment_type": equipment.equipment_type,
        "brand": equipment.brand,
        "model": equipment.model,
        "serial_number": equipment.serial_number,
        "description": equipment.description,
        "specifications": (
            json.loads(equipment.specifications) if equipment.specifications else {}
        ),
        "image_url": equipment.image_url,
        "location": equipment.location,
        "responsible_staff": equipment.responsible_staff,
        "status": equipment.status,
        "is_bookable": equipment.is_bookable,
        "quantity": equipment.quantity,
        "last_maintenance_date": equipment.last_maintenance_date,
        "next_maintenance_date": equipment.next_maintenance_date,
        "created_at": equipment.created_at,
    }
