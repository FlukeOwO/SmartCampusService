"""
Auth router - /api/v1/auth
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import Page, PageParams
from app.common.constants import UserRole
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.auth.service import AuthService
from app.schemas.user import (
    AccessTokenResponse,
    AdminUserCreate,
    AdminUserUpdate,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DB):
    """สมัครสมาชิก (ได้ role student เสมอ)"""
    return await AuthService(db).register(data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, data: UserLogin, db: DB):
    """เข้าสู่ระบบ - จำกัด 5 ครั้ง/นาที/IP"""
    return await AuthService(db).login(data)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: TokenRefreshRequest, db: DB):
    return await AuthService(db).refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def read_me(user: CurrentUser):
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, user: CurrentUser, db: DB):
    return await AuthService(db).update_profile(user, data)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: UserPasswordUpdate, user: CurrentUser, db: DB):
    await AuthService(db).change_password(user, data)


@router.get("/users", response_model=Page[UserResponse])
async def list_users(
    _: AdminUser,
    db: DB,
    params: Annotated[PageParams, Depends()],
    role: UserRole | None = Query(None),
):
    items, total = await AuthService(db).list_users(params, role)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: AdminUserCreate, _: AdminUser, db: DB):
    """admin สร้างบัญชี staff/admin"""
    return await AuthService(db).admin_create_user(data)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: AdminUserUpdate, admin: AdminUser, db: DB):
    """admin เปลี่ยน role หรือระงับบัญชี"""
    return await AuthService(db).admin_update_user(admin, user_id, data)
