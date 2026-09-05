import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow


class DocSourceType(str, enum.Enum):
    editor = "editor"
    upload = "upload"


class DocStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_space_updated", "space_id", "updated_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, default="未命名文档")
    source_type: Mapped[DocSourceType] = mapped_column(
        Enum(DocSourceType, native_enum=False, length=16), default=DocSourceType.editor
    )
    content_json: Mapped[dict | None] = mapped_column(JSONB, default=None)
    content_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus, native_enum=False, length=16), default=DocStatus.uploaded
    )
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[list | None] = mapped_column(JSONB, default=None)
    file_path: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_no"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (Index("uq_doc_version", "document_id", "version_no", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_no: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[dict | None] = mapped_column(JSONB, default=None)
    content_md: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    document: Mapped[Document] = relationship(back_populates="versions")
