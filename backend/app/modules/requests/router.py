"""
Request router - /api/v1/requests
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi import Request as HttpRequest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import Page, PageParams
from app.common.constants import RequestPriority, RequestStatus, RequestType
from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser, StaffUser
from app.modules.requests.service import RequestService
from app.schemas.request import (
    RequestAssign,
    RequestCreate,
    RequestFeedback,
    RequestListItem,
    RequestResponse,
    RequestUpdate,
    RequestUpdateStatus,
    SignedUrlResponse,
)

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PageParams, Depends()]


def _request_form(
    title: str,
    description: str,
    request_type: RequestType,
    priority: RequestPriority,
    location: str | None,
    contact_phone: str | None,
) -> RequestCreate:
    """Validate form fields with the schema so a short title is 422, not a 500."""
    try:
        return RequestCreate(
            title=title,
            description=description,
            request_type=request_type,
            priority=priority,
            location=location,
            contact_phone=contact_phone,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    user: CurrentUser,
    db: DB,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    request_type: Annotated[RequestType, Form()] = RequestType.OTHER,
    priority: Annotated[RequestPriority, Form()] = RequestPriority.MEDIUM,
    location: Annotated[str | None, Form()] = None,
    contact_phone: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    """สร้างคำร้อง (multipart/form-data) พร้อมไฟล์แนบได้สูงสุด 3 ไฟล์ ไฟล์ละ 8 MB รวมไม่เกิน 24 MB"""
    data = _request_form(title, description, request_type, priority, location, contact_phone)
    return await RequestService(db).create(user, data, files or [])


@router.get("/me", response_model=Page[RequestListItem])
async def my_requests(
    user: CurrentUser,
    db: DB,
    params: Pagination,
    status_filter: RequestStatus | None = Query(None, alias="status"),
):
    items, total = await RequestService(db).list(params, user_id=user.id, status=status_filter)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("", response_model=Page[RequestListItem])
async def all_requests(
    _: StaffUser,
    db: DB,
    params: Pagination,
    status_filter: RequestStatus | None = Query(None, alias="status"),
    request_type: RequestType | None = None,
    priority: RequestPriority | None = None,
    assigned_staff_id: int | None = None,
    search: str | None = Query(None, max_length=100),
):
    """คำร้องทั้งหมด (staff/admin)"""
    items, total = await RequestService(db).list(
        params,
        status=status_filter,
        request_type=request_type,
        priority=priority,
        assigned_staff_id=assigned_staff_id,
        search=search,
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(request_id: int, user: CurrentUser, db: DB):
    return await RequestService(db).get(user, request_id)


@router.patch("/{request_id}", response_model=RequestResponse)
async def update_request(request_id: int, data: RequestUpdate, user: CurrentUser, db: DB):
    """เจ้าของแก้ไขได้ขณะยัง pending"""
    return await RequestService(db).update(user, request_id, data)


@router.post("/{request_id}/cancel", response_model=RequestResponse)
async def cancel_request(request_id: int, user: CurrentUser, db: DB):
    return await RequestService(db).cancel(user, request_id)


@router.post("/{request_id}/feedback", response_model=RequestResponse)
async def request_feedback(request_id: int, data: RequestFeedback, user: CurrentUser, db: DB):
    return await RequestService(db).feedback(user, request_id, data)


@router.patch("/{request_id}/status", response_model=RequestResponse)
async def update_status(request_id: int, data: RequestUpdateStatus, staff: StaffUser, db: DB):
    """pending -> in_progress/rejected, in_progress -> completed/rejected"""
    return await RequestService(db).update_status(staff, request_id, data)


@router.patch("/{request_id}/assign", response_model=RequestResponse)
async def assign_request(request_id: int, data: RequestAssign, staff: StaffUser, db: DB):
    return await RequestService(db).assign(staff, request_id, data)


@router.post("/{request_id}/attachments", response_model=RequestResponse)
async def add_attachments(
    request_id: int,
    user: CurrentUser,
    db: DB,
    files: Annotated[list[UploadFile], File()],
):
    return await RequestService(db).add_attachments(user, request_id, files)


@router.get("/{request_id}/attachments/{attachment_id}/url", response_model=SignedUrlResponse)
async def attachment_url(
    request_id: int, attachment_id: int, user: CurrentUser, db: DB, http_request: HttpRequest
):
    """ออก Signed URL อายุสั้นหลังตรวจสิทธิ์แล้ว"""
    url = await RequestService(db).attachment_url(user, request_id, attachment_id)
    if url.startswith("/"):
        # local storage ตอบเป็น path (/storage/...) ต้องเติม origin ของ backend
        # ไม่งั้น frontend ที่อยู่คนละ origin (localhost:5173) จะเปิดไม่เจอ
        url = str(http_request.base_url).rstrip("/") + url
    return {"url": url, "expires_in_seconds": settings.SIGNED_URL_EXPIRE_MINUTES * 60}
