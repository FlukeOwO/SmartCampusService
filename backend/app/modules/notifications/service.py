"""
Notification service - in-app notification

notify_* ถูกเรียกจาก Service ของคำร้องและการจอง โดย add ลง session เดียวกัน
แล้ว commit พร้อมการเปลี่ยนสถานะ: ถ้าบันทึกสถานะไม่สำเร็จ notification ก็ไม่ถูกสร้าง
"""

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import PageParams
from app.common.constants import NotificationType
from app.common.exceptions import NotFoundException
from app.models import Booking, Notification, Request, User

_BOOKING_LABELS = {
    NotificationType.BOOKING_CREATED: ("ส่งคำขอจองแล้ว", "รอเจ้าหน้าที่อนุมัติการจอง"),
    NotificationType.BOOKING_CONFIRMED: ("การจองได้รับการอนุมัติ", "การจองของคุณได้รับการอนุมัติแล้ว"),
    NotificationType.BOOKING_REJECTED: ("การจองถูกปฏิเสธ", "การจองของคุณถูกปฏิเสธ"),
    NotificationType.BOOKING_CANCELLED: ("การจองถูกยกเลิก", "การจองถูกยกเลิกแล้ว"),
}


def _add(
    db: AsyncSession,
    user_id: int,
    ntype: NotificationType,
    title: str,
    message: str,
    resource_type: str,
    resource_id: int,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            notification_type=ntype.value,
            title=title,
            message=message,
            related_resource_type=resource_type,
            related_resource_id=resource_id,
            action_url=f"/{resource_type}s/{resource_id}",
            is_read=False,
        )
    )


def notify_booking(
    db: AsyncSession, booking: Booking, ntype: NotificationType, reason: str | None = None
) -> None:
    title, message = _BOOKING_LABELS[ntype]
    message = f"{message}: {booking.title}"
    if reason:
        message = f"{message} (เหตุผล: {reason})"
    _add(db, booking.user_id, ntype, title, message, "booking", booking.id)


def notify_request_created(db: AsyncSession, request: Request) -> None:
    _add(
        db,
        request.user_id,
        NotificationType.REQUEST_CREATED,
        "ส่งคำร้องแล้ว",
        f"คำร้อง {request.request_number} ถูกส่งเรียบร้อย",
        "request",
        request.id,
    )


def notify_request_status(db: AsyncSession, request: Request) -> None:
    _add(
        db,
        request.user_id,
        NotificationType.REQUEST_UPDATE,
        "สถานะคำร้องเปลี่ยน",
        f"คำร้อง {request.request_number} เปลี่ยนสถานะเป็น {request.status}",
        "request",
        request.id,
    )


def notify_request_assigned(db: AsyncSession, request: Request, staff_id: int) -> None:
    _add(
        db,
        staff_id,
        NotificationType.REQUEST_ASSIGNED,
        "ได้รับมอบหมายงาน",
        f"คุณได้รับมอบหมายคำร้อง {request.request_number}: {request.title}",
        "request",
        request.id,
    )


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(
        self, user: User, params: PageParams, unread_only: bool
    ) -> tuple[list[Notification], int]:
        query = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return list(rows), total or 0

    async def stats(self, user: User) -> dict:
        total, unread = (
            await self.db.execute(
                select(
                    func.count(),
                    func.count().filter(Notification.is_read.is_(False)),
                ).where(Notification.user_id == user.id)
            )
        ).one()
        return {"total": total, "unread": unread, "read": total - unread}

    async def get_owned(self, user: User, notification_id: int) -> Notification:
        notification = await self.db.get(Notification, notification_id)
        # ของคนอื่นตอบ 404 เหมือนไม่มี เพื่อไม่ให้เดา id ได้
        if notification is None or notification.user_id != user.id:
            raise NotFoundException("Notification not found")
        return notification

    async def mark_read(self, user: User, notification_id: int) -> Notification:
        notification = await self.get_owned(user, notification_id)
        if not notification.is_read:
            notification.mark_as_read()
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user: User) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await self.db.commit()
        return result.rowcount or 0

    async def delete(self, user: User, notification_id: int) -> None:
        notification = await self.get_owned(user, notification_id)
        await self.db.delete(notification)
        await self.db.commit()

    async def delete_read(self, user: User) -> int:
        result = await self.db.execute(
            delete(Notification).where(
                Notification.user_id == user.id, Notification.is_read.is_(True)
            )
        )
        await self.db.commit()
        return result.rowcount or 0
