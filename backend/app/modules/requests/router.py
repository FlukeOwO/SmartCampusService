"""
Request Router - API Endpoints สำหรับ Request Management
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    RequestPriority,
    RequestStatus,
    RequestType,
    UserRole,
)
from app.core.database import get_db
from app.models import User
from app.modules.auth.dependencies import (
    get_current_active_user,
    require_roles,
    require_staff,
)
from app.modules.requests.service import RequestService
from app.schemas.request import (
    PaginatedRequestsResponse,
    RequestAssign,
    RequestCreate,
    RequestListResponse,
    RequestResponse,
    RequestUpdate,
    RequestUpdateStatus,
)

router = APIRouter(prefix="/requests", tags=["requests"])


# ============================================================================
# Create Request
# ============================================================================


@router.post(
    "",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สร้าง Request ใหม่",
    description="สร้างคำร้อง/แจ้งปัญหาใหม่ พร้อมอัปโหลดไฟล์แนบได้",
)
async def create_request(
    title: Annotated[str, Form(...)],
    description: Annotated[str, Form(...)],
    request_type: Annotated[RequestType, Form()] = RequestType.OTHER,
    priority: Annotated[RequestPriority, Form()] = RequestPriority.MEDIUM,
    location: Annotated[Optional[str], Form()] = None,
    contact_phone: Annotated[Optional[str], Form()] = None,
    files: Annotated[list[UploadFile], File()] = [],
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    สร้าง Request ใหม่ พร้อมอัปโหลดไฟล์แนบ (multipart/form-data)
    
    **Parameters:**
    - **title**: หัวข้อคำร้อง (min 5 chars)
    - **description**: รายละเอียดคำร้อง (min 10 chars)
    - **request_type**: ประเภทคำร้อง (maintenance, complaint, inquiry, other)
    - **priority**: ระดับความสำคัญ (low, medium, high, urgent)
    - **location**: สถานที่ (optional)
    - **contact_phone**: เบอร์โทรติดต่อ (optional)
    - **files**: ไฟล์แนบ (optional, multiple files)
    
    **Returns:**
    - Request object พร้อม attachments
    """
    request_data = RequestCreate(
        title=title,
        description=description,
        request_type=request_type,
        priority=priority,
        location=location,
        contact_phone=contact_phone,
    )

    service = RequestService(db)
    request = await service.create_request(
        request_data=request_data,
        user=current_user,
        files=files if files else None,
    )

    return request


# ============================================================================
# Get User's Requests
# ============================================================================


