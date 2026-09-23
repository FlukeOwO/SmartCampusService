<<<<<<< HEAD
"""
Smart Campus Service Platform - Main Application
Cloud-Ready FastAPI Application with Health Checks and Graceful Shutdown
"""

import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import check_db_connection, close_db_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan Management
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Manager
    จัดการ startup และ shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} ({settings.ENVIRONMENT})")
    logger.info(f"Database URL: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    logger.info(f"Storage Provider: {settings.STORAGE_PROVIDER}")

    # ตรวจสอบ Database Connection
    if await check_db_connection():
        logger.info("✓ Database connection successful")
    else:
        logger.error("✗ Database connection failed")

    yield

    # Shutdown (Graceful)
    logger.info("Shutting down application...")
    await close_db_connection()
    logger.info("✓ Database connections closed")


# ============================================================================
# FastAPI Application Instance
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Smart Campus Service Platform API - Cloud-Ready Architecture",
    version="1.0.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security Headers (Production)
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.is_development else ["*.run.app", "*.example.com"],
    )


# ============================================================================
# Health Check Endpoints (สำหรับ Cloud Run Container Health Probes)
# ============================================================================


@app.get("/healthz", tags=["Health"])
async def health_check():
    """
    Liveness Probe - ตรวจสอบว่า Application ยังทำงานอยู่
    Google Cloud Run จะเรียก endpoint นี้เพื่อตรวจสอบ container health
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        },
    )


@app.get("/readyz", tags=["Health"])
async def readiness_check():
    """
    Readiness Probe - ตรวจสอบว่า Application พร้อมรับ traffic
    ตรวจสอบ Database connection และ dependencies อื่น ๆ
    """
    # ตรวจสอบ Database
    db_healthy = await check_db_connection()

    if not db_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "unhealthy",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "database": "healthy",
            "storage": settings.STORAGE_PROVIDER,
        },
    )


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api_docs": f"{settings.API_PREFIX}/docs",
        "health_check": "/healthz",
        "readiness_check": "/readyz",
    }


@app.get(f"{settings.API_PREFIX}", tags=["Root"])
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "Smart Campus Service API v1",
        "documentation": f"{settings.API_PREFIX}/docs",
    }


# ============================================================================
# Graceful Shutdown Handler (Cloud Run SIGTERM)
# ============================================================================


def handle_sigterm(signum, frame):
    """
    Handle SIGTERM signal สำหรับ Graceful Shutdown
    Cloud Run ส่ง SIGTERM ก่อนจะ terminate container
    """
    logger.info("Received SIGTERM signal, initiating graceful shutdown...")
    sys.exit(0)


# Register SIGTERM handler
signal.signal(signal.SIGTERM, handle_sigterm)


# ============================================================================
# Static Files (สำหรับ Local Storage)
# ============================================================================

# Mount static files directory สำหรับ serve uploaded files ใน development
if settings.STORAGE_PROVIDER == "local":
    import os
    
    storage_path = settings.LOCAL_STORAGE_PATH
    if os.path.exists(storage_path):
        app.mount("/storage", StaticFiles(directory=storage_path), name="storage")
        logger.info(f"✓ Static files mounted at /storage -> {storage_path}")


# ============================================================================
# API Routes
# ============================================================================

from app.modules.auth.router import router as auth_router
from app.modules.bookings.router import router as bookings_router
from app.modules.inventory.router import router as inventory_router
from app.modules.requests.router import router as requests_router
from app.modules.notifications.router import router as notifications_router

# Register routers
app.include_router(
    auth_router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    bookings_router,
    prefix=f"{settings.API_PREFIX}/bookings",
    tags=["Bookings"],
)

app.include_router(
    inventory_router,
    prefix=f"{settings.API_PREFIX}/inventory",
    tags=["Inventory"],
)

app.include_router(
    requests_router,
    prefix=f"{settings.API_PREFIX}/requests",
    tags=["Requests"],
)

app.include_router(
    notifications_router,
    prefix=f"{settings.API_PREFIX}/notifications",
    tags=["Notifications"],
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

from app.common.exceptions import AppException


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """Handle custom application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "details": exc.details,
        },
    )
=======
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "Smart Campus"}
>>>>>>> ace2920d97465972070607b564e16328fbfec24d
