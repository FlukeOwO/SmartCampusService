# =============================================================================
# Multi-stage Dockerfile for Smart Campus Service Backend
# Optimized for both Development and Production (Cloud Run)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Python Image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies Builder
# -----------------------------------------------------------------------------
FROM python-base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Development Image (Hot Reload)
# -----------------------------------------------------------------------------
FROM python-base as development

# Copy dependencies from builder
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Development command (with auto-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Stage 4: Production Builder (Compile Python files)
# -----------------------------------------------------------------------------
FROM dependencies as production-builder

# Copy application code
COPY . .

# Compile Python files for faster startup
RUN python -m compileall -b /app

# Remove source .py files (keep only .pyc)
# RUN find /app -name "*.py" -type f -delete

# -----------------------------------------------------------------------------
# Stage 5: Production Image (Minimal, Cloud Run Ready)
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    WORKERS=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/storage && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/healthz || exit 1

# Production command
# Cloud Run recommends single worker with async framework
CMD exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-1} \
    --loop uvloop \
    --http httptools \
    --no-access-log

# -----------------------------------------------------------------------------
# Build Instructions:
# -----------------------------------------------------------------------------
# Development:
#   docker build --target development -t campus-backend:dev .
#
# Production:
#   docker build --target production -t campus-backend:prod .
#
# For Cloud Run:
#   docker build --target production -t gcr.io/PROJECT_ID/campus-backend:latest .
#   docker push gcr.io/PROJECT_ID/campus-backend:latest
#   gcloud run deploy campus-backend \
#     --image gcr.io/PROJECT_ID/campus-backend:latest \
#     --platform managed \
#     --region asia-southeast1 \
#     --allow-unauthenticated
# -----------------------------------------------------------------------------
