"""
Request (คำร้อง/แจ้งปัญหา) schemas
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.constants import RequestPriority, RequestStatus, RequestType


class RequestAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    filename: str
    file_size: int
    file_type: str | None = None
    created_at: datetime


class RequestBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    request_type: RequestType = RequestType.OTHER
    priority: RequestPriority = RequestPriority.MEDIUM
    location: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)


class RequestCreate(RequestBase):
    pass


class RequestUpdate(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=255)
    description: str | None = Field(None, min_length=10)
    request_type: RequestType | None = None
    priority: RequestPriority | None = None
    location: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)


class RequestUpdateStatus(BaseModel):
    status: RequestStatus
    status_notes: str | None = None
    resolution: str | None = None
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def _require_reason(self):
        if self.status == RequestStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when status is rejected")
        return self


class RequestAssign(BaseModel):
    assigned_staff_id: int


class RequestFeedback(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: str | None = None


class RequestResponse(RequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_number: str
    user_id: int
    assigned_staff_id: int | None = None
    status: RequestStatus
    status_notes: str | None = None
    resolution: str | None = None
    rejection_reason: str | None = None
    rating: int | None = None
    feedback: str | None = None
    created_at: datetime
    updated_at: datetime
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attachments: list[RequestAttachmentResponse] = []


class RequestListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_number: str
    title: str
    request_type: RequestType
    priority: RequestPriority
    status: RequestStatus
    user_id: int
    assigned_staff_id: int | None = None
    created_at: datetime
    updated_at: datetime


class SignedUrlResponse(BaseModel):
    url: str
    expires_in_seconds: int
