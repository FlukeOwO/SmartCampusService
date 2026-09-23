"""
Notification Router - API Endpoints สำหรับ Notification System
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, NotificationType
from app.core.database import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_active_user
from app.modules.notifications.service import NotificationService
from app.schemas.notification import (
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
    NotificationStatsResponse,
    PaginatedNotificationsResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============================================================================
# Get User's Notifications
# ============================================================================


@router.get(
    "",
    response_model=PaginatedNotificationsResponse,
    summary="ดึงรายการ Notifications ของตัวเอง",
    description="ดึงรายการการแจ้งเตือนของผู้ใช้ที่ล็อกอินอยู่",
)
async def get_my_notifications(
    is_read: Annotated[Optional[bool], Query()] = None,
    notification_type: Annotated[Optional[NotificationType], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงรายการ Notifications ของผู้ใช้ที่ล็อกอินอยู่
    
    **Query Parameters:**
    - **is_read**: Filter by read status (true/false) (optional)
    - **notification_type**: Filter by type (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    
    **Returns:**
    - Paginated list of notifications with stats (total, read, unread)
    """
    service = NotificationService(db)
    skip = (page - 1) * page_size

    notifications, total, stats = await service.get_user_notifications(
        user=current_user,
        is_read=is_read,
        notification_type=notification_type,
        skip=skip,
        limit=page_size,
    )

    return PaginatedNotificationsResponse(
        items=[NotificationListResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        stats=NotificationStatsResponse(**stats),
    )


# ============================================================================
# Get Notification by ID
# ============================================================================


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="ดึงข้อมูล Notification โดย ID",
    description="ดึงข้อมูลการแจ้งเตือนแบบละเอียด",
)
async def get_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงข้อมูล Notification โดย ID
    
    **Permissions:**
    - เข้าถึงได้เฉพาะ Notification ของตัวเอง
    """
    service = NotificationService(db)
    notification = await service.get_notification_by_id(notification_id, user=current_user)
    return notification


# ============================================================================
# Get Notification Stats
# ============================================================================


@router.get(
    "/stats/summary",
    response_model=NotificationStatsResponse,
    summary="ดึงสถิติการแจ้งเตือน",
    description="ดึงสถิติการแจ้งเตือน (total, read, unread)",
)
async def get_notification_stats(
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงสถิติการแจ้งเตือนของผู้ใช้
    
    **Returns:**
    - total: จำนวนทั้งหมด
    - read: จำนวนที่อ่านแล้ว
    - unread: จำนวนที่ยังไม่ได้อ่าน
    """
    service = NotificationService(db)
    _, _, stats = await service.get_user_notifications(
        user=current_user,
        skip=0,
        limit=1,  # เราต้องการแค่ stats ไม่ต้องการ items
    )

    return NotificationStatsResponse(**stats)


# ============================================================================
# Mark as Read
# ============================================================================


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="ทำเครื่องหมายว่าอ่านแล้ว",
    description="ทำเครื่องหมายว่าอ่าน Notification แล้ว",
)
async def mark_notification_as_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ทำเครื่องหมายว่าอ่าน Notification แล้ว
    
    **Permissions:**
    - เข้าถึงได้เฉพาะ Notification ของตัวเอง
    """
    service = NotificationService(db)
    notification = await service.mark_notification_as_read(notification_id, user=current_user)
    return notification


@router.post(
    "/read/batch",
    summary="ทำเครื่องหมายว่าอ่านหลายรายการ",
    description="ทำเครื่องหมายว่าอ่าน Notifications หลายรายการพร้อมกัน",
)
async def mark_notifications_as_read(
    request: NotificationMarkReadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ทำเครื่องหมายว่าอ่าน Notifications หลายรายการ
    
    **Request Body:**
    ```json
    {
        "notification_ids": [1, 2, 3, 4, 5]
    }
    ```
    
    **Returns:**
    - จำนวน Notifications ที่ทำเครื่องหมายแล้ว
    """
    service = NotificationService(db)
    count = await service.mark_notifications_as_read(
        notification_ids=request.notification_ids,
        user=current_user,
    )

    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "count": count,
    }


@router.post(
    "/read/all",
    summary="ทำเครื่องหมายว่าอ่านทั้งหมด",
    description="ทำเครื่องหมายว่าอ่าน Notifications ทั้งหมด",
)
async def mark_all_notifications_as_read(
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ทำเครื่องหมายว่าอ่าน Notifications ทั้งหมด
    
    **Returns:**
    - จำนวน Notifications ที่ทำเครื่องหมายแล้ว
    """
    service = NotificationService(db)
    count = await service.mark_all_as_read(user=current_user)

    return {
        "success": True,
        "message": f"Marked all {count} notifications as read",
        "count": count,
    }


# ============================================================================
# Delete Notifications
# ============================================================================


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ลบ Notification",
    description="ลบการแจ้งเตือน",
)
async def delete_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ลบ Notification
    
    **Permissions:**
    - เข้าถึงได้เฉพาะ Notification ของตัวเอง
    """
    service = NotificationService(db)
    await service.delete_notification(notification_id, user=current_user)
    return None


@router.delete(
    "/read/all",
    summary="ลบ Notifications ที่อ่านแล้วทั้งหมด",
    description="ลบการแจ้งเตือนที่อ่านแล้วทั้งหมด",
)
async def delete_all_read_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ลบ Notifications ที่อ่านแล้วทั้งหมด
    
    **Returns:**
    - จำนวน Notifications ที่ลบ
    """
    service = NotificationService(db)
    count = await service.delete_all_read_notifications(user=current_user)

    return {
        "success": True,
        "message": f"Deleted {count} read notifications",
        "count": count,
    }
