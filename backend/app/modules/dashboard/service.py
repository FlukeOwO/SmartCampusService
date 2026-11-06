"""
Dashboard service - สถิติภาพรวม (อ่านอย่างเดียว)

เป็นโมดูลรายงานจึง aggregate ข้ามตารางของโมดูลอื่นได้ แต่ไม่เขียนข้อมูลใด ๆ
ทุก query เป็น GROUP BY / COUNT ใน PostgreSQL ไม่ดึงแถวทั้งหมดมานับในแอป
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import (
    ACTIVE_BOOKING_STATUSES,
    REQUEST_STATUS_TRANSITIONS,
    BookingStatus,
    RequestStatus,
)
from app.models import Booking, Request, Room, User

TOP_ROOMS_LIMIT = 5


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _count_by(self, column) -> dict[str, int]:
        rows = await self.db.execute(select(column, func.count()).group_by(column))
        return {str(key): count for key, count in rows.all()}

    async def summary(self, window_days: int) -> dict:
        now = datetime.now(UTC)
        since = now - timedelta(days=window_days)
        return {
            "generated_at": now,
            "window_days": window_days,
            "requests": await self._request_stats(since),
            "bookings": await self._booking_stats(since, now),
            "top_rooms": await self._top_rooms(since),
            "daily": await self._daily(since, now),
            "users_by_role": await self._count_by(User.role),
        }

    async def _request_stats(self, since: datetime) -> dict:
        by_status = await self._count_by(Request.status)
        open_statuses = list(REQUEST_STATUS_TRANSITIONS)  # pending, in_progress
        open_unassigned = await self.db.scalar(
            select(func.count()).where(
                Request.status.in_(open_statuses), Request.assigned_staff_id.is_(None)
            )
        )
        avg_seconds = await self.db.scalar(
            select(
                func.avg(func.extract("epoch", Request.completed_at - Request.created_at))
            ).where(Request.status == RequestStatus.COMPLETED.value)
        )
        created = await self.db.scalar(
            select(func.count()).select_from(Request).where(Request.created_at >= since)
        )
        return {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "by_type": await self._count_by(Request.request_type),
            "by_priority": await self._count_by(Request.priority),
            "open_unassigned": open_unassigned or 0,
            "avg_resolution_hours": round(float(avg_seconds) / 3600, 2) if avg_seconds else None,
            "created_in_window": created or 0,
        }

    async def _booking_stats(self, since: datetime, now: datetime) -> dict:
        by_status = await self._count_by(Booking.status)
        upcoming = await self.db.scalar(
            select(func.count()).where(
                Booking.status == BookingStatus.CONFIRMED.value, Booking.start_time > now
            )
        )
        created = await self.db.scalar(
            select(func.count()).select_from(Booking).where(Booking.created_at >= since)
        )
        return {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "pending_approval": by_status.get(BookingStatus.PENDING.value, 0),
            "upcoming_confirmed": upcoming or 0,
            "created_in_window": created or 0,
        }

    async def _top_rooms(self, since: datetime) -> list[dict]:
        used = (*ACTIVE_BOOKING_STATUSES, BookingStatus.COMPLETED.value)
        rows = await self.db.execute(
            select(Room.id, Room.room_number, Room.room_name, func.count(Booking.id).label("n"))
            .join(Booking, Booking.room_id == Room.id)
            .where(Booking.status.in_(used), Booking.start_time >= since)
            .group_by(Room.id)
            .order_by(func.count(Booking.id).desc(), Room.room_number)
            .limit(TOP_ROOMS_LIMIT)
        )
        return [
            {"room_id": rid, "room_number": number, "room_name": name, "bookings": n}
            for rid, number, name, n in rows.all()
        ]

    async def _daily(self, since: datetime, now: datetime) -> list[dict]:
        # session timezone เป็น UTC (ตั้งใน connect_args) วันที่จึงเป็นวันตาม UTC
        async def per_day(model) -> dict[date, int]:
            day = cast(model.created_at, Date)
            rows = await self.db.execute(
                select(day, func.count()).where(model.created_at >= since).group_by(day)
            )
            return dict(rows.all())

        requests, bookings = await per_day(Request), await per_day(Booking)
        days = (now.date() - since.date()).days
        out = []
        for offset in range(days + 1):
            d = since.date() + timedelta(days=offset)
            out.append({"date": d, "requests": requests.get(d, 0), "bookings": bookings.get(d, 0)})
        return out
