"""
Base Models - Shared SQLAlchemy Models และ Pydantic Schemas
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ============================================================================
# SQLAlchemy Base Models
# ============================================================================


class TimestampMixin:
    """
    Mixin สำหรับ timestamp columns
    เพิ่ม created_at และ updated_at ให้กับทุก table
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="เวลาที่สร้างระเบียน",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="เวลาที่อัปเดตระเบียนล่าสุด",
    )


# ============================================================================
# Common Response Schemas
# ============================================================================

from pydantic import BaseModel, ConfigDict


class ResponseBase(BaseModel):
    """Base Response Schema"""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Simple message response"""

    message: str
    detail: str | None = None


class PaginationParams(BaseModel):
    """Pagination parameters"""

    page: int = 1
    page_size: int = 10
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size"""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ):
        """Factory method for creating paginated response"""
        import math
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        )
