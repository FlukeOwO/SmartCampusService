"""
Booking Service - Business Logic สำหรับการจอง
ใช้ Pessimistic Locking (SELECT FOR UPDATE) เพื่อป้องกัน Race Condition

Enhanced with:
- Time validation (start < end, no past bookings)
- Resource status checks
- User permission validation
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.constants import BookingStatus, EquipmentStatus, RoomStatus, UserRole
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models import Booking, Equipment, Room, User
from app.schemas.booking import BookingCreateEquipment, BookingCreateRoom


class BookingService:
    """
    Booking Service - จัดการการจองห้องและอุปกรณ์
    
    Features:
        - Pessimistic Locking เพื่อป้องกัน Double Booking
        - ตรวจสอบความพร้อมของห้อง/อุปกรณ์
        - ตรวจสอบ Time Slot ซ้ำซ้อน
        - Validation: เวลา, สถานะ Resource, สิทธิ์ผู้ใช้
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Validation Methods
    # =========================================================================

    def _validate_booking_times(
        self,
        start_time: datetime,
        end_time: datetime,
        min_duration_minutes: int = 15,
        max_duration_hours: int = 24,
        allow_past: bool = False,
    ) -> None:
        """
        ตรวจสอบความถูกต้องของเวลาการจอง
        
        Args:
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
            min_duration_minutes: ระยะเวลาขั้นต่ำ (นาที)
            max_duration_hours: ระยะเวลาสูงสุด (ชั่วโมง)
            allow_past: อนุญาตให้จองย้อนหลังหรือไม่
        
        Raises:
            ValidationException: ถ้าเวลาไม่ถูกต้อง
        """
        now = datetime.utcnow()

        # 1. ตรวจสอบว่า start_time < end_time
        if start_time >= end_time:
            raise ValidationException(
                "Start time must be before end time"
            )

        # 2. ตรวจสอบว่าไม่จองย้อนหลัง (ถ้าไม่อนุญาต)
        if not allow_past and start_time < now:
            raise ValidationException(
                "Cannot create bookings in the past"
            )

        # 3. ตรวจสอบระยะเวลาขั้นต่ำ
        duration = end_time - start_time
        min_duration = timedelta(minutes=min_duration_minutes)
        if duration < min_duration:
            raise ValidationException(
                f"Booking duration must be at least {min_duration_minutes} minutes"
            )

        # 4. ตรวจสอบระยะเวลาสูงสุด
        max_duration = timedelta(hours=max_duration_hours)
        if duration > max_duration:
            raise ValidationException(
                f"Booking duration cannot exceed {max_duration_hours} hours"
            )

        # 5. ตรวจสอบว่าไม่จองล่วงหน้าเกินไป (เช่น 90 วัน)
        max_advance_days = 90
        max_advance = timedelta(days=max_advance_days)
        if start_time > now + max_advance:
            raise ValidationException(
                f"Cannot book more than {max_advance_days} days in advance"
            )

    def _can_user_approve_booking(self, user: User) -> bool:
        """ตรวจสอบว่า User มีสิทธิ์อนุมัติการจองหรือไม่"""
        return user.role in [UserRole.STAFF.value, UserRole.ADMIN.value]

    def _can_user_cancel_booking(self, booking: Booking, user: User) -> bool:
        """ตรวจสอบว่า User สามารถยกเลิกการจองนี้ได้หรือไม่"""
        # เจ้าของสามารถยกเลิกได้
        if booking.user_id == user.id:
            return True

        # Staff/Admin สามารถยกเลิกได้ทุกการจอง
        if user.role in [UserRole.STAFF.value, UserRole.ADMIN.value]:
            return True

        return False

    # =========================================================================
    # Room Booking
    # =========================================================================

    async def create_room_booking(
        self, user_id: int, booking_data: BookingCreateRoom
    ) -> Booking:
        """
        สร้างการจองห้อง พร้อม Transaction Locking และ Enhanced Validation
        
        Process:
            1. Validate booking times (start < end, no past, duration limits)
            2. Lock ห้องด้วย SELECT FOR UPDATE
            3. ตรวจสอบว่าห้องพร้อมใช้งาน และ status
            4. ตรวจสอบว่ามีการจองซ้ำในช่วงเวลานั้นหรือไม่
            5. สร้างการจอง
        
        Args:
            user_id: ID ของผู้จอง
            booking_data: ข้อมูลการจอง
        
        Returns:
            Booking object ที่สร้างแล้ว
        
        Raises:
            ValidationException: เวลาไม่ถูกต้อง, ห้องไม่พร้อมใช้งาน
            NotFoundException: ไม่พบห้อง
            ConflictException: มีการจองซ้ำในช่วงเวลานั้น
        """
        # 1. Validate booking times
        self._validate_booking_times(
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            min_duration_minutes=15,
            max_duration_hours=24,
            allow_past=False,
        )

        async with self.db.begin():
            # 2. Lock ห้อง (Pessimistic Locking)
            room_query = (
                select(Room)
                .where(Room.id == booking_data.room_id)
                .with_for_update()  # SELECT FOR UPDATE - ป้องกัน concurrent access
            )
            result = await self.db.execute(room_query)
            room = result.scalar_one_or_none()

            if not room:
                raise NotFoundException(f"Room ID {booking_data.room_id} not found")

            # 3. ตรวจสอบสถานะห้อง
            if not room.is_bookable:
                raise ValidationException(
                    f"Room {room.room_number} is not bookable"
                )

            if room.status != RoomStatus.AVAILABLE.value:
                raise ValidationException(
                    f"Room {room.room_number} is currently {room.status} and cannot be booked"
                )

            # ตรวจสอบจำนวนผู้เข้าร่วมไม่เกิน capacity
            if booking_data.attendees_count and booking_data.attendees_count > room.capacity:
                raise ValidationException(
                    f"Number of attendees ({booking_data.attendees_count}) exceeds room capacity ({room.capacity})"
                )

            # 4. ตรวจสอบการจองซ้ำ (Conflict Detection)
            conflict = await self._check_room_conflict(
                room_id=booking_data.room_id,
                start_time=booking_data.start_time,
                end_time=booking_data.end_time,
            )

            if conflict:
                raise ConflictException(
                    f"Room {room.room_number} is already booked during this time slot"
                )

            # 5. สร้างการจอง
            booking = Booking(
                user_id=user_id,
                room_id=booking_data.room_id,
                title=booking_data.title,
                description=booking_data.description,
                purpose=booking_data.purpose,
                start_time=booking_data.start_time,
                end_time=booking_data.end_time,
                contact_person=booking_data.contact_person,
                contact_phone=booking_data.contact_phone,
                attendees_count=booking_data.attendees_count,
                notes=booking_data.notes,
                status=BookingStatus.PENDING.value,
            )

            self.db.add(booking)
            await self.db.flush()  # Flush to get ID
            await self.db.refresh(booking)

            return booking

    async def _check_room_conflict(
        self,
        room_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """
        ตรวจสอบว่ามีการจองห้องซ้ำในช่วงเวลานั้นหรือไม่
        
        Conflict occurs when:
            - มีการจองที่ยังใช้งานอยู่ (pending, confirmed)
            - ช่วงเวลาทับซ้อนกัน
        
        Args:
            room_id: ID ของห้อง
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
            exclude_booking_id: ID ของการจองที่ต้องการยกเว้น (สำหรับการแก้ไข)
        
        Returns:
            True ถ้ามีการจองซ้ำ
        """
        # สถานะที่ถือว่ายังใช้งานอยู่
        active_statuses = [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]

        # Query สำหรับตรวจสอบการทับซ้อนของเวลา
        # Overlap occurs when: (start_time < existing_end) AND (end_time > existing_start)
        conflict_query = select(Booking).where(
            and_(
                Booking.room_id == room_id,
                Booking.status.in_(active_statuses),
                Booking.start_time < end_time,
                Booking.end_time > start_time,
            )
        )

        # ยกเว้นการจองที่กำลังแก้ไข
        if exclude_booking_id:
            conflict_query = conflict_query.where(Booking.id != exclude_booking_id)

        result = await self.db.execute(conflict_query)
        conflicting_booking = result.scalar_one_or_none()

        return conflicting_booking is not None

    # =========================================================================
    # Equipment Booking
    # =========================================================================

    async def create_equipment_booking(
        self, user_id: int, booking_data: BookingCreateEquipment
    ) -> Booking:
        """
        สร้างการจองอุปกรณ์ พร้อม Transaction Locking และ Enhanced Validation
        
        Process:
            1. Validate booking times (start < end, no past, duration limits)
            2. Lock อุปกรณ์ด้วย SELECT FOR UPDATE
            3. ตรวจสอบว่าอุปกรณ์พร้อมใช้งาน และ status
            4. ตรวจสอบว่ามีการจองซ้ำในช่วงเวลานั้นหรือไม่
            5. สร้างการจอง
        
        Args:
            user_id: ID ของผู้จอง
            booking_data: ข้อมูลการจอง
        
        Returns:
            Booking object ที่สร้างแล้ว
        
        Raises:
            ValidationException: เวลาไม่ถูกต้อง, อุปกรณ์ไม่พร้อมใช้งาน
            NotFoundException: ไม่พบอุปกรณ์
            ConflictException: มีการจองซ้ำในช่วงเวลานั้น
        """
        # 1. Validate booking times
        self._validate_booking_times(
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            min_duration_minutes=15,
            max_duration_hours=168,  # อุปกรณ์อาจจองได้นานกว่าห้อง (max 7 days)
            allow_past=False,
        )

        async with self.db.begin():
            # 2. Lock อุปกรณ์ (Pessimistic Locking)
            equipment_query = (
                select(Equipment)
                .where(Equipment.id == booking_data.equipment_id)
                .with_for_update()  # SELECT FOR UPDATE
            )
            result = await self.db.execute(equipment_query)
            equipment = result.scalar_one_or_none()

            if not equipment:
                raise NotFoundException(
                    f"Equipment ID {booking_data.equipment_id} not found"
                )

            # 3. ตรวจสอบสถานะอุปกรณ์
            if not equipment.is_bookable:
                raise ValidationException(
                    f"Equipment {equipment.equipment_name} is not bookable"
                )

            if equipment.status != EquipmentStatus.AVAILABLE.value:
                status_messages = {
                    EquipmentStatus.IN_USE.value: "currently in use",
                    EquipmentStatus.MAINTENANCE.value: "under maintenance",
                    EquipmentStatus.BROKEN.value: "broken",
                    EquipmentStatus.RETIRED.value: "retired",
                }
                status_msg = status_messages.get(equipment.status, equipment.status)
                raise ValidationException(
                    f"Equipment {equipment.equipment_name} is {status_msg} and cannot be booked"
                )

            # 4. ตรวจสอบการจองซ้ำ
            conflict = await self._check_equipment_conflict(
                equipment_id=booking_data.equipment_id,
                start_time=booking_data.start_time,
                end_time=booking_data.end_time,
            )

            if conflict:
                raise ConflictException(
                    f"Equipment {equipment.equipment_name} is already booked during this time slot"
                )

            # 5. สร้างการจอง
            booking = Booking(
                user_id=user_id,
                equipment_id=booking_data.equipment_id,
                title=booking_data.title,
                description=booking_data.description,
                purpose=booking_data.purpose,
                start_time=booking_data.start_time,
                end_time=booking_data.end_time,
                contact_person=booking_data.contact_person,
                contact_phone=booking_data.contact_phone,
                notes=booking_data.notes,
                status=BookingStatus.PENDING.value,
            )

            self.db.add(booking)
            await self.db.flush()
            await self.db.refresh(booking)

            return booking

    async def _check_equipment_conflict(
        self,
        equipment_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """
        ตรวจสอบว่ามีการจองอุปกรณ์ซ้ำในช่วงเวลานั้นหรือไม่
        
        Args:
            equipment_id: ID ของอุปกรณ์
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
            exclude_booking_id: ID ของการจองที่ต้องการยกเว้น
        
        Returns:
            True ถ้ามีการจองซ้ำ
        """
        active_statuses = [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]

        conflict_query = select(Booking).where(
            and_(
                Booking.equipment_id == equipment_id,
                Booking.status.in_(active_statuses),
                Booking.start_time < end_time,
                Booking.end_time > start_time,
            )
        )

        if exclude_booking_id:
            conflict_query = conflict_query.where(Booking.id != exclude_booking_id)

        result = await self.db.execute(conflict_query)
        conflicting_booking = result.scalar_one_or_none()

        return conflicting_booking is not None

    # =========================================================================
    # Booking Management
    # =========================================================================

    async def get_booking_by_id(
        self, booking_id: int, load_relations: bool = False
    ) -> Booking:
        """
        ดึงข้อมูลการจองตาม ID
        
        Args:
            booking_id: ID ของการจอง
            load_relations: โหลด relationships (user, room, equipment)
        
        Returns:
            Booking object
        
        Raises:
            NotFoundException: ไม่พบการจอง
        """
        query = select(Booking).where(Booking.id == booking_id)

        if load_relations:
            query = query.options(
                selectinload(Booking.user),
                selectinload(Booking.room),
                selectinload(Booking.equipment),
            )

        result = await self.db.execute(query)
        booking = result.scalar_one_or_none()

        if not booking:
            raise NotFoundException(f"Booking ID {booking_id} not found")

        return booking

    async def get_user_bookings(
        self,
        user_id: int,
        status: Optional[BookingStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Booking]:
        """
        ดึงรายการการจองของผู้ใช้
        
        Args:
            user_id: ID ของผู้ใช้
            status: กรองตามสถานะ (optional)
            limit: จำนวนรายการสูงสุด
            offset: เริ่มต้นจากรายการที่
        
        Returns:
            List of Booking objects
        """
        query = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.start_time.desc())
            .limit(limit)
            .offset(offset)
        )

        if status:
            query = query.where(Booking.status == status.value)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def approve_booking(
        self, booking_id: int, approved_by: int, notes: Optional[str] = None
    ) -> Booking:
        """
        อนุมัติการจอง (สำหรับ Staff/Admin)
        
        Args:
            booking_id: ID ของการจอง
            approved_by: ID ของผู้อนุมัติ
            notes: หมายเหตุเพิ่มเติม
        
        Returns:
            Updated Booking object
        
        Raises:
            NotFoundException: ไม่พบการจอง
            ValidationException: ไม่สามารถอนุมัติได้ (สถานะไม่ถูกต้อง)
        """
        booking = await self.get_booking_by_id(booking_id)

        if booking.status != BookingStatus.PENDING.value:
            raise ValidationException(
                f"Cannot approve booking with status: {booking.status}"
            )

        booking.status = BookingStatus.CONFIRMED.value
        booking.approved_by = approved_by
        booking.approved_at = datetime.utcnow()
        if notes:
            booking.notes = notes

        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    async def reject_booking(
        self, booking_id: int, rejection_reason: str
    ) -> Booking:
        """
        ปฏิเสธการจอง
        
        Args:
            booking_id: ID ของการจอง
            rejection_reason: เหตุผลที่ปฏิเสธ
        
        Returns:
            Updated Booking object
        """
        booking = await self.get_booking_by_id(booking_id)

        if booking.status != BookingStatus.PENDING.value:
            raise ValidationException(
                f"Cannot reject booking with status: {booking.status}"
            )

        booking.status = BookingStatus.REJECTED.value
        booking.rejection_reason = rejection_reason

        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    async def cancel_booking(
        self, booking_id: int, user_id: int, cancellation_reason: str
    ) -> Booking:
        """
        ยกเลิกการจอง (โดยผู้จอง)
        
        Args:
            booking_id: ID ของการจอง
            user_id: ID ของผู้ใช้ (ต้องเป็นเจ้าของการจอง)
            cancellation_reason: เหตุผลที่ยกเลิก
        
        Returns:
            Updated Booking object
        
        Raises:
            NotFoundException: ไม่พบการจอง
            ValidationException: ไม่มีสิทธิ์ยกเลิก หรือสถานะไม่ถูกต้อง
        """
        booking = await self.get_booking_by_id(booking_id)

        # ตรวจสอบว่าเป็นเจ้าของการจองหรือไม่
        if booking.user_id != user_id:
            raise ValidationException("You can only cancel your own bookings")

        # ตรวจสอบสถานะ
        if booking.status not in [
            BookingStatus.PENDING.value,
            BookingStatus.CONFIRMED.value,
        ]:
            raise ValidationException(
                f"Cannot cancel booking with status: {booking.status}"
            )

        booking.status = BookingStatus.CANCELLED.value
        booking.cancellation_reason = cancellation_reason

        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    # =========================================================================
    # Availability Check
    # =========================================================================

    async def check_room_availability(
        self, room_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """
        ตรวจสอบว่าห้องว่างในช่วงเวลาที่ระบุหรือไม่
        
        Args:
            room_id: ID ของห้อง
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
        
        Returns:
            True ถ้าห้องว่าง, False ถ้าไม่ว่าง
        """
        # ตรวจสอบว่าห้องพร้อมใช้งาน
        room = await self.db.get(Room, room_id)
        if not room or not room.is_bookable or room.status != RoomStatus.AVAILABLE.value:
            return False

        # ตรวจสอบการจองซ้ำ
        conflict = await self._check_room_conflict(room_id, start_time, end_time)
        return not conflict

    async def check_equipment_availability(
        self, equipment_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """
        ตรวจสอบว่าอุปกรณ์ว่างในช่วงเวลาที่ระบุหรือไม่
        
        Args:
            equipment_id: ID ของอุปกรณ์
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
        
        Returns:
            True ถ้าอุปกรณ์ว่าง, False ถ้าไม่ว่าง
        """
        # ตรวจสอบว่าอุปกรณ์พร้อมใช้งาน
        equipment = await self.db.get(Equipment, equipment_id)
        if (
            not equipment
            or not equipment.is_bookable
            or equipment.status != EquipmentStatus.AVAILABLE.value
        ):
            return False

        # ตรวจสอบการจองซ้ำ
        conflict = await self._check_equipment_conflict(
            equipment_id, start_time, end_time
        )
        return not conflict
