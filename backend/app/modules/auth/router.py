"""
Auth Router - API Endpoints สำหรับ Authentication
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AuthenticationException, ConflictException
from app.core.database import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_active_user, require_admin
from app.modules.auth.service import AuthService
from app.schemas.user import (
    AccessTokenResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPasswordUpdate,
    UserProfile,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    ลงทะเบียนผู้ใช้ใหม่
    
    - **email**: อีเมล (unique)
    - **password**: รหัสผ่าน (ขั้นต่ำ 8 ตัวอักษร)
    - **full_name**: ชื่อ-นามสกุล
    - **student_id**: รหัสนักศึกษา (สำหรับ Student)

    Public registration creates a STUDENT account. Staff/Admin accounts must
    be provisioned through a protected administrative flow.
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.register_user(user_data)
        return user
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    เข้าสู่ระบบ
    
    - **email**: อีเมล
    - **password**: รหัสผ่าน
    
    Returns:
        - access_token: สำหรับเข้าถึง API
        - refresh_token: สำหรับขอ access token ใหม่
        - user: ข้อมูลผู้ใช้
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.authenticate_user(login_data)
        return result
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    ขอ Access Token ใหม่จาก Refresh Token
    
    - **refresh_token**: Refresh token ที่ได้จากการ login
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.refresh_access_token(refresh_data.refresh_token)
        return result
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    ดูข้อมูลโปรไฟล์ของตัวเอง
    
    Required: Authentication (Bearer Token)
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    แก้ไขข้อมูลโปรไฟล์
    
    Required: Authentication
    """
    # Update user fields
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    if update_data.phone_number is not None:
        current_user.phone_number = update_data.phone_number
    if update_data.department is not None:
        current_user.department = update_data.department
    if update_data.avatar_url is not None:
        current_user.avatar_url = update_data.avatar_url

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: UserPasswordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    เปลี่ยนรหัสผ่าน
    
    Required: Authentication
    """
    from app.core.security import get_password_hash, verify_password

    # ตรวจสอบรหัสผ่านเดิม
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # เปลี่ยนรหัสผ่าน
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
):
    """
    ดูรายการผู้ใช้ทั้งหมด
    
    Required: Admin role
    """
    from sqlalchemy import select

    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return users
