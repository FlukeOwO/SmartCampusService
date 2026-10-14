"""
Shared model mixins และ response schemas
"""

from datetime import datetime
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams:
    """Query params ?page=&page_size= ใช้ร่วมกันทุก list endpoint"""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class MessageResponse(BaseModel):
    message: str
