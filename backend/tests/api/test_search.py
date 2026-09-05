"""向量检索测试。"""


async def _setup_with_docs(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "nickname": "Alice"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "检索空间"}, headers=headers)
    ).json()["id"]

    for title, content in [
        ("Python教程", "Python 是一门编程语言。 #python\n\nFlask 是 Python 的 web 框架。"),
        ("数据库指南", "PostgreSQL 是关系型数据库。 #database\n\npgvector 支持向量检索。"),
    ]:
        doc = (
            await client.post(
                f"/api/v1/spaces/{space_id}/documents", json={"title": title}, headers=headers
            )
        ).json()
        resp = await client.put(
            f"/api/v1/documents/{doc['id']}/content",
            json={"content_text": content, "content_json": None},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
    return headers, space_id


async def test_search_hits_relevant_document(client):
    headers, space_id = await _setup_with_docs(client)
    resp = await client.post(
        f"/api/v1/spaces/{space_id}/search",
        json={"query": "pgvector", "top_k": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    hits = resp.json()
    assert len(hits) >= 1
    # 包含 pgvector 关键词的文档应出现在结果中（FakeEmbedding 分桶语义下该 token 必然命中）
    titles = {h["document_title"] for h in hits}
    assert "数据库指南" in titles


async def test_search_rbac(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.com", "password": "password123", "nickname": "Bob"},
    )
    headers_b = {"Authorization": f"Bearer {resp.json()['token']}"}
    resp = await client.post(
        "/api/v1/spaces/999/search", json={"query": "x"}, headers=headers_b
    )
    assert resp.status_code == 403
