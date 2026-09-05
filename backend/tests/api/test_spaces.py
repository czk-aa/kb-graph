"""空间与 RBAC 测试。"""
import pytest


async def _register_and_login(client, email, nickname):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "nickname": nickname},
    )
    token = resp.json()["token"]
    return token, {"Authorization": f"Bearer {token}"}


async def _create_space(client, headers, name="研发空间"):
    return await client.post(
        "/api/v1/spaces", json={"name": name, "description": "测试空间"}, headers=headers
    )


async def test_create_and_list_spaces(client):
    _, headers = await _register_and_login(client, "a@test.com", "Alice")
    resp = await _create_space(client, headers)
    assert resp.status_code == 201
    assert resp.json()["my_role"] == "owner"

    resp = await client.get("/api/v1/spaces", headers=headers)
    assert resp.status_code == 200
    spaces = resp.json()
    assert len(spaces) == 1
    assert spaces[0]["name"] == "研发空间"


async def test_non_member_cannot_access_space(client):
    _, headers_a = await _register_and_login(client, "a@test.com", "Alice")
    _, headers_b = await _register_and_login(client, "b@test.com", "Bob")

    resp = await _create_space(client, headers_a)
    space_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/spaces/{space_id}", headers=headers_b)
    assert resp.status_code == 403


async def test_member_can_read_admin_can_manage(client):
    _, headers_a = await _register_and_login(client, "a@test.com", "Alice")
    _, headers_b = await _register_and_login(client, "b@test.com", "Bob")
    resp = await _create_space(client, headers_a)
    space_id = resp.json()["id"]

    # A 把 B 加为 admin
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/members",
        json={"email": "b@test.com", "role": "admin"},
        headers=headers_a,
    )
    assert resp.status_code == 201

    # B（admin）可以改空间
    resp = await client.patch(
        f"/api/v1/spaces/{space_id}", json={"name": "改名"}, headers=headers_b
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名"

    # B（admin）不能删空间
    resp = await client.delete(f"/api/v1/spaces/{space_id}", headers=headers_b)
    assert resp.status_code == 403


async def test_member_role_cannot_manage_members(client):
    _, headers_a = await _register_and_login(client, "a@test.com", "Alice")
    _, headers_b = await _register_and_login(client, "b@test.com", "Bob")
    _, headers_c = await _register_and_login(client, "c@test.com", "Carol")
    space_id = (await _create_space(client, headers_a)).json()["id"]

    await client.post(
        f"/api/v1/spaces/{space_id}/members",
        json={"email": "b@test.com", "role": "member"},
        headers=headers_a,
    )

    # B 是普通成员，无权加人
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/members",
        json={"email": "c@test.com"},
        headers=headers_b,
    )
    assert resp.status_code == 403


async def test_add_member_unknown_user(client):
    _, headers_a = await _register_and_login(client, "a@test.com", "Alice")
    space_id = (await _create_space(client, headers_a)).json()["id"]
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/members",
        json={"email": "ghost@test.com"},
        headers=headers_a,
    )
    assert resp.status_code == 404


async def test_cannot_remove_owner(client):
    _, headers_a = await _register_and_login(client, "a@test.com", "Alice")
    _, headers_b = await _register_and_login(client, "b@test.com", "Bob")
    space_id = (await _create_space(client, headers_a)).json()["id"]
    owner_id = (await client.get("/api/v1/auth/me", headers=headers_a)).json()["id"]
    await client.post(
        f"/api/v1/spaces/{space_id}/members",
        json={"email": "b@test.com", "role": "admin"},
        headers=headers_a,
    )
    resp = await client.delete(f"/api/v1/spaces/{space_id}/members/{owner_id}", headers=headers_b)
    assert resp.status_code == 403
