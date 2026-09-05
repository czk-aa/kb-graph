import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class JobType(str, enum.Enum):
    parse = "parse"
    embed = "embed"
    extract = "extract"
    summarize = "summarize"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class AiJob(Base, TimestampMixin):
    __tablename__ = "ai_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    space_id: Mapped[int] = mapped_column(BigInteger)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), default=None
    )
    job_type: Mapped[JobType] = mapped_column(Enum(JobType, native_enum=False, length=16))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=16), default=JobStatus.queued
    )
    error: Mapped[str | None] = mapped_column(Text, default=None)
    celery_task_id: Mapped[str | None] = mapped_column(Text, default=None)
