"""
Auth Dependencies - FastAPI Dependencies สำหรับ Authentication
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import UserRole
from app.common.exceptions import AuthenticationException
from app.core.database import get_db
from app.models import User
from app.modules.auth.service import AuthService

# HTTP Bearer Token Scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency สำหรับดึงข้อมูลผู้ใช้ปัจจุบันจาก JWT Token
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException: ถ้า token ไม่ถูกต้อง
    """
    try:
        auth_service = AuthService(db)
        token = credentials.credentials
        user = await auth_service.get_user_from_token(token)
        return user
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency สำหรับตรวจสอบว่าผู้ใช้ active หรือไม่
    
    Args:
        current_user: User จาก get_current_user
    
    Returns:
        User object
    
    Raises:
        HTTPException: ถ้าผู้ใช้ไม่ active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


def require_roles(allowed_roles: list[UserRole]):
    """
    Dependency Factory สำหรับตรวจสอบ Role
    
    Args:
        allowed_roles: List ของ roles ที่อนุญาต
    
    Returns:
        Dependency function
    
    Example:
        @app.get("/admin")
        async def admin_only(
            user: Annotated[User, Depends(require_roles([UserRole.ADMIN]))]
        ):
            return {"message": "Admin only"}
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        user_role = current_user.role
        allowed_role_values = [role.value for role in allowed_roles]

        if user_role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_role_values}",
            )

        return current_user

    return role_checker


def require_staff():
    """Dependency สำหรับตรวจสอบว่าเป็น Staff หรือ Admin"""
    return require_roles([UserRole.STAFF, UserRole.ADMIN])


def require_admin():
    """Dependency สำหรับตรวจสอบว่าเป็น Admin"""
    return require_roles([UserRole.ADMIN])
