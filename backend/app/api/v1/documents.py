"""文档路由：CRUD、上传、版本。"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, require_space_role
from app.core.exceptions import NotFoundError, ValidationError
from app.models import DocSourceType, DocStatus, Document, DocumentVersion, JobType, JobStatus
from app.models import SpaceRole
from app.models.job import AiJob
from app.schemas.document import (
    DocumentContentPut,
    DocumentCreate,
    DocumentDetailOut,
    DocumentOut,
    DocumentUpdate,
    DocumentVersionOut,
    JobOut,
)
from app.services.parsers import SUPPORTED_EXTS

router = APIRouter(tags=["documents"])

MemberRequired = Depends(require_space_role("member"))

# 协同房间活跃的文档集合（P7 填充使用；此处预留互斥检查）
_ACTIVE_COLLAB: set[int] = set()


def collab_is_active(document_id: int) -> bool:
    return document_id in _ACTIVE_COLLAB


async def _load_doc(db, document_id: int) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    return doc


async def _bump_version(db, doc: Document, user_id: int, content_text: str, content_json: dict | None) -> int:
    next_no = (
        await db.scalar(
            select(func.max(DocumentVersion.version_no)).where(
                DocumentVersion.document_id == doc.id
            )
        )
        or 0
    ) + 1
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version_no=next_no,
            content_md=content_text,
            content_json=content_json,
            created_by=user_id,
        )
    )
    return next_no


def _save_upload(space_id: int, filename: str, data: bytes) -> Path:
    settings = get_settings()
    if len(data) > settings.upload_max_bytes:
        raise ValidationError("文件超过 20MB 限制")
    ext = Path(filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".md", ".markdown"]:
        raise ValidationError(f"不支持的文件类型：{ext}（支持 {'/'.join(SUPPORTED_EXTS)}）")
    base = Path(settings.uploads_dir) / str(space_id)
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    return path


@router.get("/spaces/{space_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    space_id: int,
    current_user: CurrentUser,
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    _: object = MemberRequired,
) -> list[DocumentOut]:
    stmt = select(Document).where(Document.space_id == space_id)
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Document.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    docs = (await db.scalars(stmt)).all()
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/spaces/{space_id}/documents", response_model=DocumentDetailOut, status_code=201)
async def create_document(
    space_id: int,
    body: DocumentCreate,
    current_user: CurrentUser,
    db: DbSession,
    _: object = MemberRequired,
) -> DocumentDetailOut:
    doc = Document(
        space_id=space_id,
        title=body.title,
        source_type=DocSourceType.editor,
        status=DocStatus.ready,
        content_text="",
        created_by=current_user.id,
    )
    db.add(doc)
    await db.flush()
    await _bump_version(db, doc, current_user.id, "", None)
    await db.commit()
    await db.refresh(doc)
    return DocumentDetailOut.model_validate(doc)


@router.post(
    "/spaces/{space_id}/documents/upload", response_model=list[DocumentDetailOut], status_code=201
)
async def upload_documents(
    space_id: int,
    files: list[UploadFile],
    current_user: CurrentUser,
    db: DbSession,
    _: object = MemberRequired,
) -> list[DocumentDetailOut]:
    out: list[DocumentDetailOut] = []
    docs: list[Document] = []
    job_ids: list[int] = []
    for file in files:
        data = await file.read()
        path = _save_upload(space_id, file.filename or "untitled.md", data)
        title = Path(file.filename or "未命名文档").stem
        doc = Document(
            space_id=space_id,
            title=title,
            source_type=DocSourceType.upload,
            status=DocStatus.uploaded,
            content_text="",
            file_path=str(path),
            created_by=current_user.id,
        )
        db.add(doc)
        await db.flush()
        job = AiJob(space_id=space_id, document_id=doc.id, job_type=JobType.parse)
        db.add(job)
        await db.flush()
        job_ids.append(job.id)
        docs.append(doc)
    await db.commit()
    # 提交后再入队，任务在独立会话中可见
    from app.tasks.parse_task import enqueue_parse

    for jid in job_ids:
        await enqueue_parse(jid)
    for doc in docs:
        await db.refresh(doc)
        out.append(DocumentDetailOut.model_validate(doc))
    return out


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
async def get_document(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> DocumentDetailOut:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    return DocumentDetailOut.model_validate(doc)


@router.patch("/documents/{document_id}", response_model=DocumentDetailOut)
async def update_document(
    document_id: int,
    body: DocumentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentDetailOut:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    if body.title is not None:
        doc.title = body.title
    await db.commit()
    await db.refresh(doc)
    return DocumentDetailOut.model_validate(doc)


@router.put("/documents/{document_id}/content", response_model=DocumentDetailOut)
async def put_document_content(
    document_id: int,
    body: DocumentContentPut,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentDetailOut:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    if collab_is_active(doc.id):
        from app.core.exceptions import ConflictError

        raise ConflictError("文档正被多人协同编辑，内容保存走协同通道")
    doc.content_json = body.content_json
    doc.content_text = body.content_text
    if doc.status == DocStatus.failed:
        doc.status = DocStatus.ready
    await _bump_version(db, doc, current_user.id, body.content_text, body.content_json)
    await db.commit()
    await db.refresh(doc)
    # 内容变化 → 重新向量化
    if body.content_text:
        from app.tasks.embed_task import enqueue_embed

        await enqueue_embed(doc.id)
    return DocumentDetailOut.model_validate(doc)


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionOut])
async def list_versions(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> list[DocumentVersionOut]:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    rows = (
        await db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_no.desc())
        )
    ).all()
    return [DocumentVersionOut.model_validate(v) for v in rows]


@router.get("/documents/{document_id}/versions/{version_no}", response_model=DocumentVersionOut)
async def get_version(
    document_id: int,
    version_no: int,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentVersionOut:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    ver = await db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id, DocumentVersion.version_no == version_no
        )
    )
    if ver is None:
        raise NotFoundError("版本不存在")
    return DocumentVersionOut.model_validate(ver)


@router.post("/documents/{document_id}/restore/{version_no}", response_model=DocumentDetailOut)
async def restore_version(
    document_id: int,
    version_no: int,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentDetailOut:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    ver = await db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id, DocumentVersion.version_no == version_no
        )
    )
    if ver is None:
        raise NotFoundError("版本不存在")
    doc.content_text = ver.content_md
    doc.content_json = ver.content_json
    await _bump_version(db, doc, current_user.id, ver.content_md, ver.content_json)
    await db.commit()
    await db.refresh(doc)
    return DocumentDetailOut.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> None:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    await db.delete(doc)
    await db.commit()


@router.post("/documents/{document_id}/extract", response_model=JobOut, status_code=202)
async def trigger_extract(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> JobOut:
    """手动触发图谱抽取。"""
    from app.tasks.extract_task import enqueue_extract

    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    job = AiJob(space_id=doc.space_id, document_id=doc.id, job_type=JobType.extract)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await enqueue_extract(doc.id, job.id)
    return JobOut.model_validate(job)


@router.get("/documents/{document_id}/jobs", response_model=list[JobOut])
async def list_document_jobs(
    document_id: int, current_user: CurrentUser, db: DbSession
) -> list[JobOut]:
    doc = await _load_doc(db, document_id)
    await require_space_role("member")(doc.space_id, current_user, db)
    rows = (
        await db.scalars(
            select(AiJob).where(AiJob.document_id == doc.id).order_by(AiJob.created_at.desc())
        )
    ).all()
    return [JobOut.model_validate(j) for j in rows]
