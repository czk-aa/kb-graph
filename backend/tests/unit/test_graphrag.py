"""GraphRAG 混合检索单元测试：种子图 + 邻居扩展 + 重排。"""
import pytest

from app.services.retrieval import _chunks_of_entities, _expand_neighbors, _entities_from_chunks


async def _seed_graph(db):
    """构造图：FastAPI --uses--> PostgreSQL --uses--> pgvector，各实体挂 chunk。"""
    from app.models import (
        Chunk,
        ChunkEntity,
        Document,
        Entity,
        EntityEdge,
        EntityType,
        Space,
        User,
    )

    user = User(email="g@test.com", password_hash="x", nickname="G")
    db.add(user)
    await db.flush()
    space = Space(name="图空间", owner_id=user.id)
    db.add(space)
    await db.flush()
    doc = Document(space_id=space.id, title="种子文档", created_by=user.id)
    db.add(doc)
    await db.flush()

    space_id = space.id
    ents = {}
    for name in ["FastAPI", "PostgreSQL", "pgvector"]:
        e = Entity(space_id=space_id, name=name, name_norm=name.lower(), type=EntityType.technology)
        db.add(e)
        await db.flush()
        ents[name] = e

    edges = [
        ("FastAPI", "PostgreSQL", 3),
        ("PostgreSQL", "pgvector", 2),
    ]
    for src, dst, w in edges:
        db.add(
            EntityEdge(
                space_id=space_id,
                src_id=ents[src].id,
                dst_id=ents[dst].id,
                relation="uses",
                weight=w,
            )
        )

    chunks = {}
    for i, name in enumerate(["FastAPI", "PostgreSQL", "pgvector"]):
        c = Chunk(
            document_id=1,
            space_id=space_id,
            seq=i,
            content=f"{name} chunk content",
            token_count=10,
            content_hash=f"hash{i}",
        )
        db.add(c)
        await db.flush()
        chunks[name] = c
        db.add(ChunkEntity(chunk_id=c.id, entity_id=ents[name].id))
    await db.commit()
    return ents, chunks


async def test_entities_from_chunks(db):
    ents, chunks = await _seed_graph(db)
    result = await _entities_from_chunks([chunks["FastAPI"].id], max_entities=5)
    assert len(result) == 1
    assert result[0]["name"] == "FastAPI"


async def test_expand_neighbors_two_hops(db):
    ents, chunks = await _seed_graph(db)
    neighbors = await _expand_neighbors([ents["FastAPI"].id], hops=2, max_neighbors=15)
    nodes = {n["node"] for n in neighbors}
    assert ents["PostgreSQL"].id in nodes
    assert ents["pgvector"].id in nodes  # 2 跳可达
    # 权重排序：PostgreSQL(3) 在 pgvector(2) 前
    order = [n["node"] for n in neighbors]
    assert order.index(ents["PostgreSQL"].id) < order.index(ents["pgvector"].id)


async def test_chunks_of_entities(db):
    ents, chunks = await _seed_graph(db)
    ids = await _chunks_of_entities([ents["PostgreSQL"].id, ents["pgvector"].id])
    assert chunks["PostgreSQL"].id in ids
    assert chunks["pgvector"].id in ids
