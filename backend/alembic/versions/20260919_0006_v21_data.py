"""add V2.1 plan metadata, execution, feedback, and pantry tables

Revision ID: 20260919_0006
Revises: 20260919_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260919_0006"
down_revision = "20260919_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("meal_plans")}
    for name, column in (
        ("title", sa.Column("title", sa.String(100), nullable=True)),
        ("source_plan_id", sa.Column("source_plan_id", sa.Integer(), nullable=True)),
        ("archived_at", sa.Column("archived_at", sa.DateTime(), nullable=True)),
    ):
        if name not in columns:
            op.add_column("meal_plans", column)
    foreign_keys = {tuple(key["constrained_columns"]) for key in inspect(bind).get_foreign_keys("meal_plans")}
    if ("source_plan_id",) not in foreign_keys and bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_meal_plans_source", "meal_plans", "meal_plans", ["source_plan_id"], ["plan_id"], ondelete="SET NULL")
    indexes = {index["name"] for index in inspect(bind).get_indexes("meal_plans")}
    if "ix_meal_plans_profile_created" not in indexes:
        op.create_index("ix_meal_plans_profile_created", "meal_plans", ["profile_id", "created_at"])
    if "ix_meal_plans_profile_archived" not in indexes:
        op.create_index("ix_meal_plans_profile_archived", "meal_plans", ["profile_id", "archived_at"])

    if not inspect(bind).has_table("plan_execution_events"):
        op.create_table(
        "plan_execution_events",
        sa.Column("event_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("meal_slot", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("plan_id", "day", "meal_slot", name="uq_plan_execution_slot"),
        )
    for name in ("plan_id", "user_id"):
        if f"ix_plan_execution_events_{name}" not in {index["name"] for index in inspect(bind).get_indexes("plan_execution_events")}:
            op.create_index(f"ix_plan_execution_events_{name}", "plan_execution_events", [name])

    if not inspect(bind).has_table("user_feedback"):
        op.create_table(
        "user_feedback",
        sa.Column("feedback_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("meal_plans.plan_id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.recipe_id", ondelete="SET NULL"), nullable=True),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    for name in ("user_id", "plan_id", "recipe_id"):
        if f"ix_user_feedback_{name}" not in {index["name"] for index in inspect(bind).get_indexes("user_feedback")}:
            op.create_index(f"ix_user_feedback_{name}", "user_feedback", [name])

    if not inspect(bind).has_table("pantry_items"):
        op.create_table(
        "pantry_items",
        sa.Column("pantry_item_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.ingredient_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "ingredient_id", "expires_at", name="uq_pantry_owner_ingredient_expiry"),
        )
    for name in ("user_id", "ingredient_id"):
        if f"ix_pantry_items_{name}" not in {index["name"] for index in inspect(bind).get_indexes("pantry_items")}:
            op.create_index(f"ix_pantry_items_{name}", "pantry_items", [name])


def downgrade() -> None:
    op.drop_table("pantry_items")
    op.drop_table("user_feedback")
    op.drop_table("plan_execution_events")
    op.drop_index("ix_meal_plans_profile_archived", table_name="meal_plans")
    op.drop_index("ix_meal_plans_profile_created", table_name="meal_plans")
    if op.get_bind().dialect.name != "sqlite":
        foreign_keys = {tuple(key["constrained_columns"]): key.get("name") for key in inspect(op.get_bind()).get_foreign_keys("meal_plans")}
        name = foreign_keys.get(("source_plan_id",))
        if name:
            op.drop_constraint(name, "meal_plans", type_="foreignkey")
    op.drop_column("meal_plans", "archived_at")
    op.drop_column("meal_plans", "source_plan_id")
    op.drop_column("meal_plans", "title")
