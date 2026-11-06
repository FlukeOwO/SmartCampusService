"""
Dashboard schemas - สถิติภาพรวมสำหรับ staff/admin
"""

from datetime import date, datetime

from pydantic import BaseModel


class RequestStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_priority: dict[str, int]
    open_unassigned: int
    avg_resolution_hours: float | None
    created_in_window: int


class BookingStats(BaseModel):
    total: int
    by_status: dict[str, int]
    pending_approval: int
    upcoming_confirmed: int
    created_in_window: int


class TopRoom(BaseModel):
    room_id: int
    room_number: str
    room_name: str
    bookings: int


class DailyCount(BaseModel):
    date: date
    requests: int
    bookings: int


class DashboardSummary(BaseModel):
    generated_at: datetime
    window_days: int
    requests: RequestStats
    bookings: BookingStats
    top_rooms: list[TopRoom]
    daily: list[DailyCount]
    users_by_role: dict[str, int]
