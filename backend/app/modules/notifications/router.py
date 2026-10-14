"""
Notification router - /api/v1/notifications (เห็นได้เฉพาะเจ้าของ)
Frontend poll GET /stats/summary ทุก ~30 วินาที
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import Page, PageParams
from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.notifications.service import NotificationService
from app.schemas.notification import MarkedCount, NotificationResponse, NotificationStats

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Page[NotificationResponse])
async def list_notifications(
    user: CurrentUser,
    db: DB,
    params: Annotated[PageParams, Depends()],
    unread_only: bool = Query(False),
):
    items, total = await NotificationService(db).list_for_user(user, params, unread_only)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/stats/summary", response_model=NotificationStats)
async def notification_stats(user: CurrentUser, db: DB):
    return await NotificationService(db).stats(user)


@router.post("/read/all", response_model=MarkedCount)
async def mark_all_read(user: CurrentUser, db: DB):
    return {"updated": await NotificationService(db).mark_all_read(user)}


@router.delete("/read", response_model=MarkedCount)
async def delete_read(user: CurrentUser, db: DB):
    return {"updated": await NotificationService(db).delete_read(user)}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: int, user: CurrentUser, db: DB):
    return await NotificationService(db).get_owned(user, notification_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(notification_id: int, user: CurrentUser, db: DB):
    return await NotificationService(db).mark_read(user, notification_id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: int, user: CurrentUser, db: DB):
    await NotificationService(db).delete(user, notification_id)
