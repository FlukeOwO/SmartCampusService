"""
Request service - คำร้อง/แจ้งปัญหา, ไฟล์แนบ, มอบหมายงาน

สิทธิ์ระดับข้อมูล: นักศึกษาเห็น/แก้ได้เฉพาะคำร้องของตัวเอง, staff/admin เห็นทั้งหมด
ไฟล์แนบเก็บที่ requests/{request_id}/{uuid}.{ext} ใน bucket private
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.base_models import PageParams
from app.common.constants import (
    REQUEST_STATUS_TRANSITIONS,
    STAFF_ROLES,
    RequestPriority,
    RequestStatus,
    RequestType,
)
from app.common.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.common.storage import get_storage, read_validated_upload
from app.core.config import settings
from app.models import Request, RequestAttachment, User
from app.modules.notifications.service import (
    notify_request_assigned,
    notify_request_created,
    notify_request_status,
)
from app.schemas.request import (
    RequestAssign,
    RequestCreate,
    RequestFeedback,
    RequestUpdate,
    RequestUpdateStatus,
)

logger = logging.getLogger(__name__)


def _new_request_number() -> str:
    return f"REQ-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


class RequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------------- load
    async def _load(self, request_id: int, for_update: bool = False) -> Request:
        query = (
            select(Request)
            .where(Request.id == request_id)
            .options(selectinload(Request.attachments))
            .execution_options(populate_existing=True)
        )
        if for_update:
            query = query.with_for_update(of=Request)
        request = await self.db.scalar(query)
        if request is None:
            raise NotFoundException("Request not found")
        return request

    async def _load_accessible(self, user: User, request_id: int, for_update: bool = False):
        request = await self._load(request_id, for_update)
        if request.user_id != user.id and not _is_staff(user):
            raise ForbiddenException("You can only access your own requests")
        return request

    async def _load_owned(self, user: User, request_id: int) -> Request:
        request = await self._load(request_id, for_update=True)
        if request.user_id != user.id:
            raise ForbiddenException("You can only modify your own requests")
        return request

    async def get(self, user: User, request_id: int) -> Request:
        return await self._load_accessible(user, request_id)

    async def _commit_and_reload(self, request_id: int) -> Request:
        await self.db.commit()
        return await self._load(request_id)

    # --------------------------------------------------------------- create
    async def create(self, user: User, data: RequestCreate, files: list[UploadFile]) -> Request:
        if len(files) > settings.MAX_FILES_PER_REQUEST:
            raise ValidationException(f"At most {settings.MAX_FILES_PER_REQUEST} files per request")
        # ตรวจไฟล์ทั้งหมดก่อนแตะ DB
        uploads = [await read_validated_upload(f) + (f.filename or "file",) for f in files]

        request = Request(
            **{k: getattr(v, "value", v) for k, v in data.model_dump().items()},
            user_id=user.id,
            request_number=_new_request_number(),
            status=RequestStatus.PENDING.value,
        )
        self.db.add(request)
        try:
            await self.db.flush()
        except IntegrityError:
            # request_number ชนกัน (โอกาสน้อยมาก) - ลองอีกครั้งด้วยเลขใหม่
            await self.db.rollback()
            request.request_number = _new_request_number()
            self.db.add(request)
            await self.db.flush()

        saved_keys = await self._store_files(request.id, uploads)
        notify_request_created(self.db, request)
        try:
            return await self._commit_and_reload(request.id)
        except Exception:
            await self._cleanup(saved_keys)
            raise

    # ---------------------------------------------------------- attachments
    async def add_attachments(self, user: User, request_id: int, files: list[UploadFile]):
        request = await self._load_owned(user, request_id)
        if request.status not in (RequestStatus.PENDING.value, RequestStatus.IN_PROGRESS.value):
            raise ValidationException("Cannot attach files to a closed request")
        if not files:
            raise ValidationException("No files provided")
        if len(request.attachments) + len(files) > settings.MAX_FILES_PER_REQUEST:
            raise ValidationException(f"At most {settings.MAX_FILES_PER_REQUEST} files per request")
        uploads = [await read_validated_upload(f) + (f.filename or "file",) for f in files]
        saved_keys = await self._store_files(request.id, uploads)
        try:
            return await self._commit_and_reload(request.id)
        except Exception:
            await self._cleanup(saved_keys)
            raise

    async def _store_files(self, request_id: int, uploads) -> list[str]:
        storage = get_storage()
        saved: list[str] = []
        try:
            for data, ext, content_type, original_name in uploads:
                key = f"requests/{request_id}/{uuid.uuid4().hex}{ext}"
                await storage.save(key, data, content_type)
                saved.append(key)
                self.db.add(
                    RequestAttachment(
                        request_id=request_id,
                        filename=original_name[:255],
                        file_path=key,
                        file_url="",  # ไม่เก็บ public URL - ขอ signed URL ตอนเปิดไฟล์
                        file_size=len(data),
                        file_type=content_type,
                    )
                )
            await self.db.flush()
        except Exception:
            await self._cleanup(saved)
            raise
        return saved

    async def _cleanup(self, keys: list[str]) -> None:
        storage = get_storage()
        for key in keys:
            await storage.delete(key)

    async def attachment_url(self, user: User, request_id: int, attachment_id: int) -> str:
        request = await self._load_accessible(user, request_id)
        attachment = next((a for a in request.attachments if a.id == attachment_id), None)
        if attachment is None:
            raise NotFoundException("Attachment not found")
        return await get_storage().signed_url(attachment.file_path, attachment.filename)

    # ----------------------------------------------------------------- list
    async def list(
        self,
        params: PageParams,
        user_id: int | None = None,
        status: RequestStatus | None = None,
        request_type: RequestType | None = None,
        priority: RequestPriority | None = None,
        assigned_staff_id: int | None = None,
        search: str | None = None,
    ) -> tuple[list[Request], int]:
        query = select(Request)
        if user_id is not None:
            query = query.where(Request.user_id == user_id)
        if status is not None:
            query = query.where(Request.status == status.value)
        if request_type is not None:
            query = query.where(Request.request_type == request_type.value)
        if priority is not None:
            query = query.where(Request.priority == priority.value)
        if assigned_staff_id is not None:
            query = query.where(Request.assigned_staff_id == assigned_staff_id)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                Request.title.ilike(pattern) | Request.request_number.ilike(pattern)
            )
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.scalars(
            query.order_by(Request.created_at.desc(), Request.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return list(rows), total or 0

    # --------------------------------------------------------------- update
    async def update(self, user: User, request_id: int, data: RequestUpdate) -> Request:
        request = await self._load_owned(user, request_id)
        if request.status != RequestStatus.PENDING.value:
            raise ValidationException("Only pending requests can be edited")
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is None and field in {"title", "description", "request_type", "priority"}:
                continue
            setattr(request, field, getattr(value, "value", value))
        return await self._commit_and_reload(request.id)

    async def cancel(self, user: User, request_id: int) -> Request:
        request = await self._load_owned(user, request_id)
        if request.status != RequestStatus.PENDING.value:
            raise ValidationException("Only pending requests can be cancelled")
        request.status = RequestStatus.CANCELLED.value
        return await self._commit_and_reload(request.id)

    async def feedback(self, user: User, request_id: int, data: RequestFeedback) -> Request:
        request = await self._load_owned(user, request_id)
        if request.status != RequestStatus.COMPLETED.value:
            raise ValidationException("Feedback is only allowed for completed requests")
        request.rating = data.rating
        request.feedback = data.feedback
        return await self._commit_and_reload(request.id)

    async def update_status(
        self, staff: User, request_id: int, data: RequestUpdateStatus
    ) -> Request:
        request = await self._load(request_id, for_update=True)
        new_status = data.status.value
        allowed = REQUEST_STATUS_TRANSITIONS.get(request.status, set())
        if new_status not in allowed:
            raise ValidationException(
                f"Cannot change status from {request.status} to {new_status}",
                details={"allowed": sorted(allowed)},
            )
        now = datetime.now(UTC)
        request.status = new_status
        if data.status_notes is not None:
            request.status_notes = data.status_notes
        if new_status == RequestStatus.IN_PROGRESS.value:
            request.started_at = now
            if request.assigned_staff_id is None:
                request.assigned_staff_id = staff.id
                request.assigned_at = now
        elif new_status == RequestStatus.COMPLETED.value:
            request.completed_at = now
            request.resolved_at = now
            request.resolution = data.resolution
        elif new_status == RequestStatus.REJECTED.value:
            request.rejection_reason = data.rejection_reason
        notify_request_status(self.db, request)
        return await self._commit_and_reload(request.id)

    async def assign(self, staff: User, request_id: int, data: RequestAssign) -> Request:
        request = await self._load(request_id, for_update=True)
        if request.status not in REQUEST_STATUS_TRANSITIONS:
            raise ValidationException("Cannot assign a closed request")
        assignee = await self.db.get(User, data.assigned_staff_id)
        if assignee is None or not assignee.is_active or not _is_staff(assignee):
            raise ValidationException("Assignee must be an active staff or admin user")
        request.assigned_staff_id = assignee.id
        request.assigned_at = datetime.now(UTC)
        notify_request_assigned(self.db, request, assignee.id)
        return await self._commit_and_reload(request.id)
