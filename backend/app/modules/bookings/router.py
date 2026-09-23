"""
Booking Router - API Endpoints สำหรับการจอง
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import BookingStatus
from app.common.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.database import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_active_user, require_staff
from app.modules.bookings.service import BookingService
from app.schemas.booking import (
    BookingApprove,
    BookingCancel,
    BookingCreateEquipment,
    BookingCreateRoom,
    BookingReject,
    BookingResponse,
    BookingWithDetails,
)

router = APIRouter()


# =============================================================================
# Room Bookings
# =============================================================================


@router.post("/rooms", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_room_booking(
    booking_data: BookingCreateRoom,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    จองห้อง
    
    Required: Authentication
    
    Process:
        1. Lock ห้องด้วย SELECT FOR UPDATE
        2. ตรวจสอบความพร้อมและ conflicts
        3. สร้างการจอง (สถานะ: pending)
    """
    try:
        service = BookingService(db)
        booking = await service.create_room_booking(current_user.id, booking_data)
        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# Equipment Bookings
# =============================================================================


@router.post(
    "/equipments",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_equipment_booking(
    booking_data: BookingCreateEquipment,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    จองอุปกรณ์
    
    Required: Authentication
    """
    try:
        service = BookingService(db)
        booking = await service.create_equipment_booking(current_user.id, booking_data)
        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# Booking Management
# =============================================================================


@router.get("/me", response_model=list[BookingResponse])
async def get_my_bookings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: BookingStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    ดูรายการการจองของตัวเอง
    
    Required: Authentication
    
    Query Parameters:
        - status: กรองตามสถานะ (pending, confirmed, cancelled, completed, rejected)
        - limit: จำนวนรายการสูงสุด
        - offset: เริ่มต้นจากรายการที่
    """
    service = BookingService(db)
    bookings = await service.get_user_bookings(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return bookings


@router.get("/{booking_id}", response_model=BookingWithDetails)
async def get_booking(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    ดูรายละเอียดการจอง
    
    Required: Authentication
    """
    try:
        service = BookingService(db)
        booking = await service.get_booking_by_id(booking_id, load_relations=True)

        # ตรวจสอบสิทธิ์ (เจ้าของหรือ Staff/Admin เท่านั้น)
        from app.common.constants import UserRole

        is_owner = booking.user_id == current_user.id
        is_staff = current_user.role in [UserRole.STAFF.value, UserRole.ADMIN.value]

        if not (is_owner or is_staff):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this booking",
            )

        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: int,
    approve_data: BookingApprove,
    current_user: Annotated[User, Depends(require_staff())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    อนุมัติการจอง
    
    Required: Staff or Admin role
    """
    try:
        service = BookingService(db)
        booking = await service.approve_booking(
            booking_id=booking_id,
            approved_by=current_user.id,
            notes=approve_data.notes,
        )
        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking(
    booking_id: int,
    reject_data: BookingReject,
    current_user: Annotated[User, Depends(require_staff())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    ปฏิเสธการจอง
    
    Required: Staff or Admin role
    """
    try:
        service = BookingService(db)
        booking = await service.reject_booking(
            booking_id=booking_id,
            rejection_reason=reject_data.rejection_reason,
        )
        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    cancel_data: BookingCancel,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    ยกเลิกการจอง (โดยผู้จอง)
    
    Required: Authentication (ต้องเป็นเจ้าของการจอง)
    """
    try:
        service = BookingService(db)
        booking = await service.cancel_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            cancellation_reason=cancel_data.cancellation_reason,
        )
        return booking
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Availability Check
# =============================================================================


@router.get("/rooms/{room_id}/availability")
async def check_room_availability(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_time: datetime = Query(..., description="เวลาเริ่มต้น (ISO format)"),
    end_time: datetime = Query(..., description="เวลาสิ้นสุด (ISO format)"),
):
    """
    ตรวจสอบความว่างของห้อง
    
    Query Parameters:
        - start_time: เวลาเริ่มต้น (ISO 8601 format)
        - end_time: เวลาสิ้นสุด (ISO 8601 format)
    
    Returns:
        - available: true ถ้าห้องว่าง
        - room_id: ID ของห้อง
        - time_slot: ช่วงเวลาที่ตรวจสอบ
    """
    service = BookingService(db)
    is_available = await service.check_room_availability(room_id, start_time, end_time)

    return {
        "available": is_available,
        "room_id": room_id,
        "time_slot": {"start_time": start_time, "end_time": end_time},
    }


@router.get("/equipments/{equipment_id}/availability")
async def check_equipment_availability(
    equipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_time: datetime = Query(..., description="เวลาเริ่มต้น (ISO format)"),
    end_time: datetime = Query(..., description="เวลาสิ้นสุด (ISO format)"),
):
    """
    ตรวจสอบความว่างของอุปกรณ์
    
    Query Parameters:
        - start_time: เวลาเริ่มต้น (ISO 8601 format)
        - end_time: เวลาสิ้นสุด (ISO 8601 format)
    """
    service = BookingService(db)
    is_available = await service.check_equipment_availability(
        equipment_id, start_time, end_time
    )

    return {
        "available": is_available,
        "equipment_id": equipment_id,
        "time_slot": {"start_time": start_time, "end_time": end_time},
    }
