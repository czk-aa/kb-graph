"""通知模型。"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
import enum


class NotifyType(str, enum.Enum):
    comment_created = "comment_created"
    comment_replied = "comment_replied"
    doc_updated = "doc_updated"
    job_completed = "job_completed"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    type: Mapped[NotifyType] = mapped_column(Enum(NotifyType, native_enum=False, length=32))
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text, default="")
    # 关联对象ID（根据 type 不同含义不同：document_id / comment_id / job_id）
    ref_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821