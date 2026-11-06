import json
import logging

from app.core.logging import JsonFormatter, _trace, parse_cloud_trace


def test_parse_cloud_trace():
    assert parse_cloud_trace("abc123/456;o=1", "proj") == ("projects/proj/traces/abc123", "456")
    assert parse_cloud_trace("abc123", "proj") == ("projects/proj/traces/abc123", None)
    assert parse_cloud_trace("", "proj") is None
    assert parse_cloud_trace("abc123/1", "") is None


def test_json_formatter_includes_trace():
    record = logging.LogRecord("t", logging.WARNING, __file__, 1, "hello %s", ("x",), None)
    token = _trace.set(("projects/p/traces/t1", "9"))
    try:
        entry = json.loads(JsonFormatter().format(record))
    finally:
        _trace.reset(token)
    assert entry["severity"] == "WARNING"
    assert entry["message"] == "hello x"
    assert entry["logging.googleapis.com/trace"] == "projects/p/traces/t1"
    assert entry["logging.googleapis.com/spanId"] == "9"
    assert "logging.googleapis.com/trace" not in json.loads(JsonFormatter().format(record))


async def test_middleware_passes_requests(client):
    resp = await client.get("/healthz", headers={"X-Cloud-Trace-Context": "abc/1;o=1"})
    assert resp.status_code == 200
