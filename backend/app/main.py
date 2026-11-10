"""
Smart Campus Service Platform - FastAPI application (Modular Monolith)

Router -> Service -> Model/DB ทุกโมดูล; error ทุกชนิดตอบเป็น {"message", "details"}
Cloud Run ส่ง SIGTERM แล้ว uvicorn ปิดตัวเอง (lifespan shutdown คืน connection pool)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import TimeoutError as DbPoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.exceptions import AppException
from app.core.config import settings
from app.core.database import check_db_connection, close_db_connection
from app.core.logging import TraceContextMiddleware, setup_logging
from app.core.rate_limit import limiter
from app.modules.auth.router import router as auth_router
from app.modules.bookings.router import router as bookings_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.inventory.router import router as inventory_router
from app.modules.notifications.router import router as notifications_router
from app.modules.requests.router import router as requests_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s (env=%s, storage=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
        settings.STORAGE_PROVIDER,
    )
    yield
    await close_db_connection()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs" if settings.docs_enabled else None,
    redoc_url=f"{settings.API_PREFIX}/redoc" if settings.docs_enabled else None,
    openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)
app.state.limiter = limiter

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ProbeFriendlyTrustedHostMiddleware(TrustedHostMiddleware):
    """Skip the host check for probes. Cloud Run may call them with an internal Host header."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") in {"/healthz", "/readyz"}:
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


app.add_middleware(ProbeFriendlyTrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(TraceContextMiddleware)


# -----------------------------------------------------------------------------
# Error handlers - รูปแบบเดียว {"message": ..., "details": ...}, ไม่ส่ง stack trace
# -----------------------------------------------------------------------------
def _error(status_code: int, message: str, details=None, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"message": message, "details": jsonable_encoder(details)},
        headers=headers,
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return _error(exc.status_code, exc.message, exc.details, headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return _error(422, "Invalid request data", details)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, str(exc.detail), headers=getattr(exc, "headers", None))


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return _error(429, "Too many requests, please try again later", {"limit": str(exc.detail)})


def _is_pool_timeout(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, DbPoolTimeout):
            return True
        current = current.__cause__ or current.__context__
    return False


@app.exception_handler(DbPoolTimeout)
async def pool_timeout_handler(request: Request, exc: DbPoolTimeout):
    logger.warning("Database pool exhausted on %s %s", request.method, request.url.path)
    return _error(
        503,
        "The server is busy. Please try again in a moment.",
        headers={"Retry-After": "3"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if _is_pool_timeout(exc):
        return await pool_timeout_handler(request, exc)  # type: ignore[arg-type]
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error(500, "Internal server error")


# -----------------------------------------------------------------------------
# Health checks (Cloud Run startup probe = /healthz)
# -----------------------------------------------------------------------------
@app.get("/healthz", tags=["Health"])
async def healthz():
    """Liveness/startup - ไม่แตะ DB เพื่อให้ instance ขึ้นได้แม้ DB ช้าชั่วคราว"""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/readyz", tags=["Health"])
async def readyz():
    if not await check_db_connection():
        return _error(503, "Database unavailable")
    return {"status": "ready", "database": "ok"}


@app.get(settings.API_PREFIX, tags=["Health"])
async def api_root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------
app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])
app.include_router(requests_router, prefix=f"{settings.API_PREFIX}/requests", tags=["Requests"])
app.include_router(bookings_router, prefix=f"{settings.API_PREFIX}/bookings", tags=["Bookings"])
app.include_router(inventory_router, prefix=f"{settings.API_PREFIX}/inventory", tags=["Inventory"])
app.include_router(dashboard_router, prefix=f"{settings.API_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(
    notifications_router, prefix=f"{settings.API_PREFIX}/notifications", tags=["Notifications"]
)

# ไฟล์แนบตอน dev (STORAGE_PROVIDER=local) - บน cloud ใช้ Signed URL แทน
if settings.STORAGE_PROVIDER == "local" and not settings.is_production:
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="storage")
