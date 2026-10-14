"""
User / Auth schemas
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.constants import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    student_id: str | None = Field(None, max_length=50)
    staff_id: str | None = Field(None, max_length=50)
    phone_number: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    """สมัครสาธารณะ - ไม่รับ role จาก client (ได้ student เสมอ)"""

    password: str = Field(..., min_length=8, max_length=72)


class AdminUserCreate(UserCreate):
    """admin สร้างบัญชี staff/admin"""

    role: UserRole = UserRole.STAFF


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone_number: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str
