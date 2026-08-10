"""add AI-native plan versions, messages, and generation runs

Revision ID: 20260810_0004
Revises: 20260802_0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260810_0004"
down_revision = "20260802_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    meal_plan_columns = {column["name"] for column in inspector.get_columns("meal_plans")}
    if "current_version_id" not in meal_plan_columns:
        op.add_column("meal_plans", sa.Column("current_version_id", sa.Integer(), nullable=True))

    tables = set(inspector.get_table_names())
    if "meal_plan_versions" not in tables:
        op.create_table(
            "meal_plan_versions",
            sa.Column("version_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("parent_version_id", sa.Integer(), nullable=True),
            sa.Column("trigger_message_id", sa.Integer(), nullable=True),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("validation_json", sa.JSON(), nullable=True),
            sa.Column("model_name", sa.String(length=120), nullable=True),
            sa.Column("prompt_version", sa.String(length=80), nullable=True),
            sa.Column("rag_meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_meal_plan_versions_plan_id", "meal_plan_versions", ["plan_id"])
        op.create_index("ix_meal_plan_versions_parent_version_id", "meal_plan_versions", ["parent_version_id"])

    if "meal_plan_messages" not in tables:
        op.create_table(
            "meal_plan_messages",
            sa.Column("message_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_id", sa.Integer(), sa.ForeignKey("meal_plan_versions.version_id", ondelete="SET NULL"), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("action_json", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="accepted"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_meal_plan_messages_plan_id", "meal_plan_messages", ["plan_id"])
        op.create_index("ix_meal_plan_messages_version_id", "meal_plan_messages", ["version_id"])

    if "meal_plan_runs" not in tables:
        op.create_table(
            "meal_plan_runs",
            sa.Column("run_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False),
            sa.Column("base_version_id", sa.Integer(), nullable=True),
            sa.Column("trigger_message_id", sa.Integer(), nullable=True),
            sa.Column("client_request_id", sa.String(length=100), nullable=True),
            sa.Column("status", sa.Enum("pending", "running", "completed", "failed"), nullable=False, server_default="pending"),
            sa.Column("current_node", sa.String(length=80), nullable=True),
            sa.Column("repair_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("output_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_meal_plan_runs_plan_id", "meal_plan_runs", ["plan_id"])
        op.create_index("ix_meal_plan_runs_base_version_id", "meal_plan_runs", ["base_version_id"])
        op.create_index("ix_meal_plan_runs_trigger_message_id", "meal_plan_runs", ["trigger_message_id"])
        op.create_index("ix_meal_plan_runs_client_request_id", "meal_plan_runs", ["client_request_id"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "meal_plan_messages" in tables:
        op.drop_table("meal_plan_messages")
    if "meal_plan_runs" in tables:
        op.drop_table("meal_plan_runs")
    if "meal_plan_versions" in tables:
        op.drop_table("meal_plan_versions")
    columns = {column["name"] for column in inspector.get_columns("meal_plans")}
    if "current_version_id" in columns:
        op.drop_column("meal_plans", "current_version_id")
