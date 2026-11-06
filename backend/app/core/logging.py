"""
Logging - JSON บรรทัดเดียวต่อ log เพื่อให้ Cloud Logging อ่าน severity ได้

TraceContextMiddleware อ่าน header X-Cloud-Trace-Context ที่ Cloud Run ใส่มากับทุก request
แล้วแนบ trace ไปกับทุก log ของ request นั้น Cloud Logging จึงจัดกลุ่ม log ของ request
เดียวกันไว้ใต้ request log และเปิดดูต่อใน Cloud Trace ได้
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

from app.core.config import settings

_trace: ContextVar[tuple[str, str | None] | None] = ContextVar("trace", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
        }
        trace = _trace.get()
        if trace:
            entry["logging.googleapis.com/trace"] = trace[0]
            if trace[1]:
                entry["logging.googleapis.com/spanId"] = trace[1]
        if record.exc_info:
            entry["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def parse_cloud_trace(header: str, project_id: str) -> tuple[str, str | None] | None:
    """'TRACE_ID/SPAN_ID;o=1' -> ('projects/<p>/traces/TRACE_ID', 'SPAN_ID')"""
    if not header or not project_id:
        return None
    trace_id, _, rest = header.partition("/")
    if not trace_id:
        return None
    span_id = rest.split(";", 1)[0] or None
    return f"projects/{project_id}/traces/{trace_id}", span_id


class TraceContextMiddleware:
    """Pure ASGI middleware (ไม่บัฟเฟอร์ body จึงไม่กระทบ upload/streaming)"""

    def __init__(self, app):
        self.app = app
        self.project_id = settings.GCP_PROJECT_ID or settings.GCS_PROJECT_ID

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        header = ""
        for name, value in scope.get("headers", []):
            if name == b"x-cloud-trace-context":
                header = value.decode("latin-1")
                break
        token = _trace.set(parse_cloud_trace(header, self.project_id))
        try:
            await self.app(scope, receive, send)
        finally:
            _trace.reset(token)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL)
    # ให้ log ของ uvicorn ออกรูปแบบเดียวกัน
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
