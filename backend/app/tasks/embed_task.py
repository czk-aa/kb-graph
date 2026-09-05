"""异步任务：分块 + 向量化入库。"""
import asyncio
import hashlib

from app.tasks.celery_app import app as celery_app


async def _embed_document(document_id: int, job_id: int | None = None) -> None:
    from sqlalchemy import select

    from app.db.session import get_session_factory
    from app.models import DocStatus, Document
    from app.models.chunk import Chunk
    from app.models.job import AiJob, JobStatus
    from app.services.chunker import chunk_text, count_tokens
    from app.services.registry import get_embedding_client

    factory = get_session_factory()
    async with factory() as db:
        job = await db.get(AiJob, job_id) if job_id else None
        doc = await db.get(Document, document_id)
        assert doc is not None
        try:
            if job:
                job.status = JobStatus.running
                await db.commit()

            doc.status = DocStatus.processing
            await db.commit()

            pieces = chunk_text(doc.content_text or "")
            if not pieces:
                doc.status = DocStatus.ready
                if job:
                    job.status = JobStatus.succeeded
                await db.commit()
                return

            embedder = get_embedding_client()
            texts = [p["content"] for p in pieces]
            vectors = await embedder.embed_texts(texts)

            # 幂等：先清除旧 chunks（内容可能已变化；MVP 采用整篇重建）
            existing = (
                await db.scalars(select(Chunk).where(Chunk.document_id == doc.id))
            ).all()
            old_hashes = {c.seq: c.content_hash for c in existing}
            for c in existing:
                await db.delete(c)
            await db.flush()

            for p, vec in zip(pieces, vectors, strict=True):
                db.add(
                    Chunk(
                        document_id=doc.id,
                        space_id=doc.space_id,
                        seq=p["seq"],
                        content=p["content"],
                        token_count=count_tokens(p["content"]),
                        section_path=p.get("section_path", ""),
                        embedding=vec,
                        content_hash=hashlib.sha256(p["content"].encode("utf-8")).hexdigest(),
                    )
                )
            doc.status = DocStatus.ready
            if job:
                job.status = JobStatus.succeeded
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            doc.status = DocStatus.failed
            if job:
                job.status = JobStatus.failed
                job.error = str(exc)[:2000]
            await db.commit()
            raise

    # 向量化完成后链式触发图谱抽取
    from app.tasks.extract_task import enqueue_extract

    await enqueue_extract(document_id, job_id)


@celery_app.task(name="tasks.embed_document")
def embed_document(document_id: int, job_id: int | None = None) -> None:
    asyncio.run(_embed_document(document_id, job_id))


async def enqueue_embed(document_id: int, job_id: int | None = None) -> None:
    """eager 模式（测试/无 Redis 开发）直接在当前事件循环执行；否则投递队列。"""
    from app.core.config import get_settings

    if get_settings().debug_eager_tasks:
        await _embed_document(document_id, job_id)
    else:
        embed_document.delay(document_id, job_id)
