"""add activity level to profiles

Revision ID: 20260824_0004
Revises: 20260802_0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260824_0004"
down_revision = "20260802_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("profiles")}
    if "activity_level" not in columns:
        op.add_column(
            "profiles",
            sa.Column(
                "activity_level",
                sa.String(length=20),
                nullable=False,
                server_default="moderate",
            ),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("profiles")}
    if "activity_level" in columns:
        op.drop_column("profiles", "activity_level")
