"""异步任务：AI 摘要与标签生成。"""
import asyncio
import json

from app.tasks.celery_app import app as celery_app


SUMMARY_PROMPT = """你是企业知识库助手。请根据以下文档内容生成：
1. 一段简洁的摘要（不超过200字）
2. 3-5个标签（关键词，逗号分隔）

请严格以JSON格式输出：{"summary": "...", "tags": "tag1, tag2, tag3"}

文档内容：
{content}"""


async def _summarize_document(document_id: int, job_id: int | None = None) -> None:
    from sqlalchemy import select

    from app.db.session import get_session_factory
    from app.models import Document
    from app.models.job import AiJob, JobStatus
    from app.models.notification import Notification, NotifyType
    from app.services.registry import get_llm_client

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

            # 截取文档内容前 3000 字符用于摘要
            content = (doc.content_text or "")[:3000]
            if not content.strip():
                if job:
                    job.status = JobStatus.succeeded
                    await db.commit()
                return

            llm = get_llm_client()
            result = await llm.chat_json(
                "你是一个专业的知识管理助手，只输出JSON格式，不要输出其他内容。",
                SUMMARY_PROMPT.format(content=content),
            )

            summary = (result.get("summary") or "")[:500]
            tags = result.get("tags", "")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()][:10]
            elif isinstance(tags, list):
                tags = tags[:10]
            else:
                tags = []

            doc.summary = summary
            doc.tags = tags
            if job:
                job.status = JobStatus.succeeded

            # 通知文档创建者
            if doc.created_by:
                db.add(
                    Notification(
                        user_id=doc.created_by,
                        space_id=doc.space_id,
                        type=NotifyType.job_completed,
                        title=f"文档「{doc.title}」的AI摘要已生成",
                        body=summary[:200],
                        ref_id=doc.id,
                    )
                )
            await db.commit()

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            if job:
                job.status = JobStatus.failed
                job.error = str(exc)[:2000]
            await db.commit()


@celery_app.task(name="tasks.summarize_document")
def summarize_document(document_id: int, job_id: int | None = None) -> None:
    asyncio.run(_summarize_document(document_id, job_id))


async def enqueue_summarize(document_id: int, job_id: int | None = None) -> None:
    from app.core.config import get_settings

    if get_settings().debug_eager_tasks:
        await _summarize_document(document_id, job_id)
    else:
        summarize_document.delay(document_id, job_id)