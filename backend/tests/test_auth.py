from app.common.constants import UserRole
from app.core.security import create_refresh_token
from tests.conftest import API, auth, make_user


async def test_register_always_creates_student(client):
    resp = await client.post(
        f"{API}/auth/register",
        json={
            "email": "New@Test.dev",
            "password": "password123",
            "full_name": "New User",
            "role": "admin",  # ต้องถูกเพิกเฉย
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "student"
    assert body["email"] == "new@test.dev"
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflict(client, student):
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": student.email, "password": "password123", "full_name": "Dup"},
    )
    assert resp.status_code == 409
    assert set(resp.json()) == {"message", "details"}


async def test_register_validation_error_format(client):
    resp = await client.post(f"{API}/auth/register", json={"email": "bad", "password": "x"})
    assert resp.status_code == 422
    assert resp.json()["message"] == "Invalid request data"


async def test_login_and_refresh(client):
    user = await make_user(UserRole.STUDENT, email="login@test.dev")
    resp = await client.post(
        f"{API}/auth/login", json={"email": "login@test.dev", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["user"]["id"] == user.id

    me = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "login@test.dev"

    refreshed = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_login_wrong_password(client, student):
    resp = await client.post(
        f"{API}/auth/login", json={"email": student.email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(client, student):
    token = create_refresh_token(student.id)
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_access_token_cannot_be_used_to_refresh(client, student):
    access = auth(student)["Authorization"].split()[1]
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


async def test_missing_token_is_401(client):
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401


async def test_list_users_requires_admin(client, student, staff, admin):
    assert (await client.get(f"{API}/auth/users", headers=auth(student))).status_code == 403
    assert (await client.get(f"{API}/auth/users", headers=auth(staff))).status_code == 403
    resp = await client.get(f"{API}/auth/users", headers=auth(admin))
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


async def test_admin_creates_staff_and_changes_role(client, admin, student):
    resp = await client.post(
        f"{API}/auth/users",
        headers=auth(admin),
        json={
            "email": "staff2@test.dev",
            "password": "password123",
            "full_name": "Staff Two",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "staff"

    resp = await client.patch(
        f"{API}/auth/users/{student.id}", headers=auth(admin), json={"role": "staff"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "staff"


async def test_deactivated_user_token_rejected(client, admin, student):
    headers = auth(student)
    await client.patch(
        f"{API}/auth/users/{student.id}", headers=auth(admin), json={"is_active": False}
    )
    assert (await client.get(f"{API}/auth/me", headers=headers)).status_code == 401


async def test_login_rate_limited(client):
    from app.core.rate_limit import limiter

    limiter.enabled = True
    limiter.reset()
    try:
        payload = {"email": "nobody@test.dev", "password": "wrong-password"}
        codes = [
            (await client.post(f"{API}/auth/login", json=payload)).status_code for _ in range(6)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
