"""异步任务：实体关系图谱抽取。"""
import asyncio

from app.tasks.celery_app import app as celery_app


async def _extract_document(document_id: int, job_id: int | None = None) -> None:
    from sqlalchemy import select

    from app.db.session import get_session_factory
    from app.models import Chunk, DocStatus, Document
    from app.models.job import AiJob, JobStatus
    from app.services.extraction import extract_from_text
    from app.services.graph_merge import merge_extraction

    factory = get_session_factory()
    async with factory() as db:
        job = await db.get(AiJob, job_id) if job_id else None
        doc = await db.get(Document, document_id)
        if doc is None:
            return
        try:
            if job:
                job.status = JobStatus.running
                await db.commit()

            chunks = (
                await db.scalars(select(Chunk).where(Chunk.document_id == document_id))
            ).all()

            merged = 0
            if not chunks:
                # 没有 chunk（未做向量化），直接用文档内容抽取
                content = doc.content_text or ""
                if len(content) >= 60:
                    context = f"文档标题：{doc.title}\n\n{content[:3000]}"
                    result = await extract_from_text(context)
                    if result and (result.entities or result.relations):
                        await merge_extraction(doc.space_id, document_id, result)
                        merged = 1
            else:
                await db.commit()  # 释放当前事务，抽取内用独立会话

                for chunk in chunks:
                    if len(chunk.content) < 60:  # 太短的 chunk 跳过
                        continue
                    context = f"文档标题：{doc.title}\n章节：{chunk.section_path or '无'}\n\n{chunk.content}"
                    result = await extract_from_text(context)
                    if result and (result.entities or result.relations):
                        await merge_extraction(doc.space_id, document_id, result)
                        merged += 1

            if job:
                job.status = JobStatus.succeeded
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            doc.status = DocStatus.ready  # 图谱失败不影响文档可用性
            if job:
                job.status = JobStatus.failed
                job.error = str(exc)[:2000]
            await db.commit()


@celery_app.task(name="tasks.extract_document")
def extract_document(document_id: int, job_id: int | None = None) -> None:
    asyncio.run(_extract_document(document_id, job_id))


async def enqueue_extract(document_id: int, job_id: int | None = None) -> None:
    from app.core.config import get_settings

    if get_settings().debug_eager_tasks:
        await _extract_document(document_id, job_id)
    else:
        extract_document.delay(document_id, job_id)
