"""Retain provenance and distinguish budget estimates from observed prices."""
from alembic import op
import sqlalchemy as sa

revision = "20261101_0008"
down_revision = "20260923_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingredients", sa.Column("price_reference", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("ingredients", "price_reference")
