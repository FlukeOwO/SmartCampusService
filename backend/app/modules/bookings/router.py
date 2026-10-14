"""
Booking router - /api/v1/bookings
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import Page, PageParams
from app.common.constants import BookingStatus
from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser, StaffUser
from app.modules.bookings.service import BookingService
from app.schemas.booking import (
    AvailabilityResponse,
    BookingCancel,
    BookingCreateEquipment,
    BookingCreateRoom,
    BookingReject,
    BookingResponse,
)

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PageParams, Depends()]
StartQ = Annotated[datetime, Query(description="ISO 8601 พร้อม timezone")]
EndQ = Annotated[datetime, Query(description="ISO 8601 พร้อม timezone")]


@router.post("/rooms", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_room(data: BookingCreateRoom, user: CurrentUser, db: DB):
    """จองห้อง - ได้ 409 ถ้าช่วงเวลาทับกับการจองที่ pending/confirmed"""
    return await BookingService(db).create_room_booking(user, data)


@router.post("/equipments", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_equipment(data: BookingCreateEquipment, user: CurrentUser, db: DB):
    """จองอุปกรณ์ (ไม่เกิน 7 วัน)"""
    return await BookingService(db).create_equipment_booking(user, data)


@router.get("/me", response_model=Page[BookingResponse])
async def my_bookings(
    user: CurrentUser,
    db: DB,
    params: Pagination,
    status_filter: BookingStatus | None = Query(None, alias="status"),
):
    items, total = await BookingService(db).list_bookings(
        params, user_id=user.id, status=status_filter
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("", response_model=Page[BookingResponse])
async def all_bookings(
    _: StaffUser,
    db: DB,
    params: Pagination,
    status_filter: BookingStatus | None = Query(None, alias="status"),
    room_id: int | None = None,
    equipment_id: int | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
):
    """ทุกการจอง (staff/admin) เช่น ?status=pending สำหรับคิวรออนุมัติ"""
    items, total = await BookingService(db).list_bookings(
        params,
        status=status_filter,
        room_id=room_id,
        equipment_id=equipment_id,
        start_from=start_from,
        start_to=start_to,
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/rooms/{room_id}/availability", response_model=AvailabilityResponse)
async def room_availability(
    room_id: int, start_time: StartQ, end_time: EndQ, _: CurrentUser, db: DB
):
    return await BookingService(db).availability("room", room_id, start_time, end_time)


@router.get("/equipments/{equipment_id}/availability", response_model=AvailabilityResponse)
async def equipment_availability(
    equipment_id: int, start_time: StartQ, end_time: EndQ, _: CurrentUser, db: DB
):
    return await BookingService(db).availability("equipment", equipment_id, start_time, end_time)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int, user: CurrentUser, db: DB):
    return await BookingService(db).get_booking(user, booking_id)


@router.put("/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(booking_id: int, staff: StaffUser, db: DB):
    return await BookingService(db).approve(staff, booking_id)


@router.put("/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking(booking_id: int, data: BookingReject, staff: StaffUser, db: DB):
    return await BookingService(db).reject(staff, booking_id, data.rejection_reason)


@router.put("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(booking_id: int, data: BookingCancel, user: CurrentUser, db: DB):
    """ผู้จองยกเลิกได้ก่อนเวลาเริ่ม, staff ยกเลิกได้เสมอ"""
    return await BookingService(db).cancel(user, booking_id, data.cancellation_reason)
