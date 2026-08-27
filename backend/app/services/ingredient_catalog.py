"""Trusted ingredient facts and deterministic normalization for AI recipes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.services.ai_plan_models import GeneratedPlan, NutritionEstimate
from app.services.nutrition_service import CATEGORY_WEIGHT_ADJUST, UNIT_TO_GRAM


CATALOG_SOURCE = "ingredient_catalog_v1"

# The first release keeps aliases in code so it can ship without another
# migration. Values must always point to a canonical Ingredient.name.
INGREDIENT_ALIASES = {
    "西红柿": "番茄",
    "圣女果": "番茄",
    "马铃薯": "土豆",
    "青花菜": "西兰花",
    "花椰菜": "西兰花",
    "牛油果果肉": "牛油果",
    "鲜牛奶": "牛奶",
    "原味酸奶": "酸奶",
    "希腊酸奶": "酸奶",
    "全麦吐司": "全麦面包",
    "吐司": "全麦面包",
    "通心粉": "意面",
    "香菇": "蘑菇",
    "白蘑菇": "蘑菇",
    "去皮鸡胸肉": "鸡胸肉",
    "鸡胸": "鸡胸肉",
    "里脊肉": "猪里脊肉",
    "猪里脊": "猪里脊肉",
    "鲜虾仁": "虾仁",
    "鳄梨": "牛油果",
    "清水": "水",
    "饮用水": "水",
    "矿泉水": "水",
    "凉白开": "水",
    "燕麦片": "燕麦",
    "即食燕麦": "燕麦",
    "藜麦米": "藜麦",
    "地瓜": "红薯",
    "甜薯": "红薯",
    "包菜": "卷心菜",
    "圆白菜": "卷心菜",
    "花菜": "菜花",
    "黑木耳": "木耳",
    "海带丝": "海带",
    "绿豆芽": "豆芽",
    "青豆": "豌豆",
    "甜椒": "彩椒",
    "灯笼椒": "彩椒",
    "去骨鸡腿肉": "鸡腿肉",
    "瘦猪肉": "猪瘦肉",
    "鳕鱼柳": "鳕鱼",
    "无糖豆浆": "豆浆",
    "熟鹰嘴豆": "鹰嘴豆",
    "花生米": "花生",
    "小麦粉": "面粉",
    "淀粉": "玉米淀粉",
    "生抽": "酱油",
    "胡椒粉": "黑胡椒",
    "食用油": "菜籽油",
    "植物油": "菜籽油",
}

_EXTRA_UNIT_TO_GRAM = {
    "头": 50.0,
    "条": 200.0,
    "只": 50.0,
    "杯": 200.0,
    "碗": 200.0,
    "罐": 200.0,
    "袋": 250.0,
    "瓶": 500.0,
}


class CatalogIngredient(BaseModel):
    ingredient_id: int
    name: str
    category: str
    unit: str
    unit_price: float = 0
    calories_per_100g: float = 0
    protein_per_100g: float = 0
    fat_per_100g: float = 0
    carbs_per_100g: float = 0
    fiber_per_100g: float = 0


class IngredientCatalog(BaseModel):
    version: str
    entries: list[CatalogIngredient]

    def prompt_entries(self) -> list[dict]:
        return [
            {
                "name": item.name,
                "category": item.category,
                "preferred_unit": item.unit,
            }
            for item in self.entries
        ]


class NormalizationIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"]
    recipe_index: int
    ingredient_index: int
    ingredient_name: str


class PlanNormalizationResult(BaseModel):
    plan: GeneratedPlan
    catalog_version: str
    issues: list[NormalizationIssue] = Field(default_factory=list)
    resolved_count: int = 0
    total_count: int = 0
    price_covered_count: int = 0

    @property
    def unresolved_ingredients(self) -> list[str]:
        return sorted({item.ingredient_name for item in self.issues if item.severity == "error"})


def _normalized_name(value: str) -> str:
    return "".join(str(value or "").strip().lower().split())


def _catalog_version(entries: Iterable[CatalogIngredient]) -> str:
    payload = [item.model_dump(mode="json") for item in sorted(entries, key=lambda value: value.ingredient_id)]
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"catalog-{digest[:12]}"


def build_catalog(entries: Iterable[CatalogIngredient | dict]) -> IngredientCatalog:
    parsed = [item if isinstance(item, CatalogIngredient) else CatalogIngredient.model_validate(item) for item in entries]
    return IngredientCatalog(version=_catalog_version(parsed), entries=parsed)


def load_seed_catalog() -> IngredientCatalog:
    seed_dir = Path(__file__).resolve().parents[1] / "db" / "seed_data"
    ingredients = json.loads((seed_dir / "ingredients.json").read_text(encoding="utf-8"))
    nutrition = json.loads((seed_dir / "ingredient_nutrition.json").read_text(encoding="utf-8"))
    nutrition_by_id = {int(item["ingredient_id"]): item for item in nutrition}
    entries = []
    for item in ingredients:
        fact = nutrition_by_id.get(int(item["ingredient_id"]), {})
        entries.append(
            CatalogIngredient(
                ingredient_id=int(item["ingredient_id"]),
                name=item["name"],
                category=item.get("category", "other"),
                unit=item.get("unit", "g"),
                unit_price=float(item.get("unit_price") or 0),
                calories_per_100g=float(fact.get("calories_per_100g") or 0),
                protein_per_100g=float(fact.get("protein_per_100g") or 0),
                fat_per_100g=float(fact.get("fat_per_100g") or 0),
                carbs_per_100g=float(fact.get("carbs_per_100g") or 0),
                fiber_per_100g=float(fact.get("fiber_per_100g") or 0),
            )
        )
    return build_catalog(entries)


def load_ingredient_catalog(db: Session, *, fallback_to_seed: bool = True) -> IngredientCatalog:
    rows = (
        db.query(Ingredient, IngredientNutrition)
        .outerjoin(IngredientNutrition, IngredientNutrition.ingredient_id == Ingredient.ingredient_id)
        .order_by(Ingredient.ingredient_id.asc())
        .all()
    )
    if not rows:
        if fallback_to_seed:
            return load_seed_catalog()
        return build_catalog([])

    entries = []
    for ingredient, nutrition in rows:
        entries.append(
            CatalogIngredient(
                ingredient_id=ingredient.ingredient_id,
                name=ingredient.name,
                category=ingredient.category or "other",
                unit=ingredient.unit or "g",
                unit_price=float(ingredient.unit_price or 0),
                calories_per_100g=float(nutrition.calories_per_100g or 0) if nutrition else 0,
                protein_per_100g=float(nutrition.protein_per_100g or 0) if nutrition else 0,
                fat_per_100g=float(nutrition.fat_per_100g or 0) if nutrition else 0,
                carbs_per_100g=float(nutrition.carbs_per_100g or 0) if nutrition else 0,
                fiber_per_100g=float(nutrition.fiber_per_100g or 0) if nutrition else 0,
            )
        )
    return build_catalog(entries)


def catalog_from_state(value: IngredientCatalog | dict | list[dict] | None) -> IngredientCatalog:
    if isinstance(value, IngredientCatalog):
        return value
    if isinstance(value, dict) and "entries" in value:
        return IngredientCatalog.model_validate(value)
    if isinstance(value, list):
        return build_catalog(value)
    return load_seed_catalog()


def strict_grams(quantity: float, unit: str, category: str) -> float:
    normalized_unit = str(unit or "").strip()
    category_map = CATEGORY_WEIGHT_ADJUST.get(category, {})
    if normalized_unit in category_map:
        return float(quantity) * float(category_map[normalized_unit])
    if normalized_unit in UNIT_TO_GRAM:
        return float(quantity) * float(UNIT_TO_GRAM[normalized_unit])
    if normalized_unit in _EXTRA_UNIT_TO_GRAM:
        return float(quantity) * float(_EXTRA_UNIT_TO_GRAM[normalized_unit])
    raise ValueError(f"无法换算单位：{normalized_unit or '空'}")


def _resolve_entry(name: str, catalog: IngredientCatalog) -> tuple[CatalogIngredient | None, str | None]:
    by_name = {_normalized_name(item.name): item for item in catalog.entries}
    normalized = _normalized_name(name)
    if normalized in by_name:
        return by_name[normalized], "exact"
    alias_target = INGREDIENT_ALIASES.get(normalized)
    if alias_target and _normalized_name(alias_target) in by_name:
        return by_name[_normalized_name(alias_target)], "alias"
    # Safe normalization only removes common preparation adjectives. It does
    # not use fuzzy matching because a wrong food match is a safety issue.
    stripped = normalized
    for token in ("新鲜", "冷冻", "去皮", "切片", "切块", "熟"):
        stripped = stripped.replace(token, "")
    if stripped in by_name:
        return by_name[stripped], "normalized"
    return None, None


def _nutrition_for(entry: CatalogIngredient, grams: float) -> NutritionEstimate:
    factor = grams / 100.0
    return NutritionEstimate(
        calories=round(entry.calories_per_100g * factor, 2),
        protein_g=round(entry.protein_per_100g * factor, 2),
        fat_g=round(entry.fat_per_100g * factor, 2),
        carbs_g=round(entry.carbs_per_100g * factor, 2),
        fiber_g=round(entry.fiber_per_100g * factor, 2),
    )


def _cost_for(entry: CatalogIngredient, quantity: float, unit: str, grams: float) -> float:
    if entry.unit_price <= 0:
        return 0.0
    if str(unit).strip() == str(entry.unit).strip():
        return round(entry.unit_price * float(quantity), 2)
    base_grams = strict_grams(1, entry.unit, entry.category)
    return round(entry.unit_price * grams / base_grams, 2)


def normalize_generated_plan(plan: GeneratedPlan, catalog: IngredientCatalog) -> PlanNormalizationResult:
    normalized_plan = plan.model_copy(deep=True)
    issues: list[NormalizationIssue] = []
    resolved_count = 0
    total_count = 0
    price_covered_count = 0

    for recipe_index, recipe in enumerate(normalized_plan.recipes):
        recipe.declared_nutrition_estimate = recipe.nutrition_estimate
        recipe.declared_cost_estimate = recipe.cost_estimate
        nutrition_total = NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)
        recipe_cost = 0.0

        for ingredient_index, item in enumerate(recipe.ingredients):
            total_count += 1
            item.input_name = item.input_name or item.name
            item.declared_nutrition_estimate = item.nutrition_estimate
            item.declared_line_cost_estimate = item.line_cost_estimate
            entry, resolution_source = _resolve_entry(item.name, catalog)
            if not entry:
                issues.append(
                    NormalizationIssue(
                        code="ingredient_unresolved",
                        message=f"食材「{item.name}」不在标准食材目录中。",
                        severity="error",
                        recipe_index=recipe_index,
                        ingredient_index=ingredient_index,
                        ingredient_name=item.name,
                    )
                )
                continue
            try:
                grams = strict_grams(item.quantity, item.unit, entry.category)
                cost = _cost_for(entry, item.quantity, item.unit, grams)
            except ValueError as exc:
                issues.append(
                    NormalizationIssue(
                        code="unit_unresolved",
                        message=f"食材「{item.name}」{exc}",
                        severity="error",
                        recipe_index=recipe_index,
                        ingredient_index=ingredient_index,
                        ingredient_name=item.name,
                    )
                )
                continue

            nutrition = _nutrition_for(entry, grams)
            item.name = entry.name
            item.ingredient_id = entry.ingredient_id
            item.catalog_name = entry.name
            item.estimated_grams = round(grams, 2)
            item.nutrition_estimate = nutrition
            item.line_cost_estimate = cost
            item.resolution_source = resolution_source
            item.data_source = CATALOG_SOURCE
            resolved_count += 1
            if entry.unit_price > 0:
                price_covered_count += 1
            else:
                issues.append(
                    NormalizationIssue(
                        code="price_missing",
                        message=f"食材「{entry.name}」暂无价格基准，成本按 0 元计算。",
                        severity="warning",
                        recipe_index=recipe_index,
                        ingredient_index=ingredient_index,
                        ingredient_name=entry.name,
                    )
                )

            nutrition_total = NutritionEstimate(
                calories=nutrition_total.calories + nutrition.calories,
                protein_g=nutrition_total.protein_g + nutrition.protein_g,
                fat_g=nutrition_total.fat_g + nutrition.fat_g,
                carbs_g=nutrition_total.carbs_g + nutrition.carbs_g,
                fiber_g=nutrition_total.fiber_g + nutrition.fiber_g,
            )
            recipe_cost += cost

        recipe.nutrition_estimate = nutrition_total
        recipe.cost_estimate = round(recipe_cost, 2)

    return PlanNormalizationResult(
        plan=normalized_plan,
        catalog_version=catalog.version,
        issues=issues,
        resolved_count=resolved_count,
        total_count=total_count,
        price_covered_count=price_covered_count,
    )
