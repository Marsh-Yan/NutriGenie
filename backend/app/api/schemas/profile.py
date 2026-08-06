"""用户画像 Pydantic Schemas"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    """创建用户画像请求"""
    age: int = Field(..., ge=1, le=150)
    gender: str = Field(..., pattern="^(male|female)$")
    height: float = Field(..., ge=50, le=250)
    weight: float = Field(..., ge=10, le=300)
    diet_type: str = Field(
        default="balanced",
        pattern="^(balanced|keto|high_protein|gluten_free|vegan|healthy)$",
    )
    health_goal: str = Field(
        default="healthy",
        pattern="^(fat_loss|muscle_gain|blood_sugar|healthy)$",
    )
    allergies: Optional[List[str]] = None
    daily_budget: float = Field(default=0, ge=0)


class ProfileUpdate(BaseModel):
    """更新用户画像请求（所有字段可选）"""
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    height: Optional[float] = Field(None, ge=50, le=250)
    weight: Optional[float] = Field(None, ge=10, le=300)
    diet_type: Optional[str] = Field(
        None, pattern="^(balanced|keto|high_protein|gluten_free|vegan|healthy)$"
    )
    health_goal: Optional[str] = Field(
        None, pattern="^(fat_loss|muscle_gain|blood_sugar|healthy)$"
    )
    allergies: Optional[List[str]] = None
    daily_budget: Optional[float] = Field(None, ge=0)


class ProfileResponse(BaseModel):
    """用户画像响应"""
    profile_id: int
    age: int
    gender: str
    height: float
    weight: float
    diet_type: str
    health_goal: str
    allergies: Optional[List[str]] = None
    daily_budget: float
    tdee: Optional[float] = None
    bmi: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
