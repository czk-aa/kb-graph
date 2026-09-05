"""知识图谱抽取与查询测试。"""
import pytest


async def _setup_doc(client, content: str):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "nickname": "Alice"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "图谱空间"}, headers=headers)
    ).json()["id"]
    doc = (
        await client.post(
            f"/api/v1/spaces/{space_id}/documents", json={"title": "技术文档"}, headers=headers
        )
    ).json()
    resp = await client.put(
        f"/api/v1/documents/{doc['id']}/content",
        json={"content_text": content},
        headers=headers,
    )
    assert resp.status_code == 200
    return headers, space_id, doc["id"]


LONG_CONTENT = (
    "# 架构说明\n\n"
    "FastAPI uses PostgreSQL as the primary database. "
    "FastAPI uses PostgreSQL for vector storage. "
    "FastAPI uses PostgreSQL for the queue backend. "
    "FastAPI uses PostgreSQL for caching. "
    "FastAPI uses PostgreSQL for sessions. "
    "FastAPI uses PostgreSQL for everything. "
    "FastAPI uses PostgreSQL. " * 3
)


async def test_extract_creates_graph(client):
    headers, space_id, doc_id = await _setup_doc(client, LONG_CONTENT)
    # PUT content 已链式触发 embed → extract（eager 同步）
    resp = await client.get(f"/api/v1/spaces/{space_id}/graph/overview", headers=headers)
    assert resp.status_code == 200
    graph = resp.json()
    names = {n["name"] for n in graph["nodes"]}
    assert "FastAPI" in names
    assert "PostgreSQL" in names
    assert len(graph["edges"]) >= 1
    edge = graph["edges"][0]
    assert edge["relation"] == "uses"
    assert edge["weight"] >= 1


async def test_extract_dedup(client):
    """重复抽取同一实体应合并（mention_count 增加）而非重复创建。"""
    headers, space_id, doc_id = await _setup_doc(client, LONG_CONTENT)
    # 再次手动触发抽取
    resp = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert resp.status_code == 202
    graph = (await client.get(f"/api/v1/spaces/{space_id}/graph/overview", headers=headers)).json()
    fastapi = [n for n in graph["nodes"] if n["name"] == "FastAPI"]
    assert len(fastapi) == 1
    assert fastapi[0]["mention_count"] >= 2


async def test_subgraph_expansion(client):
    headers, space_id, doc_id = await _setup_doc(client, LONG_CONTENT)
    overview = (await client.get(f"/api/v1/spaces/{space_id}/graph/overview", headers=headers)).json()
    fastapi_id = next(n["id"] for n in overview["nodes"] if n["name"] == "FastAPI")
    resp = await client.get(
        f"/api/v1/spaces/{space_id}/graph/subgraph?entity_id={fastapi_id}&hops=2", headers=headers
    )
    assert resp.status_code == 200
    sub = resp.json()
    assert any(n["name"] == "PostgreSQL" for n in sub["nodes"])
    assert len(sub["edges"]) >= 1


async def test_document_graph_and_entity_detail(client):
    headers, space_id, doc_id = await _setup_doc(client, LONG_CONTENT)
    dgraph = (await client.get(f"/api/v1/documents/{doc_id}/graph", headers=headers)).json()
    assert len(dgraph["nodes"]) >= 2

    entity_id = dgraph["nodes"][0]["id"]
    detail = (await client.get(f"/api/v1/entities/{entity_id}", headers=headers)).json()
    assert detail["name"] in {"FastAPI", "PostgreSQL"}
    assert any(d["id"] == doc_id for d in detail["documents"])


async def test_graph_rbac(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.com", "password": "password123", "nickname": "Bob"},
    )
    headers_b = {"Authorization": f"Bearer {resp.json()['token']}"}
    resp = await client.get("/api/v1/spaces/9999/graph/overview", headers=headers_b)
    assert resp.status_code == 403

