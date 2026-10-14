"""
Rate limit (slowapi) - ใช้กับ POST /auth/login

หมายเหตุ: ตัวนับอยู่ใน memory ของแต่ละ instance (max 3 instances บน Cloud Run)
จึงเป็นการกัน brute force ระดับพื้นฐาน ไม่ใช่ global limit
"""

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    # Cloud Run ต่อท้าย IP จริงของ client ไว้ท้ายสุดของ X-Forwarded-For
    # (ค่าด้านซ้ายมาจาก client จึงปลอมได้ ห้ามใช้)
    if settings.is_cloud_run:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip, enabled=settings.RATE_LIMIT_ENABLED)
