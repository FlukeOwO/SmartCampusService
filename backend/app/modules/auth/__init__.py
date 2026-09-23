"""
Auth Module - Authentication & User Management
"""

from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_current_user, get_current_active_user

__all__ = ["AuthService", "get_current_user", "get_current_active_user"]
