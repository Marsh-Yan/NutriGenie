"""add retry fields to ingestion jobs

Revision ID: 20260802_0003
Revises: 20260802_0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0003"
down_revision = "20260802_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("knowledge_ingestion_jobs")}
    if "retry_count" not in columns:
        op.add_column("knowledge_ingestion_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    if "max_retries" not in columns:
        op.add_column("knowledge_ingestion_jobs", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("knowledge_ingestion_jobs")}
    if "max_retries" in columns:
        op.drop_column("knowledge_ingestion_jobs", "max_retries")
    if "retry_count" in columns:
        op.drop_column("knowledge_ingestion_jobs", "retry_count")
