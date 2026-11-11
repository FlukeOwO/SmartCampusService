"""Revision selection used by infra/gcp/ops.sh. No GCP credentials required."""

import importlib.util
from pathlib import Path

import pytest


def _traffic():
    path = Path(__file__).resolve().parents[2] / "infra" / "gcp" / "traffic.py"
    spec = importlib.util.spec_from_file_location("campus_traffic", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


traffic = _traffic()


def _rev(name, created, ready=True):
    return {
        "metadata": {"name": name, "creationTimestamp": created},
        "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False"}]},
    }


def test_rollback_skips_failed_newer_revision_and_the_one_already_serving():
    # C failed smoke and is not Ready. B is serving and bad. A is the previous good revision.
    names = traffic.ready_names(
        [
            _rev("rev-c", "2026-03-03T00:00:00Z", ready=False),
            _rev("rev-b", "2026-03-02T00:00:00Z"),
            _rev("rev-a", "2026-03-01T00:00:00Z"),
        ]
    )
    assert names == ["rev-b", "rev-a"]
    assert traffic.pick_rollback(names, "rev-b") == "rev-a"


def test_rollback_from_latest_ready_goes_to_previous():
    names = ["rev-b", "rev-a"]
    assert traffic.pick_rollback(names, "rev-b") == "rev-a"


def test_rollback_when_newest_failed_does_not_target_the_serving_revision():
    # Newest failed, so it is absent. Serving is rev-a. Roll back further, not to rev-a itself.
    names = traffic.ready_names(
        [
            _rev("rev-b", "2026-03-02T00:00:00Z", ready=False),
            _rev("rev-a", "2026-03-01T00:00:00Z"),
            _rev("rev-z", "2026-02-01T00:00:00Z"),
        ]
    )
    assert traffic.pick_rollback(names, "rev-a") == "rev-z"


def test_rollback_refuses_when_nothing_is_older():
    with pytest.raises(ValueError):
        traffic.pick_rollback(["only"], "only")


def test_promote_refuses_a_revision_that_is_not_ready():
    names = traffic.ready_names(
        [
            _rev("rev-b", "2026-03-02T00:00:00Z", ready=False),
            _rev("rev-a", "2026-03-01T00:00:00Z"),
        ]
    )
    with pytest.raises(ValueError, match="not Ready"):
        traffic.pick_promote("rev-b", names)


def test_promote_accepts_latest_when_it_is_ready():
    names = ["rev-b", "rev-a"]
    assert traffic.pick_promote("rev-b", names) == "rev-b"


def test_serving_revision_uses_highest_percent():
    service = {
        "status": {
            "traffic": [
                {"revisionName": "rev-a", "percent": 90},
                {"revisionName": "rev-b", "percent": 10},
            ]
        }
    }
    assert traffic.serving_revision(service) == "rev-a"
