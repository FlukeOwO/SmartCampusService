"""
Notification Service - Business Logic สำหรับ Notification System
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import NotificationType
from app.common.exceptions import ForbiddenException, NotFoundException
from app.models import Notification, User
from app.schemas.notification import NotificationCreate


class NotificationService:
    """Service สำหรับจัดการ Notifications"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Create Notification
    # ========================================================================

    async def create_notification(
        self,
        notification_data: NotificationCreate,
    ) -> Notification:
        """
        สร้าง Notification ใหม่
        
        Args:
            notification_data: ข้อมูล Notification
        
        Returns:
            Notification object ที่สร้างแล้ว
        """
        notification = Notification(
            user_id=notification_data.user_id,
            notification_type=notification_data.notification_type.value,
            title=notification_data.title,
            message=notification_data.message,
            related_resource_type=notification_data.related_resource_type,
            related_resource_id=notification_data.related_resource_id,
            action_url=notification_data.action_url,
            is_read=False,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    async def create_notification_for_user(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_resource_type: Optional[str] = None,
        related_resource_id: Optional[int] = None,
        action_url: Optional[str] = None,
    ) -> Notification:
        """
        สร้าง Notification สำหรับผู้ใช้ (Helper method)
        
        Args:
            user_id: ID ของผู้รับ
            notification_type: ประเภทการแจ้งเตือน
            title: หัวข้อ
            message: เนื้อหา
            related_resource_type: ประเภท Resource
            related_resource_id: ID ของ Resource
            action_url: URL สำหรับ Action
        
        Returns:
            Notification object
        """
        notification_data = NotificationCreate(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_resource_type=related_resource_type,
            related_resource_id=related_resource_id,
            action_url=action_url,
        )

        return await self.create_notification(notification_data)

    # ========================================================================
    # Notification Triggers - Request Events
    # ========================================================================

    async def notify_request_created(
        self,
        request_id: int,
        request_number: str,
        user_id: int,
    ) -> None:
        """แจ้งเตือนเมื่อสร้าง Request สำเร็จ"""
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.REQUEST_UPDATE,
            title="คำร้องถูกสร้างเรียบร้อยแล้ว",
            message=f"คำร้องหมายเลข {request_number} ถูกสร้างเรียบร้อยแล้ว รอการดำเนินการ",
            related_resource_type="request",
            related_resource_id=request_id,
            action_url=f"/requests/{request_id}",
        )

    async def notify_request_assigned(
        self,
        request_id: int,
        request_number: str,
        staff_id: int,
        staff_name: str,
        requester_id: int,
    ) -> None:
        """แจ้งเตือนเมื่อ Request ถูกมอบหมาย"""
        # แจ้ง Staff ที่ถูกมอบหมาย
        await self.create_notification_for_user(
            user_id=staff_id,
            notification_type=NotificationType.REQUEST_UPDATE,
            title="คุณได้รับมอบหมายงานใหม่",
            message=f"คำร้องหมายเลข {request_number} ถูกมอบหมายให้คุณ",
            related_resource_type="request",
            related_resource_id=request_id,
            action_url=f"/requests/{request_id}",
        )

        # แจ้งผู้ส่งคำร้อง
        await self.create_notification_for_user(
            user_id=requester_id,
            notification_type=NotificationType.REQUEST_UPDATE,
            title="คำร้องได้รับการมอบหมาย",
            message=f"คำร้องหมายเลข {request_number} ได้รับการมอบหมายให้กับ {staff_name}",
            related_resource_type="request",
            related_resource_id=request_id,
            action_url=f"/requests/{request_id}",
        )

    async def notify_request_status_changed(
        self,
        request_id: int,
        request_number: str,
        user_id: int,
        old_status: str,
        new_status: str,
    ) -> None:
        """แจ้งเตือนเมื่อสถานะ Request เปลี่ยน"""
        status_messages = {
            "in_progress": "กำลังดำเนินการ",
            "completed": "เสร็จสิ้นแล้ว",
            "rejected": "ถูกปฏิเสธ",
            "cancelled": "ถูกยกเลิก",
        }

        status_text = status_messages.get(new_status, new_status)

        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.REQUEST_UPDATE,
            title=f"สถานะคำร้องเปลี่ยนเป็น {status_text}",
            message=f"คำร้องหมายเลข {request_number} เปลี่ยนสถานะเป็น {status_text}",
            related_resource_type="request",
            related_resource_id=request_id,
            action_url=f"/requests/{request_id}",
        )

    # ========================================================================
    # Notification Triggers - Booking Events
    # ========================================================================

    async def notify_booking_created(
        self,
        booking_id: int,
        user_id: int,
        resource_name: str,
        start_time: datetime,
    ) -> None:
        """แจ้งเตือนเมื่อสร้าง Booking สำเร็จ"""
        time_str = start_time.strftime("%d/%m/%Y %H:%M")
        
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            title="การจองถูกสร้างเรียบร้อยแล้ว",
            message=f"การจอง {resource_name} วันที่ {time_str} รอการอนุมัติ",
            related_resource_type="booking",
            related_resource_id=booking_id,
            action_url=f"/bookings/{booking_id}",
        )

    async def notify_booking_confirmed(
        self,
        booking_id: int,
        user_id: int,
        resource_name: str,
        start_time: datetime,
    ) -> None:
        """แจ้งเตือนเมื่อ Booking ได้รับการอนุมัติ"""
        time_str = start_time.strftime("%d/%m/%Y %H:%M")
        
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            title="การจองได้รับการอนุมัติ",
            message=f"การจอง {resource_name} วันที่ {time_str} ได้รับการอนุมัติแล้ว",
            related_resource_type="booking",
            related_resource_id=booking_id,
            action_url=f"/bookings/{booking_id}",
        )

    async def notify_booking_rejected(
        self,
        booking_id: int,
        user_id: int,
        resource_name: str,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """แจ้งเตือนเมื่อ Booking ถูกปฏิเสธ"""
        message = f"การจอง {resource_name} ถูกปฏิเสธ"
        if rejection_reason:
            message += f" เหตุผล: {rejection_reason}"
        
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.BOOKING_CANCELLED,
            title="การจองถูกปฏิเสธ",
            message=message,
            related_resource_type="booking",
            related_resource_id=booking_id,
            action_url=f"/bookings/{booking_id}",
        )

    async def notify_booking_cancelled(
        self,
        booking_id: int,
        user_id: int,
        resource_name: str,
    ) -> None:
        """แจ้งเตือนเมื่อ Booking ถูกยกเลิก"""
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.BOOKING_CANCELLED,
            title="การจองถูกยกเลิก",
            message=f"การจอง {resource_name} ถูกยกเลิกแล้ว",
            related_resource_type="booking",
            related_resource_id=booking_id,
            action_url=f"/bookings/{booking_id}",
        )

    async def notify_booking_reminder(
        self,
        booking_id: int,
        user_id: int,
        resource_name: str,
        start_time: datetime,
    ) -> None:
        """แจ้งเตือนเตือนความจำเกี่ยวกับ Booking ที่กำลังจะถึง"""
        time_str = start_time.strftime("%d/%m/%Y %H:%M")
        
        await self.create_notification_for_user(
            user_id=user_id,
            notification_type=NotificationType.BOOKING_REMINDER,
            title="เตือนความจำ: การจองกำลังจะถึง",
            message=f"การจอง {resource_name} วันที่ {time_str} กำลังจะถึง",
            related_resource_type="booking",
            related_resource_id=booking_id,
            action_url=f"/bookings/{booking_id}",
        )

    # ========================================================================
    # Get Notifications
    # ========================================================================

    async def get_user_notifications(
        self,
        user: User,
        is_read: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Notification], int, dict[str, int]]:
        """
        ดึงรายการ Notifications ของ User
        
        Args:
            user: User
            is_read: Filter by read status (optional)
            notification_type: Filter by type (optional)
            skip: Pagination offset
            limit: Pagination limit
        
        Returns:
            Tuple of (notifications, total_count, stats)
        """
        # Build query
        query = select(Notification).where(Notification.user_id == user.id)

        # Apply filters
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        if notification_type:
            query = query.where(Notification.notification_type == notification_type.value)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get stats
        stats_query = (
            select(
                func.count().label("total"),
                func.sum(func.cast(Notification.is_read, func.INTEGER())).label("read"),
            )
            .where(Notification.user_id == user.id)
        )
        stats_result = await self.db.execute(stats_query)
        stats_row = stats_result.first()
        
        total_all = stats_row.total if stats_row else 0
        read_count = int(stats_row.read) if stats_row and stats_row.read else 0
        unread_count = total_all - read_count

        stats = {
            "total": total_all,
            "read": read_count,
            "unread": unread_count,
        }

        # Apply pagination and ordering
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total, stats

    async def get_notification_by_id(
        self,
        notification_id: int,
        user: User,
    ) -> Notification:
        """
        ดึง Notification โดย ID
        
        Args:
            notification_id: ID ของ Notification
            user: User ที่ขอข้อมูล
        
        Returns:
            Notification object
        
        Raises:
            NotFoundException: ถ้าไม่พบ Notification
            ForbiddenException: ถ้าไม่มีสิทธิ์เข้าถึง
        """
        query = select(Notification).where(Notification.id == notification_id)
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            raise NotFoundException(f"Notification with ID {notification_id} not found")

        # ตรวจสอบสิทธิ์
        if notification.user_id != user.id:
            raise ForbiddenException("You do not have permission to access this notification")

        return notification

    # ========================================================================
    # Mark as Read
    # ========================================================================

    async def mark_notification_as_read(
        self,
        notification_id: int,
        user: User,
    ) -> Notification:
        """
        ทำเครื่องหมายว่าอ่าน Notification แล้ว
        
        Args:
            notification_id: ID ของ Notification
            user: User
        
        Returns:
            Notification object ที่อัปเดตแล้ว
        """
        notification = await self.get_notification_by_id(notification_id, user)

        if not notification.is_read:
            notification.mark_as_read()
            await self.db.commit()
            await self.db.refresh(notification)

        return notification

    async def mark_notifications_as_read(
        self,
        notification_ids: list[int],
        user: User,
    ) -> int:
        """
        ทำเครื่องหมายว่าอ่าน Notifications หลายรายการ
        
        Args:
            notification_ids: List ของ Notification IDs
            user: User
        
        Returns:
            จำนวน Notifications ที่อัปเดต
        """
        # ดึง Notifications ที่เป็นของ User และยังไม่ได้อ่าน
        query = (
            select(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        # ทำเครื่องหมายว่าอ่านแล้ว
        count = 0
        for notification in notifications:
            notification.mark_as_read()
            count += 1

        if count > 0:
            await self.db.commit()

        return count

    async def mark_all_as_read(self, user: User) -> int:
        """
        ทำเครื่องหมายว่าอ่านทั้งหมด
        
        Args:
            user: User
        
        Returns:
            จำนวน Notifications ที่อัปเดต
        """
        query = (
            select(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        count = 0
        for notification in notifications:
            notification.mark_as_read()
            count += 1

        if count > 0:
            await self.db.commit()

        return count

    # ========================================================================
    # Delete Notifications
    # ========================================================================

    async def delete_notification(
        self,
        notification_id: int,
        user: User,
    ) -> bool:
        """
        ลบ Notification
        
        Args:
            notification_id: ID ของ Notification
            user: User
        
        Returns:
            True ถ้าลบสำเร็จ
        """
        notification = await self.get_notification_by_id(notification_id, user)

        await self.db.delete(notification)
        await self.db.commit()

        return True

    async def delete_all_read_notifications(self, user: User) -> int:
        """
        ลบ Notifications ที่อ่านแล้วทั้งหมด
        
        Args:
            user: User
        
        Returns:
            จำนวน Notifications ที่ลบ
        """
        query = (
            select(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.is_read == True,
            )
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        count = len(notifications)
        for notification in notifications:
            await self.db.delete(notification)

        if count > 0:
            await self.db.commit()

        return count
