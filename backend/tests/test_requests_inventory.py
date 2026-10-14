from tests.conftest import API, auth

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def create_request(client, user, files=None):
    return await client.post(
        f"{API}/requests",
        headers=auth(user),
        data={"title": "Broken projector", "description": "Projector in A101 does not turn on"},
        files=files,
    )


async def test_request_lifecycle(client, student, staff):
    created = await create_request(
        client, student, files=[("files", ("photo.png", PNG, "image/png"))]
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["request_number"].startswith("REQ-")
    assert len(body["attachments"]) == 1
    request_id = body["id"]

    assigned = await client.patch(
        f"{API}/requests/{request_id}/assign",
        headers=auth(staff),
        json={"assigned_staff_id": staff.id},
    )
    assert assigned.status_code == 200

    started = await client.patch(
        f"{API}/requests/{request_id}/status",
        headers=auth(staff),
        json={"status": "in_progress"},
    )
    assert started.json()["status"] == "in_progress"

    bad = await client.patch(
        f"{API}/requests/{request_id}/status", headers=auth(staff), json={"status": "pending"}
    )
    assert bad.status_code == 400

    done = await client.patch(
        f"{API}/requests/{request_id}/status",
        headers=auth(staff),
        json={"status": "completed", "resolution": "Replaced lamp"},
    )
    assert done.json()["status"] == "completed"

    feedback = await client.post(
        f"{API}/requests/{request_id}/feedback", headers=auth(student), json={"rating": 5}
    )
    assert feedback.json()["rating"] == 5

    notes = await client.get(f"{API}/notifications", headers=auth(student))
    # created + in_progress + completed
    assert notes.json()["total"] == 3


async def test_request_ownership(client, student, student2, staff):
    created = await create_request(client, student)
    request_id = created.json()["id"]
    assert (
        await client.get(f"{API}/requests/{request_id}", headers=auth(student2))
    ).status_code == 403
    assert (
        await client.get(f"{API}/requests/{request_id}", headers=auth(staff))
    ).status_code == 200
    assert (await client.get(f"{API}/requests", headers=auth(student))).status_code == 403
    assert (
        await client.patch(
            f"{API}/requests/{request_id}/status",
            headers=auth(student),
            json={"status": "in_progress"},
        )
    ).status_code == 403
    assert (
        await client.post(f"{API}/requests/{request_id}/cancel", headers=auth(student2))
    ).status_code == 403


async def test_attachment_validation_and_signed_url(client, student, student2):
    fake = await create_request(
        client, student, files=[("files", ("evil.png", b"MZ not a png", "image/png"))]
    )
    assert fake.status_code == 400

    exe = await create_request(
        client, student, files=[("files", ("run.exe", b"MZ", "application/octet-stream"))]
    )
    assert exe.status_code == 400

    created = await create_request(client, student, files=[("files", ("a.png", PNG, "image/png"))])
    request_id = created.json()["id"]
    attachment_id = created.json()["attachments"][0]["id"]
    url = await client.get(
        f"{API}/requests/{request_id}/attachments/{attachment_id}/url", headers=auth(student)
    )
    assert url.status_code == 200
    assert url.json()["url"].startswith("/storage/requests/")
    other = await client.get(
        f"{API}/requests/{request_id}/attachments/{attachment_id}/url", headers=auth(student2)
    )
    assert other.status_code == 403


async def test_inventory_crud_requires_staff(client, student, staff):
    room = {"room_number": "Z1", "room_name": "Z", "building": "Z", "floor": 1, "capacity": 10}
    assert (
        await client.post(f"{API}/inventory/rooms", headers=auth(student), json=room)
    ).status_code == 403
    created = await client.post(f"{API}/inventory/rooms", headers=auth(staff), json=room)
    assert created.status_code == 201
    dup = await client.post(f"{API}/inventory/rooms", headers=auth(staff), json=room)
    assert dup.status_code == 409

    listed = await client.get(f"{API}/inventory/rooms", headers=auth(student))
    assert listed.json()["total"] == 1

    deleted = await client.delete(
        f"{API}/inventory/rooms/{created.json()['id']}", headers=auth(staff)
    )
    assert deleted.status_code == 204


async def test_notifications_are_private(client, student, student2, room):
    await create_request(client, student)
    notes = await client.get(f"{API}/notifications", headers=auth(student))
    note_id = notes.json()["items"][0]["id"]
    assert (
        await client.patch(f"{API}/notifications/{note_id}/read", headers=auth(student2))
    ).status_code == 404
    read = await client.patch(f"{API}/notifications/{note_id}/read", headers=auth(student))
    assert read.json()["is_read"] is True


async def test_health(client):
    assert (await client.get("/healthz")).json()["status"] == "ok"
    assert (await client.get("/readyz")).status_code == 200
