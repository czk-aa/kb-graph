import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EntityType(str, enum.Enum):
    person = "person"
    organization = "organization"
    concept = "concept"
    technology = "technology"
    product = "product"
    event = "event"
    other = "other"


class Entity(Base, TimestampMixin):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("space_id", "name_norm", "type", name="uq_entity_norm"),
        Index("ix_entities_space_type", "space_id", "type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    name_norm: Mapped[str] = mapped_column(Text)
    type: Mapped[EntityType] = mapped_column(Enum(EntityType, native_enum=False, length=16))
    description: Mapped[str] = mapped_column(Text, default="")
    aliases: Mapped[list | None] = mapped_column(JSONB, default=list)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)

    src_edges: Mapped[list["EntityEdge"]] = relationship(
        back_populates="src", foreign_keys="EntityEdge.src_id", cascade="all, delete-orphan"
    )
    dst_edges: Mapped[list["EntityEdge"]] = relationship(
        back_populates="dst", foreign_keys="EntityEdge.dst_id", cascade="all, delete-orphan"
    )


class EntityEdge(Base, TimestampMixin):
    __tablename__ = "entity_edges"
    __table_args__ = (
        UniqueConstraint("space_id", "src_id", "dst_id", "relation", name="uq_edge"),
        Index("ix_edges_src", "src_id"),
        Index("ix_edges_dst", "dst_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    src_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    dst_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    relation: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[int] = mapped_column(Integer, default=1)
    evidence_chunk_ids: Mapped[list | None] = mapped_column(JSONB, default=list)

    src: Mapped[Entity] = relationship(back_populates="src_edges", foreign_keys=[src_id])
    dst: Mapped[Entity] = relationship(back_populates="dst_edges", foreign_keys=[dst_id])


class ChunkEntity(Base):
    """chunk 与实体的映射（GraphRAG 检索桥）。"""

    __tablename__ = "chunk_entities"
    __table_args__ = (Index("ix_chunk_entities_entity", "entity_id"),)

    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
