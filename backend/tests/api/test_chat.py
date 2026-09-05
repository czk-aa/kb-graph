"""RAG 问答 SSE 测试。"""


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        lines = block.strip().splitlines()
        event_type = None
        data = None
        for line in lines:
            if line.startswith("event: "):
                event_type = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                import json

                data = json.loads(line.removeprefix("data: "))
        if event_type:
            events.append((event_type, data))
    return events


async def _setup(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "nickname": "Alice"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "问答空间"}, headers=headers)
    ).json()["id"]
    doc = (
        await client.post(
            f"/api/v1/spaces/{space_id}/documents", json={"title": "知识文档"}, headers=headers
        )
    ).json()
    await client.put(
        f"/api/v1/documents/{doc['id']}/content",
        json={"content_text": "公司年假制度：入职满一年可休 10 天年假。"},
        headers=headers,
    )
    return headers, space_id


async def test_ask_streams_sse_events(client):
    headers, space_id = await _setup(client)
    session = (
        await client.post("/api/v1/chat/sessions", json={"space_id": space_id}, headers=headers)
    ).json()

    resp = await client.post(
        "/api/v1/chat/ask",
        json={"session_id": session["id"], "question": "年假有多少天？"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [t for t, _ in events]
    assert types[0] == "citations"
    assert "delta" in types
    assert types[-1] == "done"

    _, citations_data = events[0]
    assert len(citations_data) >= 1
    assert citations_data[0]["doc_title"] == "知识文档"

    full_answer = "".join(d["text"] for t, d in events if t == "delta")
    assert len(full_answer) > 0

    # done 事件带完整答案与引用
    _, done_data = events[-1]
    assert done_data["answer"] == full_answer
    assert done_data["citations"][0]["doc_title"] == "知识文档"


async def test_ask_persists_messages(client):
    headers, space_id = await _setup(client)
    session = (
        await client.post("/api/v1/chat/sessions", json={"space_id": space_id}, headers=headers)
    ).json()
    await client.post(
        "/api/v1/chat/ask",
        json={"session_id": session["id"], "question": "测试问题"},
        headers=headers,
    )
    messages = (
        await client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers=headers)
    ).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "测试问题"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["citations"] is not None


async def test_ask_empty_knowledge_base(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "empty@test.com", "password": "password123", "nickname": "E"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "空空间"}, headers=headers)
    ).json()["id"]
    session = (
        await client.post("/api/v1/chat/sessions", json={"space_id": space_id}, headers=headers)
    ).json()
    resp = await client.post(
        "/api/v1/chat/ask",
        json={"session_id": session["id"], "question": "任意问题"},
        headers=headers,
    )
    events = _parse_sse(resp.text)
    assert events[0][0] == "citations"
    assert events[0][1] == []
    full = "".join(d["text"] for t, d in events if t == "delta")
    assert "没有找到" in full


async def test_session_rbac(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "nickname": "Alice"},
    )
    headers_a = {"Authorization": f"Bearer {resp.json()['token']}"}
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.com", "password": "password123", "nickname": "Bob"},
    )
    headers_b = {"Authorization": f"Bearer {resp.json()['token']}"}
    space_id = (
        await client.post("/api/v1/spaces", json={"name": "S"}, headers=headers_a)
    ).json()["id"]
    session = (
        await client.post("/api/v1/chat/sessions", json={"space_id": space_id}, headers=headers_a)
    ).json()

    resp = await client.post(
        "/api/v1/chat/ask",
        json={"session_id": session["id"], "question": "hi"},
        headers=headers_b,
    )
    assert resp.status_code == 403
