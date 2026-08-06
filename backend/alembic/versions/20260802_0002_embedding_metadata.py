"""add embedding metadata to knowledge documents

Revision ID: 20260802_0002
Revises: 20260802_0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0002"
down_revision = "20260802_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_documents")}
    additions = [
        ("embedding_provider", sa.String(length=50)),
        ("embedding_model", sa.String(length=100)),
        ("embedding_dimensions", sa.Integer()),
        ("embedding_version", sa.String(length=180)),
    ]
    for name, column_type in additions:
        if name not in columns:
            op.add_column("knowledge_documents", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("knowledge_documents"):
        return
    columns = {column["name"] for column in inspector.get_columns("knowledge_documents")}
    for name in ("embedding_version", "embedding_dimensions", "embedding_model", "embedding_provider"):
        if name in columns:
            op.drop_column("knowledge_documents", name)
