"""bind execution state to recipe keys and retain superseded events

Revision ID: 20260923_0007
Revises: 20260919_0006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260923_0007"
down_revision = "20260919_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("plan_execution_events")}
    if "version_id" not in columns:
        op.add_column("plan_execution_events", sa.Column("version_id", sa.Integer(), nullable=True))
    if "recipe_key" not in columns:
        op.add_column("plan_execution_events", sa.Column("recipe_key", sa.String(100), nullable=True))
    if not inspect(bind).has_table("plan_execution_archive"):
        op.create_table(
            "plan_execution_archive",
            sa.Column("archive_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("day", sa.Integer(), nullable=False),
            sa.Column("meal_slot", sa.String(20), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=True),
            sa.Column("recipe_key", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("note", sa.String(500), nullable=True),
            sa.Column("archived_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_plan_execution_archive_plan_id", "plan_execution_archive", ["plan_id"])


def downgrade() -> None:
    op.drop_table("plan_execution_archive")
    with op.batch_alter_table("plan_execution_events") as batch:
        batch.drop_column("recipe_key")
        batch.drop_column("version_id")
