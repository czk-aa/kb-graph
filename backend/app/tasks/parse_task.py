"""异步任务：文档解析（上传文件 → 纯文本），完成后链式触发向量化。"""
import asyncio
from pathlib import Path

from app.tasks.celery_app import app as celery_app


async def _parse_document(job_id: int) -> None:
    from sqlalchemy import func, select

    from app.db.session import get_session_factory
    from app.models import DocStatus, Document, DocumentVersion, JobStatus
    from app.models.job import AiJob
    from app.services.parsers import parse_file

    factory = get_session_factory()
    async with factory() as db:
        job = await db.get(AiJob, job_id)
        if job is None or job.status == JobStatus.succeeded:
            return
        doc = await db.get(Document, job.document_id)
        assert doc is not None
        try:
            job.status = JobStatus.running
            await db.commit()

            text = parse_file(Path(doc.file_path))
            doc.content_text = text
            max_no = await db.scalar(
                select(func.max(DocumentVersion.version_no)).where(
                    DocumentVersion.document_id == doc.id
                )
            )
            next_version = (max_no or 0) + 1
            db.add(
                DocumentVersion(
                    document_id=doc.id,
                    version_no=next_version,
                    content_md=text,
                    created_by=doc.created_by,
                )
            )
            job.status = JobStatus.succeeded
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            job.status = JobStatus.failed
            job.error = str(exc)[:2000]
            doc.status = DocStatus.failed
            await db.commit()
            return
    # 解析成功后链式触发向量化
    from app.tasks.embed_task import enqueue_embed

    doc_id = job.document_id
    await enqueue_embed(doc_id, job_id)


@celery_app.task(name="tasks.parse_document")
def parse_document(job_id: int) -> None:
    asyncio.run(_parse_document(job_id))


async def enqueue_parse(job_id: int) -> None:
    """eager 模式（测试/无 Redis 开发）直接在当前事件循环执行；否则投递队列。"""
    from app.core.config import get_settings

    if get_settings().debug_eager_tasks:
        await _parse_document(job_id)
    else:
        parse_document.delay(job_id)
