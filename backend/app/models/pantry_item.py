"""Owned ingredient quantities in the ingredient's canonical catalog unit."""

from sqlalchemy import Column, Date, DateTime, DECIMAL, ForeignKey, Integer, String, UniqueConstraint, func

from app.db.database import Base


class PantryItem(Base):
    __tablename__ = "pantry_items"
    __table_args__ = (UniqueConstraint("user_id", "ingredient_id", "expires_at", name="uq_pantry_owner_ingredient_expiry"),)

    pantry_item_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.ingredient_id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    expires_at = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
