import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from tests.conftest import API, auth


def slot(hours_from_now: int = 24, duration_hours: int = 2):
    start = (datetime.now(UTC) + timedelta(hours=hours_from_now)).replace(microsecond=0)
    return start, start + timedelta(hours=duration_hours)


def room_payload(room_id: int, start: datetime, end: datetime, **extra):
    return {
        "room_id": room_id,
        "title": "Study group",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        **extra,
    }


async def test_book_room_success_and_notification(client, student, room):
    start, end = slot()
    resp = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, start, end)
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "pending"

    stats = await client.get(f"{API}/notifications/stats/summary", headers=auth(student))
    assert stats.json() == {"total": 1, "unread": 1, "read": 0}


async def test_overlapping_booking_conflict(client, student, student2, room):
    start, end = slot()
    first = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, start, end)
    )
    assert first.status_code == 201
    overlap = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student2),
        json=room_payload(room.id, start + timedelta(hours=1), end + timedelta(hours=1)),
    )
    assert overlap.status_code == 409


async def test_adjacent_booking_allowed(client, student, room):
    start, end = slot()
    a = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, start, end)
    )
    b = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json=room_payload(room.id, end, end + timedelta(hours=1)),
    )
    assert (a.status_code, b.status_code) == (201, 201)


async def test_concurrent_bookings_one_wins(client, student, student2, room):
    """จองช่วงเดียวกันพร้อมกัน 2 request ต้องได้ 201 หนึ่งครั้งและ 409 หนึ่งครั้ง"""
    start, end = slot()
    payload = room_payload(room.id, start, end)
    results = await asyncio.gather(
        client.post(f"{API}/bookings/rooms", headers=auth(student), json=payload),
        client.post(f"{API}/bookings/rooms", headers=auth(student2), json=payload),
    )
    assert sorted(r.status_code for r in results) == [201, 409]


async def test_many_concurrent_bookings_only_one_succeeds(client, student, room):
    start, end = slot()
    payload = room_payload(room.id, start, end)
    results = await asyncio.gather(
        *[
            client.post(f"{API}/bookings/rooms", headers=auth(student), json=payload)
            for _ in range(5)
        ]
    )
    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 1
    assert codes.count(409) == 4


async def test_exclusion_constraint_blocks_overlap_in_db(student, room):
    """ชั้นที่ 2: แม้ข้ามโค้ดไป insert ตรง DB ก็ต้องโดนปฏิเสธ"""
    start, end = slot()
    insert = text(
        "INSERT INTO bookings (user_id, room_id, title, start_time, end_time, status) "
        "VALUES (:u, :r, 't', :s, :e, 'pending')"
    )
    async with AsyncSessionLocal() as db:
        await db.execute(insert, {"u": student.id, "r": room.id, "s": start, "e": end})
        await db.commit()
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                insert,
                {"u": student.id, "r": room.id, "s": start + timedelta(minutes=30), "e": end},
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            assert "no_overlap_room" in str(exc)
        else:
            raise AssertionError("overlapping insert was accepted")


async def test_cancelled_booking_frees_slot(client, student, student2, room):
    start, end = slot()
    first = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, start, end)
    )
    booking_id = first.json()["id"]
    cancel = await client.put(
        f"{API}/bookings/{booking_id}/cancel",
        headers=auth(student),
        json={"cancellation_reason": "plans changed"},
    )
    assert cancel.status_code == 200
    again = await client.post(
        f"{API}/bookings/rooms", headers=auth(student2), json=room_payload(room.id, start, end)
    )
    assert again.status_code == 201


async def test_booking_validation_rules(client, student, room):
    past_start = datetime.now(UTC) - timedelta(hours=2)
    resp = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json=room_payload(room.id, past_start, past_start + timedelta(hours=1)),
    )
    assert resp.status_code == 400

    start, _ = slot()
    too_short = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json=room_payload(room.id, start, start + timedelta(minutes=5)),
    )
    assert too_short.status_code == 400

    far = datetime.now(UTC) + timedelta(days=120)
    too_far = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json=room_payload(room.id, far, far + timedelta(hours=1)),
    )
    assert too_far.status_code == 400

    over_capacity = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json=room_payload(room.id, *slot(), attendees_count=500),
    )
    assert over_capacity.status_code == 400

    naive = await client.post(
        f"{API}/bookings/rooms",
        headers=auth(student),
        json={
            "room_id": room.id,
            "title": "x",
            "start_time": "2030-01-01T10:00:00",
            "end_time": "2030-01-01T11:00:00",
        },
    )
    assert naive.status_code == 422


async def test_unavailable_room_rejected(client, student, staff, room):
    await client.patch(
        f"{API}/inventory/rooms/{room.id}", headers=auth(staff), json={"status": "maintenance"}
    )
    resp = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, *slot())
    )
    assert resp.status_code == 400


async def test_equipment_booking_limits(client, student, equipment):
    start, _ = slot()
    ok = await client.post(
        f"{API}/bookings/equipments",
        headers=auth(student),
        json={
            "equipment_id": equipment.id,
            "title": "Event",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(days=3)).isoformat(),
        },
    )
    assert ok.status_code == 201
    too_long = await client.post(
        f"{API}/bookings/equipments",
        headers=auth(student),
        json={
            "equipment_id": equipment.id,
            "title": "Event",
            "start_time": (start + timedelta(days=10)).isoformat(),
            "end_time": (start + timedelta(days=18)).isoformat(),
        },
    )
    assert too_long.status_code == 400


async def test_approve_reject_requires_staff(client, student, staff, room):
    first = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, *slot())
    )
    booking_id = first.json()["id"]

    denied = await client.put(f"{API}/bookings/{booking_id}/approve", headers=auth(student))
    assert denied.status_code == 403

    approved = await client.put(f"{API}/bookings/{booking_id}/approve", headers=auth(staff))
    assert approved.status_code == 200
    assert approved.json()["status"] == "confirmed"
    assert approved.json()["approved_by"] == staff.id

    again = await client.put(
        f"{API}/bookings/{booking_id}/reject",
        headers=auth(staff),
        json={"rejection_reason": "late"},
    )
    assert again.status_code == 400


async def test_students_only_see_own_bookings(client, student, student2, staff, room):
    first = await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, *slot())
    )
    booking_id = first.json()["id"]

    assert (
        await client.get(f"{API}/bookings/{booking_id}", headers=auth(student2))
    ).status_code == 403
    assert (
        await client.get(f"{API}/bookings/{booking_id}", headers=auth(staff))
    ).status_code == 200
    assert (await client.get(f"{API}/bookings", headers=auth(student))).status_code == 403

    mine = await client.get(f"{API}/bookings/me", headers=auth(student2))
    assert mine.json()["total"] == 0

    cancel = await client.put(
        f"{API}/bookings/{booking_id}/cancel",
        headers=auth(student2),
        json={"cancellation_reason": "not mine"},
    )
    assert cancel.status_code == 403


async def test_availability(client, student, room):
    start, end = slot()
    await client.post(
        f"{API}/bookings/rooms", headers=auth(student), json=room_payload(room.id, start, end)
    )
    resp = await client.get(
        f"{API}/bookings/rooms/{room.id}/availability",
        headers=auth(student),
        params={
            "start_time": (start - timedelta(hours=1)).isoformat(),
            "end_time": (end + timedelta(hours=1)).isoformat(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert len(body["busy_slots"]) == 1
