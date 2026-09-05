"""检索编排：v1 纯向量；v2（P6）叠加图邻居扩展与重排。"""
import time
from dataclasses import dataclass, field

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import Chunk, Document


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    seq: int
    section_path: str
    content: str
    cosine: float
    graph_boost: float = 0.0

    @property
    def score(self) -> float:
        return 0.7 * self.cosine + 0.3 * self.graph_boost


@dataclass
class RetrievalResult:
    hits: list[RetrievedChunk] = field(default_factory=list)
    expanded_entities: list[dict] = field(default_factory=list)
    elapsed_ms: int = 0


async def vector_search(space_id: int, query_vec: list[float], top_k: int) -> list[RetrievedChunk]:
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
            .limit(top_k)
        )
        rows = (await s.execute(stmt)).all()
    return [
        RetrievedChunk(
            chunk_id=r.id,
            document_id=r.doc_id,
            document_title=r.doc_title,
            seq=r.seq,
            section_path=r.section_path,
            content=r.content,
            cosine=1.0 - r.distance,
        )
        for r in rows
    ]


async def retrieve(
    space_id: int,
    query: str,
    query_vec: list[float],
    top_k: int | None = None,
    context_k: int | None = None,
) -> RetrievalResult:
    """检索入口：P6 前为纯向量；P6 在此叠加图扩展。"""
    from app.core.config import get_settings

    settings = get_settings()
    started = time.perf_counter()
    k = top_k or settings.search_top_k
    hits = await vector_search(space_id, query_vec, k)
    result = RetrievalResult(
        hits=hits, elapsed_ms=int((time.perf_counter() - started) * 1000)
    )
    if context_k is not None:
        result.hits = result.hits[:context_k]
    return result
