"""
Auth dependencies - ตรวจ JWT และ role ที่ชั้น Router
(การตรวจความเป็นเจ้าของข้อมูลทำที่ Service)
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import UserRole
from app.common.exceptions import AuthenticationException, ForbiddenException
from app.core.database import get_db
from app.models import User
from app.modules.auth.service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AuthenticationException("Not authenticated")
    return await AuthService(db).get_user_from_access_token(credentials.credentials)


# อ่านง่ายขึ้นตอนประกาศ endpoint: user: CurrentUser
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    allowed = {role.value for role in roles}

    async def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ForbiddenException("Insufficient role for this action")
        return user

    return checker


def require_staff():
    return require_roles(UserRole.STAFF, UserRole.ADMIN)


def require_admin():
    return require_roles(UserRole.ADMIN)


StaffUser = Annotated[User, Depends(require_staff())]
AdminUser = Annotated[User, Depends(require_admin())]
