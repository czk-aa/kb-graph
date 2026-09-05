"""评论模型。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_document", "document_id", "created_at"),
        Index("ix_comments_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), default=None)
    content: Mapped[str] = mapped_column(Text)
    # 可选：评论关联到文档中的位置（段落/行号）
    anchor: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
    replies: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="parent", cascade="all, delete-orphan", lazy="selectin"
    )
    parent: Mapped["Comment | None"] = relationship("Comment", remote_side="Comment.id", back_populates="replies")