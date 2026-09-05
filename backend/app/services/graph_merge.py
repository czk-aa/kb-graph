"""实体/关系入库与去重合并（Reduce，规则先行）。"""
from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import Chunk, ChunkEntity, Entity, EntityEdge, EntityType
from app.services.extraction import ExtractionResult, normalize_name


async def merge_extraction(space_id: int, document_id: int, result: ExtractionResult) -> None:
    """将抽取结果合并进图谱：实体去重、关系 upsert、chunk 映射。"""
    factory = get_session_factory()
    async with factory() as db:
        # 文档的全部 chunk（用于溯源映射）
        chunk_ids = (
            await db.scalars(select(Chunk.id).where(Chunk.document_id == document_id))
        ).all()

        # 实体合并
        name_to_entity: dict[tuple[str, str], Entity] = {}
        for ent in result.entities:
            norm = normalize_name(ent.name)
            if not norm:
                continue
            key = (norm, ent.type)
            if key in name_to_entity:
                continue
            existing = await db.scalar(
                select(Entity).where(
                    Entity.space_id == space_id,
                    Entity.name_norm == norm,
                    Entity.type == EntityType(ent.type),
                )
            )
            if existing is None:
                existing = Entity(
                    space_id=space_id,
                    name=ent.name.strip(),
                    name_norm=norm,
                    type=EntityType(ent.type),
                    description=ent.description,
                    aliases=list({normalize_name(a) for a in ent.aliases if a} - {norm}),
                    mention_count=0,
                )
                db.add(existing)
                await db.flush()
            else:
                # 合并：aliases 扩充、描述取更长者
                old_aliases = set(existing.aliases or [])
                new_aliases = {normalize_name(a) for a in ent.aliases if a}
                existing.aliases = sorted(old_aliases | new_aliases - {existing.name_norm})
                if len(ent.description) > len(existing.description):
                    existing.description = ent.description
            existing.mention_count = (existing.mention_count or 0) + 1
            name_to_entity[key] = existing

        # 名称 → 实体（含 aliases 匹配），用于关系端点解析
        all_entities = (
            await db.scalars(select(Entity).where(Entity.space_id == space_id))
        ).all()
        by_norm: dict[str, Entity] = {}
        for e in all_entities:
            by_norm[e.name_norm] = e
            for a in e.aliases or []:
                by_norm.setdefault(a, e)

        def resolve(name: str) -> Entity | None:
            norm = normalize_name(name)
            # 先看本次新抽取的
            for (n, _t), ent in name_to_entity.items():
                if n == norm:
                    return ent
            return by_norm.get(norm)

        # 关系 upsert
        for rel in result.relations:
            src = resolve(rel.source)
            dst = resolve(rel.target)
            if src is None or dst is None or src.id == dst.id:
                # 引用不存在实体 → 丢弃（阻断幻觉关联）
                continue
            edge = await db.scalar(
                select(EntityEdge).where(
                    EntityEdge.space_id == space_id,
                    EntityEdge.src_id == src.id,
                    EntityEdge.dst_id == dst.id,
                    EntityEdge.relation == rel.relation,
                )
            )
            if edge is None:
                edge = EntityEdge(
                    space_id=space_id,
                    src_id=src.id,
                    dst_id=dst.id,
                    relation=rel.relation,
                    description=rel.description,
                    weight=0,
                    evidence_chunk_ids=[],
                )
                db.add(edge)
                await db.flush()
            edge.weight = (edge.weight or 0) + 1
            if len(rel.description) > len(edge.description):
                edge.description = rel.description
            evidence = list(edge.evidence_chunk_ids or [])
            for cid in chunk_ids:
                if cid not in evidence:
                    evidence.append(cid)
            edge.evidence_chunk_ids = evidence[:20]

        # chunk ↔ entity 映射
        for ent in name_to_entity.values():
            for cid in chunk_ids:
                exists = await db.get(ChunkEntity, (cid, ent.id))
                if exists is None:
                    db.add(ChunkEntity(chunk_id=cid, entity_id=ent.id))

        await db.commit()
