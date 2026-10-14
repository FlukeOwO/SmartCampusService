"""
Application exceptions - Service โยน exception เหล่านี้ แล้ว main.py แปลงเป็น
JSON รูปแบบเดียวกัน {"message": ..., "details": ...}
"""

from typing import Any


class AppException(Exception):
    status_code: int = 500
    default_message: str = "Internal server error"

    def __init__(self, message: str | None = None, details: Any = None):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    """กฎธุรกิจไม่ผ่าน เช่น จองย้อนหลัง ห้องปิดซ่อม"""

    status_code = 400
    default_message = "Business rule validation failed"


class AuthenticationException(AppException):
    status_code = 401
    default_message = "Authentication failed"


class ForbiddenException(AppException):
    status_code = 403
    default_message = "You do not have permission to perform this action"


class NotFoundException(AppException):
    status_code = 404
    default_message = "Resource not found"


class ConflictException(AppException):
    status_code = 409
    default_message = "Resource conflict"


class PayloadTooLargeException(AppException):
    status_code = 413
    default_message = "File is too large"


class StorageException(AppException):
    status_code = 502
    default_message = "Storage operation failed"
