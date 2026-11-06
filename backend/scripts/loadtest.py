"""
Load test เบื้องต้น: จำลองผู้ใช้พร้อมกัน N คน เรียก endpoint ที่ใช้บ่อยเป็นเวลา D วินาที
แล้วสรุป throughput, latency (p50/p95/p99) และ error rate
ระหว่างรันให้เปิด Cloud Monitoring dashboard ดูจำนวน instance ที่ Cloud Run scale ขึ้น

    python scripts/loadtest.py --base-url https://<service>/api/v1 --users 50 --duration 60
"""

import asyncio
import random
import statistics
import sys
import time
from collections import Counter

import httpx
from _client import base_parser, login

ENDPOINTS = [
    ("/inventory/rooms", 4),
    ("/inventory/equipments", 2),
    ("/bookings/me", 2),
    ("/notifications/stats/summary", 3),
    ("/requests/me", 1),
]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


async def user(client, headers, deadline, latencies, codes):
    paths = [path for path, _ in ENDPOINTS]
    weights = [weight for _, weight in ENDPOINTS]
    while time.perf_counter() < deadline:
        path = random.choices(paths, weights)[0]
        started = time.perf_counter()
        try:
            resp = await client.get(path, headers=headers)
            codes[resp.status_code] += 1
        except httpx.HTTPError as exc:
            codes[type(exc).__name__] += 1
            continue
        latencies.append((time.perf_counter() - started) * 1000)


async def main() -> int:
    parser = base_parser(__doc__)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--duration", type=int, default=30, help="seconds")
    args = parser.parse_args()

    limits = httpx.Limits(max_connections=args.users, max_keepalive_connections=args.users)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30, limits=limits) as client:
        # login ครั้งเดียวแล้วใช้ token ร่วมกัน (login จำกัด 5 ครั้ง/นาที/IP)
        headers = await login(client, args.email, args.password)
        latencies: list[float] = []
        codes: Counter = Counter()
        print(f"{args.users} users for {args.duration}s against {args.base_url}")
        started = time.perf_counter()
        deadline = started + args.duration
        await asyncio.gather(
            *[user(client, headers, deadline, latencies, codes) for _ in range(args.users)]
        )
        elapsed = time.perf_counter() - started

    total = sum(codes.values())
    errors = sum(n for code, n in codes.items() if not (isinstance(code, int) and code < 400))
    print(f"requests    {total} ({total / elapsed:.1f} req/s)")
    if latencies:
        print(
            f"latency ms  p50={percentile(latencies, 50):.0f} p95={percentile(latencies, 95):.0f} "
            f"p99={percentile(latencies, 99):.0f} mean={statistics.mean(latencies):.0f}"
        )
    print(f"errors      {errors} ({errors / max(total, 1):.1%})  {dict(codes)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
