"""
Notification Schemas - Pydantic schemas สำหรับ Notification API
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.common.constants import NotificationType


# ============================================================================
# Notification Schemas
# ============================================================================


class NotificationBase(BaseModel):
    """Base schema สำหรับ Notification"""

    notification_type: NotificationType
    title: str = Field(..., max_length=255, description="หัวข้อการแจ้งเตือน")
    message: str = Field(..., description="เนื้อหาการแจ้งเตือน")
    related_resource_type: Optional[str] = Field(None, description="ประเภท Resource: request, booking")
    related_resource_id: Optional[int] = Field(None, description="ID ของ Resource")
    action_url: Optional[str] = Field(None, max_length=500, description="URL สำหรับ Action")


class NotificationCreate(NotificationBase):
    """Schema สำหรับสร้าง Notification"""

    user_id: int = Field(..., description="ผู้รับการแจ้งเตือน")


class NotificationResponse(BaseModel):
    """Response schema สำหรับ Notification"""

    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    related_resource_type: Optional[str] = None
    related_resource_id: Optional[int] = None
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response schema สำหรับ list ของ Notifications"""

    id: int
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkReadRequest(BaseModel):
    """Request schema สำหรับทำเครื่องหมายว่าอ่านแล้ว"""

    notification_ids: list[int] = Field(..., description="List ของ Notification IDs")


class NotificationStatsResponse(BaseModel):
    """Response schema สำหรับสถิติการแจ้งเตือน"""

    total: int = Field(..., description="จำนวนทั้งหมด")
    unread: int = Field(..., description="จำนวนที่ยังไม่ได้อ่าน")
    read: int = Field(..., description="จำนวนที่อ่านแล้ว")


# ============================================================================
# Pagination
# ============================================================================


class PaginatedNotificationsResponse(BaseModel):
    """Response schema สำหรับ paginated notifications"""

    items: list[NotificationListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: NotificationStatsResponse