@router.get(
    "/me",
    response_model=PaginatedRequestsResponse,
    summary="ดึงรายการ Requests ของตัวเอง",
    description="ดึงรายการคำร้องของผู้ใช้ที่ล็อกอินอยู่",
)
async def get_my_requests(
    status: Annotated[Optional[RequestStatus], Query()] = None,
    request_type: Annotated[Optional[RequestType], Query()] = None,
    priority: Annotated[Optional[RequestPriority], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงรายการ Requests ของผู้ใช้ที่ล็อกอินอยู่
    
    **Query Parameters:**
    - **status**: Filter by status (optional)
    - **request_type**: Filter by type (optional)
    - **priority**: Filter by priority (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    service = RequestService(db)
    skip = (page - 1) * page_size

    requests, total = await service.get_user_requests(
        user=current_user,
        status=status,
        request_type=request_type,
        priority=priority,
        skip=skip,
        limit=page_size,
    )

    return PaginatedRequestsResponse(
        items=[RequestListResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ============================================================================
# Get All Requests (Staff/Admin)
# ============================================================================


@router.get(
    "",
    response_model=PaginatedRequestsResponse,
    summary="ดึงรายการ Requests ทั้งหมด (Staff/Admin)",
    description="ดึงรายการคำร้องทั้งหมด (สำหรับ Staff และ Admin)",
)
async def get_all_requests(
    status: Annotated[Optional[RequestStatus], Query()] = None,
    request_type: Annotated[Optional[RequestType], Query()] = None,
    priority: Annotated[Optional[RequestPriority], Query()] = None,
    assigned_staff_id: Annotated[Optional[int], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    current_user: Annotated[User, Depends(require_staff())] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงรายการ Requests ทั้งหมด (สำหรับ Staff/Admin)
    
    **Query Parameters:**
    - **status**: Filter by status (optional)
    - **request_type**: Filter by type (optional)
    - **priority**: Filter by priority (optional)
    - **assigned_staff_id**: Filter by assigned staff ID (optional)
    - **search**: Search in title/description/request_number (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    service = RequestService(db)
    skip = (page - 1) * page_size

    requests, total = await service.get_all_requests(
        status=status,
        request_type=request_type,
        priority=priority,
        assigned_staff_id=assigned_staff_id,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return PaginatedRequestsResponse(
        items=[RequestListResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ============================================================================
# Get Request by ID
# ============================================================================


@router.get(
    "/{request_id}",
    response_model=RequestResponse,
    summary="ดึงข้อมูล Request โดย ID",
    description="ดึงข้อมูลคำร้องแบบละเอียด (รวมไฟล์แนบ)",
)
async def get_request(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ดึงข้อมูล Request โดย ID (รวมไฟล์แนบ)
    
    **Permissions:**
    - Student: เข้าถึงได้เฉพาะของตัวเอง
    - Staff/Admin: เข้าถึงได้ทั้งหมด
    """
    service = RequestService(db)
    request = await service.get_request_by_id(request_id, user=current_user)
    return request


# ============================================================================
# Update Request (User)
# ============================================================================


@router.patch(
    "/{request_id}",
    response_model=RequestResponse,
    summary="แก้ไข Request (โดยเจ้าของ)",
    description="แก้ไขข้อมูลคำร้อง (เฉพาะเจ้าของ และสถานะ PENDING/REJECTED)",
)
async def update_request(
    request_id: int,
    request_data: RequestUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    แก้ไขข้อมูล Request
    
    **Permissions:**
    - เฉพาะเจ้าของ Request
    - สถานะต้องเป็น PENDING หรือ REJECTED
    
    **Editable Fields:**
    - title, description, request_type, priority, location, contact_phone
    """
    service = RequestService(db)
    request = await service.update_request(request_id, current_user, request_data)
    return request


# ============================================================================
# Update Request Status (Staff/Admin)
# ============================================================================


@router.patch(
    "/{request_id}/status",
    response_model=RequestResponse,
    summary="อัปเดตสถานะ Request (Staff/Admin)",
    description="เปลี่ยนสถานะคำร้อง (สำหรับ Staff/Admin)",
)
async def update_request_status(
    request_id: int,
    status_data: RequestUpdateStatus,
    current_user: Annotated[User, Depends(require_staff())] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    อัปเดตสถานะ Request
    
    **Permissions:**
    - Staff และ Admin เท่านั้น
    
    **Status Flow:**
    - PENDING → IN_PROGRESS → COMPLETED
    - PENDING → REJECTED
    - Any → CANCELLED (by user)
    
    **Required Fields by Status:**
    - COMPLETED: resolution (optional but recommended)
    - REJECTED: rejection_reason (required)
    """
    service = RequestService(db)
    request = await service.update_request_status(request_id, current_user, status_data)
    return request


# ============================================================================
# Assign Request (Staff/Admin)
# ============================================================================


@router.patch(
    "/{request_id}/assign",
    response_model=RequestResponse,
    summary="มอบหมาย Request ให้ Staff (Staff/Admin)",
    description="มอบหมายคำร้องให้กับเจ้าหน้าที่",
)
async def assign_request(
    request_id: int,
    assign_data: RequestAssign,
    current_user: Annotated[User, Depends(require_staff())] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    มอบหมาย Request ให้กับ Staff
    
    **Permissions:**
    - Staff และ Admin เท่านั้น
    
    **Behavior:**
    - ถ้าสถานะเป็น PENDING จะเปลี่ยนเป็น IN_PROGRESS อัตโนมัติ
    - assigned_at timestamp จะถูกบันทึก
    """
    service = RequestService(db)
    request = await service.assign_request(
        request_id=request_id,
        assigned_staff_id=assign_data.assigned_staff_id,
        user=current_user,
    )
    return request


# ============================================================================
# Cancel Request (User)
# ============================================================================


@router.post(
    "/{request_id}/cancel",
    response_model=RequestResponse,
    summary="ยกเลิก Request (โดยเจ้าของ)",
    description="ยกเลิกคำร้อง (เฉพาะเจ้าของ)",
)
async def cancel_request(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    ยกเลิก Request
    
    **Permissions:**
    - เฉพาะเจ้าของ Request
    
    **Restrictions:**
    - ไม่สามารถยกเลิก Request ที่สถานะเป็น COMPLETED หรือ CANCELLED แล้ว
    """
    service = RequestService(db)
    request = await service.cancel_request(request_id, current_user)
    return request


# ============================================================================
# Add Attachments
# ============================================================================


@router.post(
    "/{request_id}/attachments",
    response_model=RequestResponse,
    summary="เพิ่มไฟล์แนบให้ Request",
    description="เพิ่มไฟล์แนบให้กับคำร้องที่มีอยู่แล้ว",
)
async def add_request_attachments(
    request_id: int,
    files: Annotated[list[UploadFile], File(...)],
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    เพิ่มไฟล์แนบให้กับ Request
    
    **Permissions:**
    - เฉพาะเจ้าของ Request
    - สถานะต้องเป็น PENDING หรือ REJECTED
    
    **File Requirements:**
    - Images: .jpg, .jpeg, .png, .gif, .webp (max 5MB)
    - Documents: .pdf, .doc, .docx, .xls, .xlsx (max 10MB)
    """
    service = RequestService(db)
    request = await service.add_attachments_to_request(
        request_id=request_id,
        user=current_user,
        files=files,
    )
    return request
