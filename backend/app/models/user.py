"""Application user and role model."""

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nickname = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("user", "admin"), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
