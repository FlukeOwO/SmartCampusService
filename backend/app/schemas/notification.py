"""
Notification schemas
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.constants import NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    related_resource_type: str | None = None
    related_resource_id: int | None = None
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationStats(BaseModel):
    total: int
    unread: int
    read: int


class MarkedCount(BaseModel):
    updated: int
