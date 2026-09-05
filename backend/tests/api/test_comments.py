"""评论 API 测试。"""
import pytest


async def _setup(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "c@test.com", "password": "password123", "nickname": "Charlie"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "评论空间"}, headers=headers)
    ).json()["id"]
    doc = (
        await client.post(
            f"/api/v1/spaces/{space_id}/documents", json={"title": "评论文档"}, headers=headers
        )
    ).json()
    return headers, space_id, doc["id"]


async def test_create_and_list_comments(client):
    headers, space_id, doc_id = await _setup(client)

    # 创建评论
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/comments",
        json={"content": "第一条评论"},
        headers=headers,
    )
    assert resp.status_code == 201
    c = resp.json()
    assert c["content"] == "第一条评论"
    assert c["user"]["nickname"] == "Charlie"

    # 创建回复
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/comments",
        json={"content": "回复评论", "parent_id": c["id"]},
        headers=headers,
    )
    assert resp.status_code == 201

    # 列表
    resp = await client.get(f"/api/v1/documents/{doc_id}/comments", headers=headers)
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 1
    assert len(comments[0]["replies"]) == 1
    assert comments[0]["replies"][0]["content"] == "回复评论"


async def test_delete_comment(client):
    headers, space_id, doc_id = await _setup(client)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/comments",
        json={"content": "待删除"},
        headers=headers,
    )
    comment_id = resp.json()["id"]

    # 他人不能删除
    resp2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "d@test.com", "password": "password123", "nickname": "Dave"},
    )
    headers2 = {"Authorization": f"Bearer {resp2.json()['token']}"}
    resp = await client.delete(f"/api/v1/comments/{comment_id}", headers=headers2)
    assert resp.status_code == 403

    # 自己可以删除
    resp = await client.delete(f"/api/v1/comments/{comment_id}", headers=headers)
    assert resp.status_code == 204


async def test_notifications(client):
    headers, space_id, doc_id = await _setup(client)

    # 创建评论会触发通知给文档所有者
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/comments",
        json={"content": "有通知的评论"},
        headers=headers,
    )
    assert resp.status_code == 201

    # 查看通知
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    notifs = resp.json()
    # 文档所有者是自己，评论者也是自己，所以不会给自己发通知
    # 但至少通知API可用
    assert isinstance(notifs, list)


async def test_notifications_mark_read(client):
    headers, space_id, doc_id = await _setup(client)

    # 先查看通知列表
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200

    # 全部标记已读
    resp = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert resp.status_code == 204