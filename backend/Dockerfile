# =============================================================================
# Smart Campus Backend - multi-stage image
#   development : hot reload สำหรับ docker compose
#   production  : non-root, รัน uvicorn ที่ $PORT (Cloud Run ตั้งให้เอง)
#
#   docker build --target production -t campus-api backend
# =============================================================================
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# -----------------------------------------------------------------------------
FROM base AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# -----------------------------------------------------------------------------
FROM base AS development
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements-dev.txt requirements.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
RUN mkdir -p /app/storage
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
FROM base AS production
RUN groupadd --system app && useradd --system --gid app --home /app app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    ENVIRONMENT=production
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini seed.py ./
USER app
EXPOSE 8080
# exec -> uvicorn เป็น PID 1 รับ SIGTERM จาก Cloud Run แล้วปิดตัวอย่างนุ่มนวล
CMD exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1 --no-access-log
