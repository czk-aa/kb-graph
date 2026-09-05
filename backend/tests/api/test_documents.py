"""文档路由测试：CRUD、上传解析、版本恢复。"""
import io

import pytest


async def _setup(client):
    """注册用户、建空间，返回 headers。"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "nickname": "Alice"},
    )
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/spaces", json={"name": "空间", "description": ""}, headers=headers
    )
    return headers, resp.json()["id"]


async def test_create_document_bumps_version(client):
    headers, space_id = await _setup(client)
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/documents", json={"title": "设计文档"}, headers=headers
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["title"] == "设计文档"
    assert doc["status"] == "ready"

    resp = await client.get(f"/api/v1/documents/{doc['id']}/versions", headers=headers)
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1


async def test_put_content_and_restore(client):
    headers, space_id = await _setup(client)
    doc_id = (
        await client.post(
            f"/api/v1/spaces/{space_id}/documents", json={"title": "t"}, headers=headers
        )
    ).json()["id"]

    resp = await client.put(
        f"/api/v1/documents/{doc_id}/content",
        json={"content_text": "第一版内容"},
        headers=headers,
    )
    assert resp.status_code == 200
    resp = await client.put(
        f"/api/v1/documents/{doc_id}/content",
        json={"content_text": "第二版内容"},
        headers=headers,
    )
    assert resp.status_code == 200

    versions = (
        await client.get(f"/api/v1/documents/{doc_id}/versions", headers=headers)
    ).json()
    assert [v["version_no"] for v in versions] == [3, 2, 1]

    # 恢复到版本 2 → 产生版本 4
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/restore/2", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["content_text"] == "第一版内容"
    versions = (
        await client.get(f"/api/v1/documents/{doc_id}/versions", headers=headers)
    ).json()
    assert versions[0]["version_no"] == 4


async def test_upload_md_and_parse(client):
    headers, space_id = await _setup(client)
    files = [
        (
            "files",
            ("notes.md", io.BytesIO("# 标题\n\n关键内容 hello-kb".encode()), "text/markdown"),
        )
    ]
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/documents/upload", files=files, headers=headers
    )
    assert resp.status_code == 201
    docs = resp.json()
    assert docs[0]["title"] == "notes"

    doc_id = docs[0]["id"]
    doc = (await client.get(f"/api/v1/documents/{doc_id}", headers=headers)).json()
    # eager 模式下解析同步完成
    assert doc["status"] == "ready"
    assert "hello-kb" in doc["content_text"]

    jobs = (await client.get(f"/api/v1/documents/{doc_id}/jobs", headers=headers)).json()
    assert jobs[0]["job_type"] == "parse"
    assert jobs[0]["status"] == "succeeded"


async def test_upload_rejects_bad_type(client):
    headers, space_id = await _setup(client)
    files = [("files", ("evil.exe", io.BytesIO(b"MZ..."), "application/octet-stream"))]
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/documents/upload", files=files, headers=headers
    )
    assert resp.status_code == 422


async def test_document_rbac(client):
    headers_a, _ = await _setup(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.com", "password": "password123", "nickname": "Bob"},
    )
    headers_b = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post(
            "/api/v1/spaces", json={"name": "A的空间"}, headers=headers_a
        )
    ).json()["id"]

    # B 非成员不能列文档
    resp = await client.get(f"/api/v1/spaces/{space_id}/documents", headers=headers_b)
    assert resp.status_code == 403


async def test_delete_document(client):
    headers, space_id = await _setup(client)
    doc_id = (
        await client.post(
            f"/api/v1/spaces/{space_id}/documents", json={"title": "待删"}, headers=headers
        )
    ).json()["id"]
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 404
