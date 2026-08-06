"""add knowledge document and ingestion tables

Revision ID: 20260802_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("document_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("source_file", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("document_id"),
            sa.UniqueConstraint("source_file", name="uq_knowledge_source_file"),
        )
        op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"])
        op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])
    if not inspector.has_table("knowledge_chunks"):
        op.create_table(
            "knowledge_chunks",
            sa.Column("chunk_id", sa.String(length=255), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("section_title", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("chunk_id"),
        )
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
        op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])
    if not inspector.has_table("knowledge_ingestion_jobs"):
        op.create_table(
            "knowledge_ingestion_jobs",
            sa.Column("job_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
            sa.Column("stage", sa.String(length=30), nullable=False, server_default="queued"),
            sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("job_id"),
        )
        op.create_index("ix_knowledge_ingestion_jobs_document_id", "knowledge_ingestion_jobs", ["document_id"])
        op.create_index("ix_knowledge_ingestion_jobs_status", "knowledge_ingestion_jobs", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("knowledge_ingestion_jobs"):
        op.drop_table("knowledge_ingestion_jobs")
    if inspector.has_table("knowledge_chunks"):
        op.drop_table("knowledge_chunks")
    if inspector.has_table("knowledge_documents"):
        op.drop_table("knowledge_documents")
