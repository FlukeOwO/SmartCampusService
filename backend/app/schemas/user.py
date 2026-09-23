"""
User Schemas - Pydantic Models สำหรับ API Request/Response
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.common.constants import UserRole


# ============================================================================
# Base Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base User Schema"""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    student_id: str | None = Field(None, max_length=50)
    staff_id: str | None = Field(None, max_length=50)
    phone_number: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)
    # Role is intentionally not accepted from public registration.
    # New public accounts are always created as STUDENT.


# ============================================================================
# Request Schemas
# ============================================================================


class UserCreate(UserBase):
    """Schema สำหรับสร้าง User"""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema สำหรับอัปเดต User"""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone_number: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)
    avatar_url: str | None = None


class UserPasswordUpdate(BaseModel):
    """Schema สำหรับเปลี่ยนรหัสผ่าน"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema สำหรับ Login"""

    email: EmailStr
    password: str


# ============================================================================
# Response Schemas
# ============================================================================


class UserResponse(UserBase):
    """Schema สำหรับ Response (ไม่รวม password)"""

    id: int
    role: UserRole
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(UserResponse):
    """Schema สำหรับ Profile (เพิ่มข้อมูลเพิ่มเติม)"""

    pass


class TokenResponse(BaseModel):
    """Schema สำหรับ Login Token Response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    """Schema สำหรับ Refresh Token Response"""

    access_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema สำหรับ Refresh Token"""

    refresh_token: str
