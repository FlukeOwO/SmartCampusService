"""
Request Schemas - Pydantic schemas สำหรับ Request API
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.common.constants import RequestPriority, RequestStatus, RequestType


# ============================================================================
# Request Attachment Schemas
# ============================================================================


class RequestAttachmentBase(BaseModel):
    """Base schema สำหรับ Request Attachment"""

    filename: str
    file_url: str
    file_size: int
    file_type: Optional[str] = None


class RequestAttachmentResponse(RequestAttachmentBase):
    """Response schema สำหรับ Request Attachment"""

    id: int
    request_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Request Schemas
# ============================================================================


class RequestBase(BaseModel):
    """Base schema สำหรับ Request"""

    title: str = Field(..., min_length=5, max_length=255, description="หัวข้อคำร้อง")
    description: str = Field(..., min_length=10, description="รายละเอียดคำร้อง")
    request_type: RequestType = Field(default=RequestType.OTHER, description="ประเภทคำร้อง")
    priority: RequestPriority = Field(default=RequestPriority.MEDIUM, description="ระดับความสำคัญ")
    location: Optional[str] = Field(None, max_length=255, description="สถานที่")
    contact_phone: Optional[str] = Field(None, max_length=20, description="เบอร์โทรติดต่อ")


class RequestCreate(RequestBase):
    """Schema สำหรับสร้าง Request ใหม่"""

    pass


class RequestUpdate(BaseModel):
    """Schema สำหรับอัปเดต Request (user edit own request)"""

    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    request_type: Optional[RequestType] = None
    priority: Optional[RequestPriority] = None
    location: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)


class RequestUpdateStatus(BaseModel):
    """Schema สำหรับอัปเดตสถานะ Request (staff only)"""

    status: RequestStatus = Field(..., description="สถานะใหม่")
    status_notes: Optional[str] = Field(None, description="หมายเหตุสถานะ")
    resolution: Optional[str] = Field(None, description="วิธีการแก้ไข (สำหรับ completed)")
    rejection_reason: Optional[str] = Field(None, description="เหตุผลที่ปฏิเสธ (สำหรับ rejected)")

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v, info):
        """ตรวจสอบว่าถ้า status เป็น rejected ต้องมี rejection_reason"""
        if info.data.get("status") == RequestStatus.REJECTED and not v:
            raise ValueError("rejection_reason is required when status is REJECTED")
        return v


class RequestAssign(BaseModel):
    """Schema สำหรับมอบหมายงาน (staff/admin only)"""

    assigned_staff_id: int = Field(..., description="ID ของเจ้าหน้าที่ที่รับผิดชอบ")


class RequestFeedback(BaseModel):
    """Schema สำหรับให้คะแนนและ feedback (user only, after completed)"""

    rating: int = Field(..., ge=1, le=5, description="คะแนนความพึงพอใจ (1-5)")
    feedback: Optional[str] = Field(None, description="ความคิดเห็นเพิ่มเติม")


class RequestResponse(RequestBase):
    """Response schema สำหรับ Request"""

    id: int
    request_number: str
    user_id: int
    assigned_staff_id: Optional[int] = None
    status: RequestStatus
    status_notes: Optional[str] = None
    resolution: Optional[str] = None
    rejection_reason: Optional[str] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Relationships (optional, can be included with joins)
    attachments: list[RequestAttachmentResponse] = []

    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    """Response schema สำหรับ list ของ Requests"""

    id: int
    request_number: str
    title: str
    request_type: RequestType
    priority: RequestPriority
    status: RequestStatus
    user_id: int
    assigned_staff_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Pagination
# ============================================================================


class PaginatedRequestsResponse(BaseModel):
    """Response schema สำหรับ paginated requests"""

    items: list[RequestListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int