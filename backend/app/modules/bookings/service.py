"""
Booking service - จองห้อง/อุปกรณ์ และกันการจองซ้อน 2 ชั้น

ชั้นที่ 1 (ในแอป): SELECT ... FOR UPDATE ล็อกแถวห้อง/อุปกรณ์ ทำให้ request ที่แย่ง
        ทรัพยากรเดียวกันต้องเข้าคิวกัน แล้วตรวจเวลาทับก่อน insert
ชั้นที่ 2 (ใน DB): exclusion constraint no_overlap_room / no_overlap_equipment
        ถ้ามีการจองทับหลุดมาได้ DB จะปฏิเสธ (SQLSTATE 23P01) ซึ่งแปลงเป็น 409
ล็อกถูกปล่อยตอน commit ซึ่งเป็นจุดจบของ use case
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import PageParams
from app.common.constants import (
    ACTIVE_BOOKING_STATUSES,
    BOOKING_MAX_ADVANCE_DAYS,
    BOOKING_MIN_MINUTES,
    EQUIPMENT_BOOKING_MAX_DAYS,
    ROOM_BOOKING_MAX_HOURS,
    STAFF_ROLES,
    BookingStatus,
    EquipmentStatus,
    NotificationType,
    RoomStatus,
)
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models import Booking, Equipment, Room, User
from app.modules.notifications.service import notify_booking
from app.schemas.booking import BookingCreateEquipment, BookingCreateRoom

EXCLUSION_VIOLATION = "23P01"


@dataclass(frozen=True)
class _Target:
    model: type[Room] | type[Equipment]
    column: object  # Booking.room_id / Booking.equipment_id
    label: str
    available_status: str
    max_duration: timedelta


ROOM = _Target(
    Room,
    Booking.room_id,
    "Room",
    RoomStatus.AVAILABLE.value,
    timedelta(hours=ROOM_BOOKING_MAX_HOURS),
)
EQUIPMENT = _Target(
    Equipment,
    Booking.equipment_id,
    "Equipment",
    EquipmentStatus.AVAILABLE.value,
    timedelta(days=EQUIPMENT_BOOKING_MAX_DAYS),
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValidationException("Datetime values must include a timezone offset")
    return value.astimezone(UTC)


def _is_exclusion_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    for candidate in (orig, getattr(orig, "__cause__", None)):
        if getattr(candidate, "sqlstate", None) == EXCLUSION_VIOLATION:
            return True
    return False


def validate_booking_window(start: datetime, end: datetime, max_duration: timedelta) -> None:
    now = datetime.now(UTC)
    if start >= end:
        raise ValidationException("start_time must be before end_time")
    if start < now:
        raise ValidationException("Cannot book a time in the past")
    duration = end - start
    if duration < timedelta(minutes=BOOKING_MIN_MINUTES):
        raise ValidationException(f"Booking must be at least {BOOKING_MIN_MINUTES} minutes")
    if duration > max_duration:
        raise ValidationException(f"Booking cannot be longer than {max_duration}")
    if start > now + timedelta(days=BOOKING_MAX_ADVANCE_DAYS):
        raise ValidationException(
            f"Cannot book more than {BOOKING_MAX_ADVANCE_DAYS} days in advance"
        )


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------------- create
    async def create_room_booking(self, user: User, data: BookingCreateRoom) -> Booking:
        return await self._create(user, ROOM, data.room_id, data)

    async def create_equipment_booking(self, user: User, data: BookingCreateEquipment) -> Booking:
        return await self._create(user, EQUIPMENT, data.equipment_id, data)

    async def _create(
        self,
        user: User,
        target: _Target,
        resource_id: int,
        data: BookingCreateRoom | BookingCreateEquipment,
    ) -> Booking:
        # 1) validate เวลา (เทียบเป็น UTC เสมอ)
        start, end = _utc(data.start_time), _utc(data.end_time)
        validate_booking_window(start, end, target.max_duration)

        # 2) ล็อกแถวทรัพยากร - request อื่นที่จองตัวเดียวกันจะรอจน transaction นี้จบ
        resource = await self.db.scalar(
            select(target.model).where(target.model.id == resource_id).with_for_update()
        )
        if resource is None:
            raise NotFoundException(f"{target.label} not found")

        # 3) สถานะทรัพยากรและความจุ
        if not resource.is_bookable or resource.status != target.available_status:
            raise ValidationException(
                f"{target.label} is not available for booking (status: {resource.status})"
            )
        if (
            target is ROOM
            and data.attendees_count is not None
            and data.attendees_count > resource.capacity
        ):
            raise ValidationException(
                f"attendees_count ({data.attendees_count}) exceeds room capacity "
                f"({resource.capacity})"
            )

        # 4) หาการจองที่ทับเวลา
        if await self._has_overlap(target, resource_id, start, end):
            raise ConflictException(f"{target.label} is already booked for this time slot")

        # 5) insert เป็น pending แล้ว commit (ปล่อยล็อก)
        fields = data.model_dump(exclude={"start_time", "end_time", "room_id", "equipment_id"})
        booking = Booking(
            **fields,
            user_id=user.id,
            room_id=resource_id if target is ROOM else None,
            equipment_id=resource_id if target is EQUIPMENT else None,
            start_time=start,
            end_time=end,
            status=BookingStatus.PENDING.value,
        )
        self.db.add(booking)
        await self._flush_or_conflict(target.label)
        notify_booking(self.db, booking, NotificationType.BOOKING_CREATED)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def _has_overlap(
        self,
        target: _Target,
        resource_id: int,
        start: datetime,
        end: datetime,
        exclude_booking_id: int | None = None,
    ) -> bool:
        query = select(Booking.id).where(
            target.column == resource_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_time < end,
            Booking.end_time > start,
        )
        if exclude_booking_id is not None:
            query = query.where(Booking.id != exclude_booking_id)
        return bool(await self.db.scalar(select(query.exists())))

    async def _flush_or_conflict(self, label: str) -> None:
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            if _is_exclusion_violation(exc):
                raise ConflictException(f"{label} is already booked for this time slot") from exc
            raise

    # ------------------------------------------------------------------ query
    async def _get_for_update(self, booking_id: int) -> Booking:
        booking = await self.db.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if booking is None:
            raise NotFoundException("Booking not found")
        return booking

    async def get_booking(self, user: User, booking_id: int) -> Booking:
        booking = await self.db.get(Booking, booking_id)
        if booking is None:
            raise NotFoundException("Booking not found")
        if booking.user_id != user.id and user.role not in STAFF_ROLES:
            raise ForbiddenException("You can only view your own bookings")
        return booking

    async def list_bookings(
        self,
        params: PageParams,
        user_id: int | None = None,
        status: BookingStatus | None = None,
        room_id: int | None = None,
        equipment_id: int | None = None,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
    ) -> tuple[list[Booking], int]:
        query = select(Booking)
        if user_id is not None:
            query = query.where(Booking.user_id == user_id)
        if status is not None:
            query = query.where(Booking.status == status.value)
        if room_id is not None:
            query = query.where(Booking.room_id == room_id)
        if equipment_id is not None:
            query = query.where(Booking.equipment_id == equipment_id)
        if start_from is not None:
            query = query.where(Booking.start_time >= _utc(start_from))
        if start_to is not None:
            query = query.where(Booking.start_time < _utc(start_to))
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.scalars(
            query.order_by(Booking.start_time.desc(), Booking.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return list(rows), total or 0

    async def availability(
        self, target_name: str, resource_id: int, start: datetime, end: datetime
    ) -> dict:
        target = ROOM if target_name == "room" else EQUIPMENT
        start, end = _utc(start), _utc(end)
        if start >= end:
            raise ValidationException("start_time must be before end_time")
        if end - start > timedelta(days=31):
            raise ValidationException("Availability window cannot exceed 31 days")
        resource = await self.db.get(target.model, resource_id)
        if resource is None:
            raise NotFoundException(f"{target.label} not found")
        rows = await self.db.execute(
            select(Booking.start_time, Booking.end_time)
            .where(
                target.column == resource_id,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
                Booking.start_time < end,
                Booking.end_time > start,
            )
            .order_by(Booking.start_time)
        )
        busy = [{"start_time": s, "end_time": e} for s, e in rows.all()]
        bookable = resource.is_bookable and resource.status == target.available_status
        return {
            "available": bookable and not busy,
            "resource_type": target_name,
            "resource_id": resource_id,
            "start_time": start,
            "end_time": end,
            "busy_slots": busy,
        }

    # ------------------------------------------------------------- workflow
    async def approve(self, staff: User, booking_id: int) -> Booking:
        booking = await self._get_for_update(booking_id)
        if booking.status != BookingStatus.PENDING.value:
            raise ValidationException(
                f"Only pending bookings can be approved (is {booking.status})"
            )
        booking.status = BookingStatus.CONFIRMED.value
        booking.approved_by = staff.id
        booking.approved_at = datetime.now(UTC)
        notify_booking(self.db, booking, NotificationType.BOOKING_CONFIRMED)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def reject(self, staff: User, booking_id: int, reason: str) -> Booking:
        booking = await self._get_for_update(booking_id)
        if booking.status != BookingStatus.PENDING.value:
            raise ValidationException(
                f"Only pending bookings can be rejected (is {booking.status})"
            )
        booking.status = BookingStatus.REJECTED.value
        booking.rejection_reason = reason
        booking.approved_by = staff.id
        booking.approved_at = datetime.now(UTC)
        notify_booking(self.db, booking, NotificationType.BOOKING_REJECTED, reason)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def cancel(self, user: User, booking_id: int, reason: str) -> Booking:
        booking = await self._get_for_update(booking_id)
        is_staff = user.role in STAFF_ROLES
        if booking.user_id != user.id and not is_staff:
            raise ForbiddenException("You can only cancel your own bookings")
        if booking.status not in ACTIVE_BOOKING_STATUSES:
            raise ValidationException(f"Booking cannot be cancelled (is {booking.status})")
        if not is_staff and booking.start_time <= datetime.now(UTC):
            raise ValidationException("Bookings that have already started cannot be cancelled")
        booking.status = BookingStatus.CANCELLED.value
        booking.cancellation_reason = reason
        notify_booking(self.db, booking, NotificationType.BOOKING_CANCELLED, reason)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking
