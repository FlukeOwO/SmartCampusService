"""
สาธิตการกันจองซ้อน: ยิงคำขอจองห้องเดียวกัน ช่วงเวลาเดียวกัน พร้อมกัน N ครั้ง
ผลที่ถูกต้องคือ 201 หนึ่งครั้ง ที่เหลือ 409 ทั้งหมด

    python scripts/demo_race.py --base-url https://<service>/api/v1 --concurrency 20
"""

import asyncio
import random
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta

import httpx
from _client import base_parser, login


async def main() -> int:
    parser = base_parser(__doc__)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--room-id", type=int, help="ไม่ระบุ = ใช้ห้องแรกที่จองได้")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        headers = await login(client, args.email, args.password)
        room_id = args.room_id
        if room_id is None:
            params = {"bookable": True, "status": "available"}
            rooms = await client.get("/inventory/rooms", params=params, headers=headers)
            rooms.raise_for_status()
            if not rooms.json()["items"]:
                print("no bookable room found")
                return 1
            room_id = rooms.json()["items"][0]["id"]

        # สุ่มช่วงเวลาในอนาคตเพื่อให้รันซ้ำได้โดยไม่ชนกับรอบก่อน
        start = (datetime.now(UTC) + timedelta(days=random.randint(2, 60))).replace(
            hour=random.randint(1, 10), minute=0, second=0, microsecond=0
        )
        payload = {
            "room_id": room_id,
            "title": "Race condition demo",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        }
        print(f"room {room_id}, slot {start:%Y-%m-%d %H:%M} UTC")
        print(f"sending {args.concurrency} identical requests at once")

        responses = await asyncio.gather(
            *[
                client.post("/bookings/rooms", json=payload, headers=headers)
                for _ in range(args.concurrency)
            ]
        )
        codes = Counter(r.status_code for r in responses)
        for code, count in sorted(codes.items()):
            print(f"  HTTP {code}: {count}")

        ok = codes.get(201) == 1 and codes.get(409, 0) == args.concurrency - 1
        print("PASS: exactly one booking succeeded" if ok else "FAIL: unexpected result")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
