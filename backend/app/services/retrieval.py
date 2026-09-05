"""检索编排：v2 GraphRAG 混合检索（向量 top-k → 图邻居扩展 → 加权重排）。

score = 0.7 × cosine + 0.3 × graph_boost
graph_boost 按扩展实体命中排名归一（rank1=1.0 递减），无图命中退化为纯向量。
"""
import time
from dataclasses import dataclass, field

from sqlalchemy import select, text

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


async def _entities_from_chunks(chunk_ids: list[int], max_entities: int) -> list[dict]:
    """命中 chunk → 关联实体（按提及度排序）。"""
    if not chunk_ids:
        return []
    factory = get_session_factory()
    async with factory() as s:
        rows = await s.execute(
            text(
                """
                SELECT e.id, e.name, e.type, e.mention_count, COUNT(ce.chunk_id) AS hit_chunks
                FROM chunk_entities ce
                JOIN entities e ON e.id = ce.entity_id
                WHERE ce.chunk_id = ANY(:ids)
                GROUP BY e.id, e.name, e.type, e.mention_count
                ORDER BY hit_chunks DESC, e.mention_count DESC
                LIMIT :limit
                """
            ),
            {"ids": chunk_ids, "limit": max_entities},
        )
        return [dict(r) for r in rows.mappings()]


async def _expand_neighbors(entity_ids: list[int], hops: int, max_neighbors: int) -> list[dict]:
    """递归 CTE 图扩展，按权重取 top 邻居。"""
    if not entity_ids:
        return []
    factory = get_session_factory()
    async with factory() as s:
        rows = await s.execute(
            text(
                """
                WITH RECURSIVE expand AS (
                    SELECT e.dst_id AS node, 1 AS depth, e.weight AS w
                    FROM entity_edges e WHERE e.src_id = ANY(:seeds)
                    UNION
                    SELECT ee.dst_id, depth + 1, ee.weight
                    FROM entity_edges ee JOIN expand x ON ee.src_id = x.node
                    WHERE x.depth < :hops
                )
                SELECT node, SUM(w) AS total_weight, MIN(depth) AS depth
                FROM expand WHERE node <> ALL(:seeds)
                GROUP BY node ORDER BY total_weight DESC LIMIT :limit
                """
            ),
            {"seeds": entity_ids, "hops": hops, "limit": max_neighbors},
        )
        return [dict(r) for r in rows.mappings()]


async def _chunks_of_entities(entity_ids: list[int], per_entity: int = 3) -> list[int]:
    """实体反查关联 chunk（每个实体取 per_entity 个）。"""
    if not entity_ids:
        return []
    factory = get_session_factory()
    async with factory() as s:
        rows = await s.execute(
            text(
                """
                SELECT DISTINCT ON (entity_id) entity_id, chunk_id
                FROM (
                    SELECT ce.entity_id, ce.chunk_id,
                           ROW_NUMBER() OVER (PARTITION BY ce.entity_id ORDER BY c.updated_at DESC) AS rn
                    FROM chunk_entities ce JOIN chunks c ON c.id = ce.chunk_id
                    WHERE ce.entity_id = ANY(:ids)
                ) t
                WHERE rn <= :per
                """
            ),
            {"ids": entity_ids, "per": per_entity},
        )
        return [r[1] for r in rows]


async def retrieve(
    space_id: int,
    query: str,
    query_vec: list[float],
    top_k: int | None = None,
    context_k: int | None = None,
) -> RetrievalResult:
    """GraphRAG 混合检索入口；无图命中时退化为纯向量。"""
    from app.core.config import get_settings

    settings = get_settings()
    started = time.perf_counter()
    k = top_k or settings.search_top_k

    # ① 向量召回
    hits = await vector_search(space_id, query_vec, k)
    if not hits:
        return RetrievalResult(elapsed_ms=int((time.perf_counter() - started) * 1000))

    # ② 命中 chunk → 实体
    chunk_ids = [h.chunk_id for h in hits]
    entities = await _entities_from_chunks(chunk_ids, max_entities=5)
    if not entities:
        return RetrievalResult(
            hits=hits[:context_k], elapsed_ms=int((time.perf_counter() - started) * 1000)
        )

    # ③ 图扩展（1-2 跳）
    entity_ids = [e["id"] for e in entities]
    neighbors = await _expand_neighbors(entity_ids, hops=2, max_neighbors=15)

    # ④ 邻居实体反查 chunk → 候选池
    neighbor_ids = [n["node"] for n in neighbors]
    graph_chunk_ids = await _chunks_of_entities(neighbor_ids)
    graph_chunk_set = set(graph_chunk_ids) - set(chunk_ids)

    # ⑤ 候选 chunk 详情 + graph_boost 重排
    expanded_entities = [
        {
            "seed_entities": [e["name"] for e in entities],
            "expanded": [n["node"] for n in neighbors],
            "graph_chunks": len(graph_chunk_set),
        }
    ]

    candidate_map: dict[int, RetrievedChunk] = {h.chunk_id: h for h in hits}
    if graph_chunk_set:
        factory = get_session_factory()
        async with factory() as s:
            stmt = (
                select(
                    Chunk.id,
                    Chunk.seq,
                    Chunk.section_path,
                    Chunk.content,
                    Document.id.label("doc_id"),
                    Document.title.label("doc_title"),
                )
                .join(Document, Document.id == Chunk.document_id)
                .where(Chunk.id.in_(graph_chunk_set))
            )
            rows = (await s.execute(stmt)).all()
        # graph_boost 按邻居权重排名归一
        total_weight = sum(n["total_weight"] for n in neighbors) or 1
        boost_by_chunk: dict[int, float] = {}
        chunk_to_entity = {}
        if graph_chunk_set:
            factory2 = get_session_factory()
            async with factory2() as s:
                rows2 = await s.execute(
                    text(
                        "SELECT ce.chunk_id, ce.entity_id FROM chunk_entities ce "
                        "WHERE ce.chunk_id = ANY(:ids)"
                    ),
                    {"ids": list(graph_chunk_set)},
                )
                for r in rows2:
                    chunk_to_entity.setdefault(r[0], []).append(r[1])
        weight_by_entity = {n["node"]: n["total_weight"] for n in neighbors}
        for cid in graph_chunk_set:
            ents = chunk_to_entity.get(cid, [])
            w = max((weight_by_entity.get(eid, 0) for eid in ents), default=0)
            boost_by_chunk[cid] = min(w / total_weight, 1.0)
        for r in rows:
            candidate_map[r.id] = RetrievedChunk(
                chunk_id=r.id,
                document_id=r.doc_id,
                document_title=r.doc_title,
                seq=r.seq,
                section_path=r.section_path,
                content=r.content,
                cosine=0.0,  # 图补充候选无向量分；由 boost 主导
                graph_boost=boost_by_chunk.get(r.id, 0.0),
            )

    # ⑥ 重排取 top context_k
    ranked = sorted(candidate_map.values(), key=lambda h: h.score, reverse=True)
    result = RetrievalResult(
        hits=ranked[: (context_k or settings.retrieve_context_k)],
        expanded_entities=expanded_entities,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
    return result
