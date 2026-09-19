"""Additive V2.1 request and response contracts."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanMetadataUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    archived: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or (self.title is None and self.archived is None):
            raise ValueError("至少提供一项修改")
        if "title" in self.model_fields_set and (self.title is None or not self.title.strip()):
            raise ValueError("标题不能为空")
        return self


class PlanCloneOverrides(StrictModel):
    total_budget: float | None = Field(default=None, ge=0)


class PlanCloneRequest(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    overrides: PlanCloneOverrides = Field(default_factory=PlanCloneOverrides)

    @model_validator(mode="after")
    def nonblank_title(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("标题不能为空")
        return self


class ExecutionEventInput(StrictModel):
    day: int = Field(ge=1, le=7)
    meal_slot: Literal["breakfast", "lunch", "dinner"]
    status: Literal["planned", "completed", "adjusted", "skipped"]
    note: str | None = Field(default=None, max_length=500)


class ExecutionUpdate(StrictModel):
    events: list[ExecutionEventInput] = Field(min_length=1, max_length=21)

    @model_validator(mode="after")
    def unique_slots(self):
        keys = [(event.day, event.meal_slot) for event in self.events]
        if len(keys) != len(set(keys)):
            raise ValueError("同一餐次不能重复提交")
        return self


class FeedbackCreate(StrictModel):
    plan_id: int | None = Field(default=None, gt=0)
    recipe_id: int | None = Field(default=None, gt=0)
    feedback_type: Literal["liked", "disliked", "too_expensive", "too_difficult", "too_slow", "other"]
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=1000)


class PantryItemCreate(StrictModel):
    ingredient_id: int = Field(gt=0)
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=20)
    expires_at: date | None = None


class PantryItemUpdate(StrictModel):
    quantity: float | None = Field(default=None, gt=0, le=100000)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    expires_at: date | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一项修改")
        return self


class MealReplaceRequest(StrictModel):
    reason: Literal["disliked", "too_expensive", "too_difficult", "too_slow", "other"] = "other"
    exclude_recipe_ids: list[int] = Field(default_factory=list, max_length=60)
    exclude_recipe_keys: list[str] = Field(default_factory=list, max_length=60)


class PlanSummary(BaseModel):
    plan_id: int
    title: str
    status: str
    duration_days: int
    total_budget: float
    created_at: datetime
    completed_at: datetime | None
    archived_at: datetime | None
    source_plan_id: int | None
