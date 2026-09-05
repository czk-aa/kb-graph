"""entities / entity_edges / chunk_entities

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "space_id", sa.BigInteger(), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_norm", sa.Text(), nullable=False),
        sa.Column("type", sa.String(16), nullable=False, server_default="other"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("aliases", JSONB(), nullable=True),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("space_id", "name_norm", "type", name="uq_entity_norm"),
    )
    op.create_index("ix_entities_space_type", "entities", ["space_id", "type"])

    op.create_table(
        "entity_edges",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "space_id", sa.BigInteger(), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "src_id", sa.BigInteger(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "dst_id", sa.BigInteger(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("evidence_chunk_ids", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("space_id", "src_id", "dst_id", "relation", name="uq_edge"),
    )
    op.create_index("ix_edges_src", "entity_edges", ["src_id"])
    op.create_index("ix_edges_dst", "entity_edges", ["dst_id"])

    op.create_table(
        "chunk_entities",
        sa.Column(
            "chunk_id", sa.BigInteger(), sa.ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "entity_id",
            sa.BigInteger(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_chunk_entities_entity", "chunk_entities", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_chunk_entities_entity", table_name="chunk_entities")
    op.drop_table("chunk_entities")
    op.drop_index("ix_edges_dst", table_name="entity_edges")
    op.drop_index("ix_edges_src", table_name="entity_edges")
    op.drop_table("entity_edges")
    op.drop_index("ix_entities_space_type", table_name="entities")
    op.drop_table("entities")
