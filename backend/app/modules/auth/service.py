"""
Auth Service - User Authentication และ Management
"""

from typing import Optional

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import UserRole
from app.common.exceptions import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from app.models import User
from app.schemas.user import UserCreate, UserLogin


class AuthService:
    """Authentication Service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_data: UserCreate) -> User:
        """
        ลงทะเบียนผู้ใช้ใหม่
        
        Args:
            user_data: ข้อมูลผู้ใช้
        
        Returns:
            User object ที่สร้างแล้ว
        
        Raises:
            ConflictException: อีเมลซ้ำ
        """
        # ตรวจสอบอีเมลซ้ำ
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ConflictException(f"Email {user_data.email} is already registered")

        # ตรวจสอบ student_id หรือ staff_id ซ้ำ
        if user_data.student_id:
            existing_student = await self._get_user_by_student_id(user_data.student_id)
            if existing_student:
                raise ConflictException(
                    f"Student ID {user_data.student_id} is already registered"
                )

        if user_data.staff_id:
            existing_staff = await self._get_user_by_staff_id(user_data.staff_id)
            if existing_staff:
                raise ConflictException(
                    f"Staff ID {user_data.staff_id} is already registered"
                )

        # สร้างผู้ใช้ใหม่
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            student_id=user_data.student_id,
            staff_id=user_data.staff_id,
            phone_number=user_data.phone_number,
            department=user_data.department,
            # Public registration must never allow the client to choose an
            # elevated role such as STAFF or ADMIN.
            role=UserRole.STUDENT.value,
            is_active=True,
            is_verified=False,  # ต้องยืนยันอีเมลก่อน
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def authenticate_user(self, login_data: UserLogin) -> dict:
        """
        ตรวจสอบข้อมูลการ login และสร้าง tokens
        
        Args:
            login_data: ข้อมูล login (email, password)
        
        Returns:
            Dictionary ที่มี access_token, refresh_token, user
        
        Raises:
            AuthenticationException: ข้อมูลไม่ถูกต้อง
        """
        # ค้นหาผู้ใช้
        user = await self.get_user_by_email(login_data.email)
        if not user:
            raise AuthenticationException("Invalid email or password")

        # ตรวจสอบรหัสผ่าน
        if not verify_password(login_data.password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")

        # ตรวจสอบว่าผู้ใช้ active หรือไม่
        if not user.is_active:
            raise AuthenticationException("User account is inactive")

        # สร้าง tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={"role": user.role, "email": user.email},
        )
        refresh_token = create_refresh_token(subject=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user,
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        สร้าง access token ใหม่จาก refresh token
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            Dictionary ที่มี access_token ใหม่
        
        Raises:
            AuthenticationException: Token ไม่ถูกต้อง
        """
        try:
            payload = decode_token(refresh_token)
            
            # ตรวจสอบว่าเป็น refresh token
            if not verify_token_type(payload, "refresh"):
                raise AuthenticationException("Invalid token type")

            user_id = int(payload.get("sub"))
            user = await self.get_user_by_id(user_id)

            if not user or not user.is_active:
                raise AuthenticationException("User not found or inactive")

            # สร้าง access token ใหม่
            access_token = create_access_token(
                subject=user.id,
                additional_claims={"role": user.role, "email": user.email},
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
            }

        except JWTError:
            raise AuthenticationException("Invalid or expired refresh token")

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ดึงข้อมูลผู้ใช้จาก ID"""
        return await self.db.get(User, user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """ดึงข้อมูลผู้ใช้จากอีเมล"""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_by_student_id(self, student_id: str) -> Optional[User]:
        """ดึงข้อมูลผู้ใช้จาก student_id"""
        query = select(User).where(User.student_id == student_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_by_staff_id(self, staff_id: str) -> Optional[User]:
        """ดึงข้อมูลผู้ใช้จาก staff_id"""
        query = select(User).where(User.staff_id == staff_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_from_token(self, token: str) -> User:
        """
        ดึงข้อมูลผู้ใช้จาก JWT Token
        
        Args:
            token: JWT Access Token
        
        Returns:
            User object
        
        Raises:
            AuthenticationException: Token ไม่ถูกต้อง
        """
        try:
            payload = decode_token(token)
            
            # ตรวจสอบว่าเป็น access token
            if not verify_token_type(payload, "access"):
                raise AuthenticationException("Invalid token type")

            user_id = int(payload.get("sub"))
            user = await self.get_user_by_id(user_id)

            if not user:
                raise AuthenticationException("User not found")

            if not user.is_active:
                raise AuthenticationException("User account is inactive")

            return user

        except JWTError:
            raise AuthenticationException("Invalid or expired token")
