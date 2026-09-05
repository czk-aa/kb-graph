"""对话路由：会话管理 + SSE 流式问答。"""
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_space_role
from app.core.exceptions import NotFoundError
from app.models import ChatMessage, ChatRole, ChatSession
from app.schemas.document import DocumentOut  # noqa: F401 (占位)
from app.services.rag import answer_stream, sse_format

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionCreate(BaseModel):
    space_id: int


class SessionOut(BaseModel):
    id: int
    space_id: int
    title: str
    created_at: object
    updated_at: object

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list | None
    meta: dict | None

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=1, max_length=4000)


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(body: SessionCreate, current_user: CurrentUser, db: DbSession):
    await require_space_role("member")(body.space_id, current_user, db)
    session = ChatSession(space_id=body.space_id, user_id=current_user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(space_id: int, current_user: CurrentUser, db: DbSession):
    await require_space_role("member")(space_id, current_user, db)
    rows = (
        await db.scalars(
            select(ChatSession)
            .where(ChatSession.space_id == space_id, ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc())
        )
    ).all()
    return list(rows)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(session_id: int, current_user: CurrentUser, db: DbSession):
    session = await _load_session(session_id, current_user, db)
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
        )
    ).all()
    return list(rows)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int, current_user: CurrentUser, db: DbSession) -> None:
    session = await _load_session(session_id, current_user, db)
    await db.delete(session)
    await db.commit()


async def _load_session(session_id: int, current_user, db) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise NotFoundError("会话不存在")
    await require_space_role("member")(session.space_id, current_user, db)
    return session


@router.post("/ask")
async def ask(body: AskRequest, current_user: CurrentUser, db: DbSession):
    session = await _load_session(body.session_id, current_user, db)

    # 历史窗口（最近 6 条，不含当前问题）
    history_rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(6)
        )
    ).all()
    history = [
        {"role": m.role.value, "content": m.content}
        for m in reversed(history_rows)
        if m.role in (ChatRole.user, ChatRole.assistant)
    ]

    # 落库用户消息
    db.add(ChatMessage(session_id=session.id, role=ChatRole.user, content=body.question))
    await db.commit()

    async def event_stream():
        answer_parts: list[str] = []
        final_citations: list = []
        final_meta: dict = {}
        try:
            async for event in answer_stream(history, body.question, session.space_id):
                if event["type"] == "delta":
                    answer_parts.append(event["data"]["text"])
                elif event["type"] == "done":
                    final_citations = event["data"].get("citations", [])
                    final_meta = event["data"].get("meta", {})
                yield sse_format(event)
                # 检索阶段可能较慢，发心跳防中间层超时
                if event["type"] == "citations":
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            # 客户端断连：落库已生成部分
            await _save_assistant_message(session.id, "".join(answer_parts), final_citations, final_meta)
            raise
        await _save_assistant_message(session.id, "".join(answer_parts), final_citations, final_meta)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _save_assistant_message(session_id: int, content: str, citations: list, meta: dict) -> None:
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as s:
        s.add(
            ChatMessage(
                session_id=session_id,
                role=ChatRole.assistant,
                content=content,
                citations=citations,
                meta=meta,
            )
        )
        await s.commit()
