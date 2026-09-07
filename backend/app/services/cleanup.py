"""数据清洗：孤立实体清理。"""

from sqlalchemy import text

from app.db.session import get_session_factory


async def cleanup_orphan_entities(space_id: int) -> int:
    """删除空间中没有任何 chunk_entities 映射的孤立实体，返回删除数量。"""
    factory = get_session_factory()
    async with factory() as s:
        result = await s.execute(
            text(
                """
                DELETE FROM entities
                WHERE id NOT IN (
                    SELECT DISTINCT entity_id FROM chunk_entities
                )
                AND space_id = :space_id
                """
            ),
            {"space_id": space_id},
        )
        await s.commit()
        deleted = result.rowcount or 0
    return deleted