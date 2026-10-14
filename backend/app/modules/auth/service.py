"""
Auth service - สมัคร, login, refresh, จัดการผู้ใช้
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_models import PageParams
from app.common.constants import UserRole
from app.common.exceptions import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserCreate,
    UserLogin,
    UserPasswordUpdate,
    UserUpdate,
)

# ใช้เทียบเวลาเมื่อไม่พบอีเมล เพื่อไม่ให้เดาได้จากเวลาตอบว่าอีเมลมีในระบบหรือไม่
_DUMMY_HASH = get_password_hash("timing-attack-dummy-password")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ users
    async def _create_user(self, data: UserCreate, role: UserRole) -> User:
        await self._ensure_unique(data)
        user = User(
            email=data.email.lower(),
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            student_id=data.student_id,
            staff_id=data.staff_id,
            phone_number=data.phone_number,
            department=data.department,
            role=role.value,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictException("Email, student ID or staff ID is already registered") from exc
        await self.db.refresh(user)
        return user

    async def register(self, data: UserCreate) -> User:
        # การสมัครสาธารณะได้ role student เสมอ
        return await self._create_user(data, UserRole.STUDENT)

    async def admin_create_user(self, data: AdminUserCreate) -> User:
        return await self._create_user(data, data.role)

    async def _ensure_unique(self, data: UserCreate) -> None:
        checks = [("Email", User.email, data.email.lower())]
        if data.student_id:
            checks.append(("Student ID", User.student_id, data.student_id))
        if data.staff_id:
            checks.append(("Staff ID", User.staff_id, data.staff_id))
        for label, column, value in checks:
            exists = await self.db.scalar(select(select(User.id).where(column == value).exists()))
            if exists:
                raise ConflictException(f"{label} is already registered")

    async def get_user(self, user_id: int) -> User:
        user = await self.db.get(User, user_id)
        if user is None:
            raise NotFoundException("User not found")
        return user

    async def list_users(self, params: PageParams, role: UserRole | None) -> tuple[list[User], int]:
        query = select(User)
        if role:
            query = query.where(User.role == role.value)
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.scalars(
            query.order_by(User.id).offset(params.offset).limit(params.page_size)
        )
        return list(rows), total or 0

    async def admin_update_user(self, actor: User, user_id: int, data: AdminUserUpdate) -> User:
        user = await self.get_user(user_id)
        if user.id == actor.id and (data.role or data.is_active is False):
            raise ValidationException(
                "Admins cannot change their own role or deactivate themselves"
            )
        if data.role is not None:
            user.role = data.role.value
        if data.is_active is not None:
            user.is_active = data.is_active
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user: User, data: UserPasswordUpdate) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise ValidationException("Current password is incorrect")
        user.hashed_password = get_password_hash(data.new_password)
        await self.db.commit()

    # ----------------------------------------------------------------- tokens
    async def login(self, data: UserLogin) -> dict:
        user = await self.db.scalar(select(User).where(User.email == data.email.lower()))
        if user is None:
            verify_password(data.password, _DUMMY_HASH)
            raise AuthenticationException("Invalid email or password")
        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")
        if not user.is_active:
            raise AuthenticationException("User account is inactive")
        return {
            "access_token": create_access_token(user.id, user.role),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
            "user": user,
        }

    async def refresh(self, refresh_token: str) -> dict:
        user = await self._user_from_token(refresh_token, "refresh")
        return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer"}

    async def get_user_from_access_token(self, token: str) -> User:
        return await self._user_from_token(token, "access")

    async def _user_from_token(self, token: str, token_type: str) -> User:
        try:
            payload = decode_token(token, token_type)  # type: ignore[arg-type]
            user_id = int(payload["sub"])
        except (TokenError, ValueError) as exc:
            raise AuthenticationException(str(exc) or "Invalid token") from exc
        # role มาจาก DB เสมอ ไม่เชื่อ role ใน token (กันกรณี role ถูกเปลี่ยนหลังออก token)
        user = await self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise AuthenticationException("User not found or inactive")
        return user
