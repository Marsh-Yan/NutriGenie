"""约束分析服务

根据用户画像和用户输入，生成用于推荐引擎的约束集。

约束集包括：
  - 热量目标（基于 TDEE + 健康目标）
  - 每日预算（总预算 / 天数）
  - 排除的过敏原列表
  - 饮食类型约束
  - 活动系数
"""

from typing import List, Optional, Dict

from app.models.profile import Profile
from app.services.tdee import calculate_tdee, calculate_bmr

# ─── 健康目标 → 热量调整系数 ─────────────────────

HEALTH_GOAL_ADJUSTMENT: Dict[str, float] = {
    "fat_loss": 0.80,       # 减脂：TDEE × 0.8（20% 热量缺口）
    "muscle_gain": 1.10,    # 增肌：TDEE × 1.1（10% 热量盈余）
    "blood_sugar": 0.90,    # 控糖：TDEE × 0.9（温和缺口）
    "healthy": 1.0,         # 健康饮食：维持 TDEE
}

# ─── 健康目标 → 蛋白质系数（g / kg 体重） ─────────

PROTEIN_FACTOR: Dict[str, float] = {
    "fat_loss": 2.0,        # 减脂：高蛋白保留肌肉
    "muscle_gain": 2.0,     # 增肌：高蛋白支持肌肉合成
    "blood_sugar": 1.5,     # 控糖：中等蛋白
    "healthy": 1.2,         # 健康饮食：维持
}

# ─── 活动系数默认值 ───────────────────────────────

ACTIVITY_FACTOR_DESCRIPTIONS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "extra": 1.9,
}

# ─── 饮食类型 → 宏量营养素配比 ───────────────────
# (蛋白质%, 脂肪%, 碳水%)

DIET_MACRO_SPLIT: Dict[str, tuple] = {
    "balanced": (0.20, 0.30, 0.50),       # 均衡：2:3:5
    "keto": (0.25, 0.60, 0.15),           # 生酮：高脂肪
    "high_protein": (0.35, 0.25, 0.40),   # 高蛋白
    "gluten_free": (0.20, 0.30, 0.50),    # 无麸质（同均衡）
    "vegan": (0.15, 0.25, 0.60),          # 素食：较高碳水
    "healthy": (0.25, 0.25, 0.50),        # 健康饮食
}


class ConstraintSet:
    """约束集 — 推荐引擎据此进行筛选和评分"""

    def __init__(
        self,
        # 热量
        target_calories: float,
        calorie_min: float,
        calorie_max: float,
        # 蛋白质
        target_protein: float,
        # 预算
        daily_budget: float,
        total_budget: float,
        # 排除项
        excluded_ingredient_ids: List[int],
        allergen_names: List[str],
        # 饮食类型
        diet_type: str,
        health_goal: str,
        # 宏量营养素配比
        macro_split: tuple,
        # TDEE 原始值
        tdee: float,
        bmr: float,
    ):
        self.target_calories = target_calories
        self.calorie_min = calorie_min
        self.calorie_max = calorie_max
        self.target_protein = target_protein
        self.daily_budget = daily_budget
        self.total_budget = total_budget
        self.excluded_ingredient_ids = excluded_ingredient_ids
        self.allergen_names = allergen_names
        self.diet_type = diet_type
        self.health_goal = health_goal
        self.macro_split = macro_split
        self.tdee = tdee
        self.bmr = bmr

    def to_dict(self) -> dict:
        return {
            "target_calories": self.target_calories,
            "calorie_min": self.calorie_min,
            "calorie_max": self.calorie_max,
            "target_protein": self.target_protein,
            "daily_budget": self.daily_budget,
            "total_budget": self.total_budget,
            "excluded_ingredient_ids": self.excluded_ingredient_ids,
            "allergen_names": self.allergen_names,
            "diet_type": self.diet_type,
            "health_goal": self.health_goal,
            "macro_split": {
                "protein_pct": self.macro_split[0],
                "fat_pct": self.macro_split[1],
                "carbs_pct": self.macro_split[2],
            },
            "tdee": self.tdee,
            "bmr": self.bmr,
        }

    def __repr__(self) -> str:
        return (
            f"ConstraintSet(target_calories={self.target_calories:.0f}, "
            f"daily_budget=¥{self.daily_budget:.1f}, "
            f"diet={self.diet_type}, "
            f"goal={self.health_goal}, "
            f"excluded_allergens={self.allergen_names})"
        )


def build_constraints(
    profile: Profile,
    duration_days: int,
    total_budget: float,
    activity_factor: float = 1.55,
    custom_weight_kg: Optional[float] = None,
) -> ConstraintSet:
    """根据用户画像构建约束集

    Args:
        profile: 用户画像对象
        duration_days: 规划天数
        total_budget: 总预算
        activity_factor: 活动系数（默认 1.55 中度活动）
        custom_weight_kg: 可选的自定义体重（热计算用）

    Returns:
        ConstraintSet 实例
    """
    weight = custom_weight_kg if custom_weight_kg else float(profile.weight)
    height = float(profile.height)

    # 1. 计算 TDEE 和 BMR
    tdee = calculate_tdee(
        gender=profile.gender,
        weight_kg=weight,
        height_cm=height,
        age=profile.age,
        activity_factor=activity_factor,
    )
    bmr = calculate_bmr(
        gender=profile.gender,
        weight_kg=weight,
        height_cm=height,
        age=profile.age,
    )

    # 2. 计算热量目标
    adjustment = HEALTH_GOAL_ADJUSTMENT.get(profile.health_goal, 1.0)
    target_calories = round(tdee * adjustment, 0)

    # 热量范围：目标 ± 150kcal
    calorie_min = max(target_calories - 150, 1000)
    calorie_max = target_calories + 150

    # 3. 计算蛋白质目标
    protein_factor = PROTEIN_FACTOR.get(profile.health_goal, 1.2)
    target_protein = round(weight * protein_factor, 1)

    # 4. 预算分解
    daily_budget = round(total_budget / duration_days, 2) if duration_days > 0 else total_budget

    # 5. 过敏原 → 排除的食材 ID（后续由推荐引擎查询数据库填充）
    allergen_names = profile.allergies or []
    excluded_ingredient_ids = []  # 将在推荐引擎中基于名称解析

    # 6. 饮食类型宏量营养素配比
    macro_split = DIET_MACRO_SPLIT.get(profile.diet_type, (0.20, 0.30, 0.50))

    return ConstraintSet(
        target_calories=target_calories,
        calorie_min=calorie_min,
        calorie_max=calorie_max,
        target_protein=target_protein,
        daily_budget=daily_budget,
        total_budget=total_budget,
        excluded_ingredient_ids=excluded_ingredient_ids,
        allergen_names=allergen_names,
        diet_type=profile.diet_type,
        health_goal=profile.health_goal,
        macro_split=macro_split,
        tdee=round(tdee, 1),
        bmr=round(bmr, 1),
    )
