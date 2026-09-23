"""
Custom Exceptions - Application-specific exceptions
"""

from typing import Any


class AppException(Exception):
    """Base exception สำหรับ Application"""

    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationException(AppException):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationException(AppException):
    """Insufficient permissions"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundException(AppException):
    """Resource not found"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictException(AppException):
    """Resource conflict (e.g., duplicate booking)"""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class ValidationException(AppException):
    """Validation error"""

    def __init__(self, message: str = "Validation error", details: Any = None):
        super().__init__(message, status_code=422, details=details)


class StorageException(AppException):
    """Storage operation failed"""

    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message, status_code=500)
