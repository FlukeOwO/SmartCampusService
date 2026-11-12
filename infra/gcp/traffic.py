#!/usr/bin/env python3
"""Pick Cloud Run revisions for ops.sh promote / canary / rollback.

latestCreatedRevisionName can be a revision that failed to become Ready.
The revision created immediately before it can be the one already serving,
so a naive "second newest" rollback is a no-op (or worse, targets the bad revision).

rollback: newest Ready revision strictly older than the one serving traffic.
promote/canary: the latest created revision, but only when that revision is Ready.
"""

from __future__ import annotations

import argparse
import json
import sys


def ready_names(revisions: list[dict]) -> list[str]:
    """Ready revision names, newest first."""
    ready: list[tuple[str, str]] = []
    for rev in revisions:
        conditions = (rev.get("status") or {}).get("conditions") or []
        is_ready = any(
            cond.get("type") == "Ready" and cond.get("status") == "True" for cond in conditions
        )
        if not is_ready:
            continue
        meta = rev.get("metadata") or {}
        name = meta.get("name") or ""
        if name:
            ready.append((meta.get("creationTimestamp") or "", name))
    ready.sort(reverse=True)
    return [name for _, name in ready]


def serving_revision(service: dict) -> str:
    """Revision currently receiving the most traffic."""
    traffic = (service.get("status") or {}).get("traffic") or []
    best_name = ""
    best_percent = -1
    for item in traffic:
        if item.get("percent") is not None:
            percent = int(item["percent"])
        elif item.get("latestRevision"):
            percent = 100
        else:
            percent = 0
        if percent > best_percent and item.get("revisionName"):
            best_percent = percent
            best_name = item["revisionName"]
    return best_name


def pick_rollback(ready_newest_first: list[str], serving: str) -> str:
    """Newest Ready revision created before the one that is serving."""
    if not serving:
        raise ValueError("no revision is serving traffic")
    if serving not in ready_newest_first:
        raise ValueError(f"serving revision {serving} is not Ready")
    older = ready_newest_first[ready_newest_first.index(serving) + 1 :]
    if not older:
        raise ValueError(f"no older Ready revision to roll back to (serving {serving})")
    return older[0]


def pick_promote(latest_created: str, ready_newest_first: list[str]) -> str:
    """Latest created revision, refused when it is not Ready."""
    if not ready_newest_first:
        raise ValueError("no Ready revision")
    if not latest_created:
        raise ValueError("could not read the latest created revision")
    latest_ready = ready_newest_first[0]
    if latest_created != latest_ready:
        raise ValueError(
            f"latest revision {latest_created} is not Ready; "
            f"refusing to send it traffic (latest Ready is {latest_ready})"
        )
    return latest_ready


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pick a Cloud Run revision")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serving")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--serving", required=True)
    promote = sub.add_parser("promote")
    promote.add_argument("--latest-created", required=True)
    args = parser.parse_args(argv)
    raw = json.load(sys.stdin)
    try:
        if args.command == "serving":
            name = serving_revision(raw)
            if not name:
                raise ValueError("no revision is serving traffic")
            print(name)
        elif args.command == "rollback":
            print(pick_rollback(ready_names(raw), args.serving))
        else:
            print(pick_promote(args.latest_created, ready_names(raw)))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
