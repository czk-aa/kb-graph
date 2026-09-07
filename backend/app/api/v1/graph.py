"""知识图谱查询路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.deps import CurrentUser, DbSession, require_space_role
from app.core.exceptions import NotFoundError
from app.db.session import get_session_factory

router = APIRouter(tags=["graph"])


@router.get("/spaces/{space_id}/graph/overview")
async def graph_overview(
    space_id: int,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 500,
    type_filter: str | None = None,
    search: str | None = None,
) -> dict:
    await require_space_role("member")(space_id, current_user, db)

    factory = get_session_factory()
    async with factory() as s:
        type_clause = "AND e.type = :type_filter" if type_filter else ""
        search_clause = "AND (e.name ILIKE :search OR e.name_norm ILIKE :search)" if search else ""
        nodes = (
            await s.execute(
                text(
                    f"""
                    SELECT e.id, e.name, e.type, e.mention_count, e.description
                    FROM entities e
                    WHERE e.space_id = :space_id {type_clause} {search_clause}
                    ORDER BY e.mention_count DESC
                    LIMIT :limit
                    """
                ),
                {
                    "space_id": space_id,
                    "limit": limit,
                    "type_filter": type_filter,
                    "search": f"%{search}%" if search else None,
                },
            )
        ).mappings()
        node_list = [dict(n) for n in nodes]
        node_ids = [n["id"] for n in node_list]

        edges: list[dict] = []
        if node_ids:
            rows = await s.execute(
                text(
                    """
                    SELECT id, src_id, dst_id, relation, weight
                    FROM entity_edges
                    WHERE space_id = :space_id AND src_id = ANY(:ids) AND dst_id = ANY(:ids)
                    """
                ),
                {"space_id": space_id, "ids": node_ids},
            )
            edges = [dict(r) for r in rows.mappings()]

    return {"nodes": node_list, "edges": edges}


@router.get("/spaces/{space_id}/graph/subgraph")
async def graph_subgraph(
    space_id: int,
    entity_id: int,
    current_user: CurrentUser,
    db: DbSession,
    hops: int = 2,
) -> dict:
    await require_space_role("member")(space_id, current_user, db)
    hops = min(max(hops, 1), 3)

    factory = get_session_factory()
    async with factory() as s:
        # 递归 CTE：从种子实体扩展 hops 跳
        expand = await s.execute(
            text(
                """
                WITH RECURSIVE expand AS (
                    SELECT e.dst_id AS node, 1 AS depth
                    FROM entity_edges e WHERE e.src_id = :seed
                    UNION
                    SELECT ee.dst_id, depth + 1
                    FROM entity_edges ee JOIN expand x ON ee.src_id = x.node
                    WHERE x.depth < :hops
                )
                SELECT DISTINCT node FROM expand
                """
            ),
            {"seed": entity_id, "hops": hops},
        )
        node_ids = [r[0] for r in expand] + [entity_id]

        nodes = (
            await s.execute(
                text(
                    "SELECT id, name, type, mention_count, description FROM entities "
                    "WHERE id = ANY(:ids) AND space_id = :space_id"
                ),
                {"ids": list(set(node_ids)), "space_id": space_id},
            )
        ).mappings()
        edges = (
            await s.execute(
                text(
                    "SELECT id, src_id, dst_id, relation, weight FROM entity_edges "
                    "WHERE src_id = ANY(:ids) AND dst_id = ANY(:ids) AND space_id = :space_id"
                ),
                {"ids": list(set(node_ids)), "space_id": space_id},
            )
        ).mappings()

    return {"nodes": [dict(n) for n in nodes], "edges": [dict(e) for e in edges]}


@router.get("/documents/{document_id}/graph")
async def document_graph(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> dict:
    from sqlalchemy import text as stext

    from app.models import Document

    doc = await db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    await require_space_role("member")(doc.space_id, current_user, db)

    factory = get_session_factory()
    async with factory() as s:
        rows = await s.execute(
            stext(
                """
                SELECT DISTINCT e.id, e.name, e.type, e.mention_count, e.description
                FROM chunk_entities ce
                JOIN chunks c ON c.id = ce.chunk_id
                JOIN entities e ON e.id = ce.entity_id
                WHERE c.document_id = :doc_id
                """
            ),
            {"doc_id": document_id},
        )
        nodes = [dict(r) for r in rows.mappings()]
        ids = [n["id"] for n in nodes]
        edges = []
        if ids:
            erows = await s.execute(
                stext(
                    "SELECT id, src_id, dst_id, relation, weight FROM entity_edges "
                    "WHERE src_id = ANY(:ids) AND dst_id = ANY(:ids)"
                ),
                {"ids": ids},
            )
            edges = [dict(r) for r in erows.mappings()]
    return {"nodes": nodes, "edges": edges}


@router.get("/entities/{entity_id}")
async def entity_detail(entity_id: int, current_user: CurrentUser, db: DbSession) -> dict:
    from app.models import Entity

    entity = await db.get(Entity, entity_id)
    if entity is None:
        raise NotFoundError("实体不存在")
    await require_space_role("member")(entity.space_id, current_user, db)

    factory = get_session_factory()
    async with factory() as s:
        docs = (
            await s.execute(
                text(
                    """
                    SELECT DISTINCT d.id, d.title
                    FROM chunk_entities ce
                    JOIN chunks c ON c.id = ce.chunk_id
                    JOIN documents d ON d.id = c.document_id
                    WHERE ce.entity_id = :eid
                    LIMIT 50
                    """
                ),
                {"eid": entity_id},
            )
        ).mappings()
        doc_list = [dict(d) for d in docs]

    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.type.value if hasattr(entity.type, "value") else str(entity.type),
        "description": entity.description,
        "aliases": entity.aliases,
        "mention_count": entity.mention_count,
        "documents": doc_list,
    }


@router.post("/spaces/{space_id}/graph/cleanup-orphans")
async def cleanup_orphans(
    space_id: int,
    current_user: CurrentUser,
    _: object = Depends(require_space_role("admin")),
) -> dict:
    """清理空间中无任何文档引用的孤立实体。"""
    from app.services.cleanup import cleanup_orphan_entities

    deleted = await cleanup_orphan_entities(space_id)
    return {"deleted": deleted}
