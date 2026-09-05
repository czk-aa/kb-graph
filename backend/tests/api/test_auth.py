"""注册/登录/鉴权测试。"""
import pytest


async def register(client, email="a@test.com", password="password123", nickname="Alice"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "nickname": nickname},
    )


async def login(client, email="a@test.com", password="password123"):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_register_login_me(client):
    resp = await register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "a@test.com"
    assert body["token"]

    resp = await login(client)
    assert resp.status_code == 200
    token = resp.json()["token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "Alice"


async def test_register_duplicate_email(client):
    await register(client)
    resp = await register(client, nickname="Bob")
    assert resp.status_code == 409


async def test_register_weak_password(client):
    resp = await register(client, password="short")
    assert resp.status_code == 422


async def test_login_wrong_password(client):
    await register(client)
    resp = await login(client, password="wrong-password")
    assert resp.status_code == 401


async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/spaces"])
async def test_spaces_require_auth(client, path):
    resp = await client.get(path)
    assert resp.status_code == 401
