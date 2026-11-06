"""
Dashboard router - /api/v1/dashboard (staff/admin)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import StaffUser
from app.modules.dashboard.service import DashboardService
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    _: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365, description="ช่วงเวลาย้อนหลังสำหรับสถิติรายวัน"),
):
    """สถิติภาพรวมคำร้อง การจอง ห้องยอดนิยม และจำนวนต่อวัน"""
    return await DashboardService(db).summary(days)
