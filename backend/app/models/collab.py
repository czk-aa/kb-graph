"""协同编辑状态持久化模型。"""
from sqlalchemy import BigInteger, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocCollabState(Base):
    __tablename__ = "doc_collab_state"

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    yupdate: Mapped[bytes] = mapped_column(LargeBinary, default=b"")