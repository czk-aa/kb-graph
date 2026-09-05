"""向量检索路由。"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_space_role
from app.db.session import get_session_factory
from app.models import Chunk, Document
from app.services.registry import get_embedding_client

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    seq: int
    section_path: str
    content: str
    score: float


@router.post("/spaces/{space_id}/search", response_model=list[SearchHit])
async def search(
    space_id: int, body: SearchRequest, current_user: CurrentUser, db: DbSession
) -> list[SearchHit]:
    await require_space_role("member")(space_id, current_user, db)

    embedder = get_embedding_client()
    query_vec = await embedder.embed_query(body.query)

    # 使用独立会话执行向量查询（与请求会话解耦，便于复用与测试）
    factory = get_session_factory()
    async with factory() as s:
        stmt = (
            select(
                Chunk.id,
                Chunk.seq,
                Chunk.section_path,
                Chunk.content,
                Chunk.embedding.cosine_distance(query_vec).label("distance"),
                Document.id.label("doc_id"),
                Document.title.label("doc_title"),
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.space_id == space_id)
            .order_by("distance")
            .limit(body.top_k)
        )
        rows = (await s.execute(stmt)).all()

    return [
        SearchHit(
            document_id=r.doc_id,
            document_title=r.doc_title,
            chunk_id=r.id,
            seq=r.seq,
            section_path=r.section_path,
            content=r.content,
            score=1.0 - r.distance,
        )
        for r in rows
    ]
