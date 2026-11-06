from datetime import UTC, datetime, timedelta

from tests.conftest import API, auth


async def _book(client, user, room_id, start):
    return await client.post(
        f"{API}/bookings/rooms",
        headers=auth(user),
        json={
            "room_id": room_id,
            "title": "Meeting",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        },
    )


async def test_dashboard_requires_staff(client, student):
    resp = await client.get(f"{API}/dashboard/summary", headers=auth(student))
    assert resp.status_code == 403


async def test_dashboard_summary_counts(client, student, staff, room):
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    first = await _book(client, student, room.id, start)
    await _book(client, student, room.id, start + timedelta(hours=2))
    await client.put(f"{API}/bookings/{first.json()['id']}/approve", headers=auth(staff))

    created = await client.post(
        f"{API}/requests",
        headers=auth(student),
        data={"title": "Broken chair", "description": "Chair in A101 is broken"},
    )
    request_id = created.json()["id"]
    await client.patch(
        f"{API}/requests/{request_id}/status", headers=auth(staff), json={"status": "in_progress"}
    )
    await client.patch(
        f"{API}/requests/{request_id}/status",
        headers=auth(staff),
        json={"status": "completed", "resolution": "Replaced"},
    )
    await client.post(
        f"{API}/requests",
        headers=auth(student),
        data={"title": "Wifi is down", "description": "No wifi on floor 3 of building B"},
    )

    resp = await client.get(f"{API}/dashboard/summary?days=7", headers=auth(staff))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["window_days"] == 7
    assert body["requests"]["total"] == 2
    assert body["requests"]["by_status"] == {"completed": 1, "pending": 1}
    assert body["requests"]["open_unassigned"] == 1
    assert body["requests"]["avg_resolution_hours"] is not None
    assert body["bookings"]["total"] == 2
    assert body["bookings"]["pending_approval"] == 1
    assert body["bookings"]["upcoming_confirmed"] == 1
    assert body["top_rooms"][0] == {
        "room_id": room.id,
        "room_number": room.room_number,
        "room_name": room.room_name,
        "bookings": 2,
    }
    assert len(body["daily"]) == 8
    today = body["daily"][-1]
    assert today["requests"] == 2 and today["bookings"] == 2
    assert body["users_by_role"] == {"student": 1, "staff": 1}


async def test_dashboard_empty(client, admin):
    resp = await client.get(f"{API}/dashboard/summary", headers=auth(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["requests"]["total"] == 0
    assert body["requests"]["avg_resolution_hours"] is None
    assert body["top_rooms"] == []
    assert len(body["daily"]) == 31
