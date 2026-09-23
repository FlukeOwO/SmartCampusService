"""
Request Service - Business Logic สำหรับ Request Management
"""

from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.constants import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_DOCUMENT_SIZE_MB,
    MAX_IMAGE_SIZE_MB,
    RequestPriority,
    RequestStatus,
    RequestType,
    UserRole,
)
from app.common.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.common.storage import get_file_extension, get_storage_service, validate_file_type
from app.models import Request, RequestAttachment, User
from app.schemas.request import RequestCreate, RequestUpdate, RequestUpdateStatus


class RequestService:
    """Service สำหรับจัดการ Requests"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_service()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _generate_request_number(self) -> str:
        """
        สร้างเลขที่คำร้องแบบ unique
        Format: REQ-YYYYMMDD-XXXXXX (XXXXXX = random 6 digits)
        """
        import random

        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
        return f"REQ-{timestamp}-{random_digits}"

    async def _get_request_by_id(
        self, request_id: int, with_attachments: bool = False
    ) -> Request:
        """ดึง Request โดย ID"""
        query = select(Request).where(Request.id == request_id)

        if with_attachments:
            query = query.options(selectinload(Request.attachments))

        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request:
            raise NotFoundException(f"Request with ID {request_id} not found")

        return request

    def _can_user_access_request(self, request: Request, user: User) -> bool:
        """ตรวจสอบว่า User สามารถเข้าถึง Request นี้ได้หรือไม่"""
        # Admin และ Staff เข้าถึงได้ทั้งหมด
        if user.role in [UserRole.ADMIN.value, UserRole.STAFF.value]:
            return True

        # Student เข้าถึงได้เฉพาะของตัวเอง
        return request.user_id == user.id

    def _can_user_modify_request(self, request: Request, user: User) -> bool:
        """ตรวจสอบว่า User สามารถแก้ไข Request ได้หรือไม่"""
        # เฉพาะเจ้าของ Request แก้ไขได้ และต้องเป็นสถานะ PENDING หรือ REJECTED
        if request.user_id != user.id:
            return False

        return request.status in [RequestStatus.PENDING.value, RequestStatus.REJECTED.value]

    # ========================================================================
    # Create Request
    # ========================================================================

    async def create_request(
        self,
        request_data: RequestCreate,
        user: User,
        files: list[UploadFile] | None = None,
    ) -> Request:
        """
        สร้าง Request ใหม่
        
        Args:
            request_data: ข้อมูล Request
            user: ผู้สร้าง Request
            files: ไฟล์แนบ (optional)
        
        Returns:
            Request object ที่สร้างแล้ว
        """
        # สร้าง Request object
        request = Request(
            user_id=user.id,
            request_number=self._generate_request_number(),
            title=request_data.title,
            description=request_data.description,
            request_type=request_data.request_type.value,
            priority=request_data.priority.value,
            location=request_data.location,
            contact_phone=request_data.contact_phone,
            status=RequestStatus.PENDING.value,
        )

        self.db.add(request)
        await self.db.flush()  # เพื่อให้ได้ request.id

        # Upload files ถ้ามี
        if files:
            for file in files:
                await self._add_attachment(request, file)

        await self.db.commit()
        await self.db.refresh(request)

        # Load relationships
        await self.db.refresh(request, ["attachments"])

        return request

    # ========================================================================
    # File Attachment
    # ========================================================================

    async def _add_attachment(self, request: Request, file: UploadFile) -> RequestAttachment:
        """
        เพิ่มไฟล์แนบให้กับ Request
        
        Args:
            request: Request object
            file: UploadFile
        
        Returns:
            RequestAttachment object
        
        Raises:
            ValidationException: ถ้าไฟล์ไม่ถูกต้อง
        """
        # ตรวจสอบ file extension
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS
        if not validate_file_type(file.filename or "", allowed_extensions):
            raise ValidationException(
                f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # ตรวจสอบขนาดไฟล์
        ext = get_file_extension(file.filename or "")
        max_size = (
            MAX_IMAGE_SIZE_MB
            if ext in ALLOWED_IMAGE_EXTENSIONS
            else MAX_DOCUMENT_SIZE_MB
        )

        # Upload file
        upload_result = await self.storage.upload(
            file=file,
            folder=f"requests/{request.id}",
            max_size_mb=max_size,
        )

        # สร้าง RequestAttachment
        attachment = RequestAttachment(
            request_id=request.id,
            filename=upload_result["filename"],
            file_path=upload_result["path"],
            file_url=upload_result["url"],
            file_size=upload_result["size"],
            file_type=file.content_type,
        )

        self.db.add(attachment)
        return attachment

    async def add_attachments_to_request(
        self,
        request_id: int,
        user: User,
        files: list[UploadFile],
    ) -> Request:
        """
        เพิ่มไฟล์แนบให้กับ Request ที่มีอยู่แล้ว
        
        Args:
            request_id: ID ของ Request
            user: User ที่เพิ่มไฟล์
            files: ไฟล์แนบ
        
        Returns:
            Request object ที่อัปเดตแล้ว
        """
        request = await self._get_request_by_id(request_id, with_attachments=True)

        # ตรวจสอบสิทธิ์
        if not self._can_user_modify_request(request, user):
            raise ForbiddenException("You cannot add attachments to this request")

        # เพิ่มไฟล์
        for file in files:
            await self._add_attachment(request, file)

        await self.db.commit()
        await self.db.refresh(request, ["attachments"])

        return request

    # ========================================================================
    # Get Requests
    # ========================================================================

    async def get_request_by_id(self, request_id: int, user: User) -> Request:
        """
        ดึงข้อมูล Request โดย ID
        
        Args:
            request_id: ID ของ Request
            user: User ที่ขอข้อมูล
        
        Returns:
            Request object
        """
        request = await self._get_request_by_id(request_id, with_attachments=True)

        # ตรวจสอบสิทธิ์
        if not self._can_user_access_request(request, user):
            raise ForbiddenException("You do not have permission to access this request")

        return request

    async def get_user_requests(
        self,
        user: User,
        status: Optional[RequestStatus] = None,
        request_type: Optional[RequestType] = None,
        priority: Optional[RequestPriority] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Request], int]:
        """
        ดึงรายการ Requests ของ User
        
        Args:
            user: User
            status: Filter by status (optional)
            request_type: Filter by type (optional)
            priority: Filter by priority (optional)
            skip: Pagination offset
            limit: Pagination limit
        
        Returns:
            Tuple of (requests, total_count)
        """
        # Build query
        query = select(Request).where(Request.user_id == user.id)

        # Apply filters
        if status:
            query = query.where(Request.status == status.value)
        if request_type:
            query = query.where(Request.request_type == request_type.value)
        if priority:
            query = query.where(Request.priority == priority.value)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination and ordering
        query = query.order_by(Request.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    async def get_all_requests(
        self,
        status: Optional[RequestStatus] = None,
        request_type: Optional[RequestType] = None,
        priority: Optional[RequestPriority] = None,
        assigned_staff_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Request], int]:
        """
        ดึงรายการ Requests ทั้งหมด (สำหรับ Staff/Admin)
        
        Args:
            status: Filter by status (optional)
            request_type: Filter by type (optional)
            priority: Filter by priority (optional)
            assigned_staff_id: Filter by assigned staff (optional)
            search: Search in title/description (optional)
            skip: Pagination offset
            limit: Pagination limit
        
        Returns:
            Tuple of (requests, total_count)
        """
        # Build query
        query = select(Request)

        # Apply filters
        if status:
            query = query.where(Request.status == status.value)
        if request_type:
            query = query.where(Request.request_type == request_type.value)
        if priority:
            query = query.where(Request.priority == priority.value)
        if assigned_staff_id:
            query = query.where(Request.assigned_staff_id == assigned_staff_id)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Request.title.ilike(search_pattern),
                    Request.description.ilike(search_pattern),
                    Request.request_number.ilike(search_pattern),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination and ordering
        query = query.order_by(Request.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    # ========================================================================
    # Update Request
    # ========================================================================

    async def update_request(
        self,
        request_id: int,
        user: User,
        request_data: RequestUpdate,
    ) -> Request:
        """
        อัปเดตข้อมูล Request (โดยเจ้าของ Request)
        
        Args:
            request_id: ID ของ Request
            user: User ที่แก้ไข
            request_data: ข้อมูลที่ต้องการอัปเดต
        
        Returns:
            Request object ที่อัปเดตแล้ว
        """
        request = await self._get_request_by_id(request_id)

        # ตรวจสอบสิทธิ์
        if not self._can_user_modify_request(request, user):
            raise ForbiddenException(
                "You cannot modify this request or request status does not allow modification"
            )

        # อัปเดตข้อมูล
        update_data = request_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(request, key):
                # Convert enum to value
                if isinstance(value, (RequestType, RequestPriority)):
                    value = value.value
                setattr(request, key, value)

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # ========================================================================
    # Update Status (Staff/Admin)
    # ========================================================================

    async def update_request_status(
        self,
        request_id: int,
        user: User,
        status_data: RequestUpdateStatus,
    ) -> Request:
        """
        อัปเดตสถานะ Request (โดย Staff/Admin)
        
        Args:
            request_id: ID ของ Request
            user: Staff/Admin ที่อัปเดต
            status_data: ข้อมูลสถานะใหม่
        
        Returns:
            Request object ที่อัปเดตแล้ว
        """
        request = await self._get_request_by_id(request_id)

        # อัปเดตสถานะ
        old_status = request.status
        request.status = status_data.status.value
        request.status_notes = status_data.status_notes

        # อัปเดต timestamps ตามสถานะ
        now = datetime.utcnow()

        if status_data.status == RequestStatus.IN_PROGRESS and old_status == RequestStatus.PENDING.value:
            request.started_at = now

        elif status_data.status == RequestStatus.COMPLETED:
            request.completed_at = now
            request.resolved_at = now
            request.resolution = status_data.resolution

        elif status_data.status == RequestStatus.REJECTED:
            request.rejection_reason = status_data.rejection_reason

        await self.db.commit()
        await self.db.refresh(request)

        # TODO: สร้าง Notification สำหรับเจ้าของ Request

        return request

    # ========================================================================
    # Assign Request (Staff/Admin)
    # ========================================================================

    async def assign_request(
        self,
        request_id: int,
        assigned_staff_id: int,
        user: User,
    ) -> Request:
        """
        มอบหมายงานให้กับ Staff
        
        Args:
            request_id: ID ของ Request
            assigned_staff_id: ID ของ Staff ที่จะรับผิดชอบ
            user: Admin/Staff ที่มอบหมาย
        
        Returns:
            Request object ที่อัปเดตแล้ว
        """
        request = await self._get_request_by_id(request_id)

        # ตรวจสอบว่า assigned_staff เป็น Staff หรือ Admin จริง
        staff_query = select(User).where(User.id == assigned_staff_id)
        staff_result = await self.db.execute(staff_query)
        staff = staff_result.scalar_one_or_none()

        if not staff:
            raise NotFoundException(f"User with ID {assigned_staff_id} not found")

        if staff.role not in [UserRole.STAFF.value, UserRole.ADMIN.value]:
            raise ValidationException("Can only assign to staff or admin users")

        # มอบหมายงาน
        request.assigned_staff_id = assigned_staff_id

        if not request.assigned_at:
            request.assigned_at = datetime.utcnow()

        # ถ้ายังเป็น PENDING ให้เปลี่ยนเป็น IN_PROGRESS
        if request.status == RequestStatus.PENDING.value:
            request.status = RequestStatus.IN_PROGRESS.value
            request.started_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(request)

        # TODO: สร้าง Notification สำหรับ Staff ที่ถูกมอบหมาย

        return request

    # ========================================================================
    # Cancel Request (User)
    # ========================================================================

    async def cancel_request(self, request_id: int, user: User) -> Request:
        """
        ยกเลิก Request (โดยเจ้าของ Request)
        
        Args:
            request_id: ID ของ Request
            user: User ที่ยกเลิก
        
        Returns:
            Request object ที่อัปเดตแล้ว
        """
        request = await self._get_request_by_id(request_id)

        # ตรวจสอบสิทธิ์
        if request.user_id != user.id:
            raise ForbiddenException("You can only cancel your own requests")

        # ตรวจสอบสถานะ
        if request.status in [
            RequestStatus.COMPLETED.value,
            RequestStatus.CANCELLED.value,
        ]:
            raise ValidationException(
                f"Cannot cancel request with status {request.status}"
            )

        request.status = RequestStatus.CANCELLED.value

        await self.db.commit()
        await self.db.refresh(request)

        return request
