"""六维评分函数

每个维度返回 0.0 ~ 1.0 的分数。
1.0 = 完全匹配，0.0 = 完全不匹配。
"""

# ─── 3.4.1 Health Score ──────────────────────────


def health_score(
    recipe_calories: float,
    target_min: float,
    target_max: float,
) -> float:
    """热量匹配度评分

    计算一道菜的每份热量与用户目标热量区间的匹配程度。

    评分规则:
      - 热量在 [target_min, target_max] 内 → 1.0
      - 每偏离区间边界 100kcal，扣 0.15 分（最低 0.0）
      - 低于 min 和高于 max 分别计算

    Args:
        recipe_calories: 菜谱每份热量（kcal）
        target_min: 目标热量下限
        target_max: 目标热量上限

    Returns:
        0.0 ~ 1.0 的分数
    """
    if target_min <= 0 or target_max <= 0 or target_min >= target_max:
        return 0.0

    if recipe_calories <= 0:
        return 0.0

    # 在目标区间内
    if target_min <= recipe_calories <= target_max:
        return 1.0

    # 低于下限
    if recipe_calories < target_min:
        deficit = target_min - recipe_calories
        penalty = (deficit / 100.0) * 0.15
        return max(0.0, 1.0 - penalty)

    # 高于上限
    excess = recipe_calories - target_max
    penalty = (excess / 100.0) * 0.15
    return max(0.0, 1.0 - penalty)


# ─── 3.4.2 Budget Score ──────────────────────────


def budget_score(
    daily_budget: float,
    recipe_cost: float,
    meals_per_day: int = 3,
) -> float:
    """预算匹配度评分

    计算一道菜的价格与每日预算的匹配程度。
    假设每日吃 meals_per_day 餐，每餐理想花费为 budget / meals_per_day。

    评分规则:
      - 成本 ≤ 每餐预算 → 1.0
      - 成本超过每餐预算，每超出 20% 扣 0.2 分（最低 0.0）
      - 成本为 0（免费/未知）→ 1.0
      - 每日预算为 0（未设置）→ 1.0（不约束）

    Args:
        daily_budget: 每日预算（元）
        recipe_cost: 这道菜每份的预估成本（元）
        meals_per_day: 每天几餐，默认 3

    Returns:
        0.0 ~ 1.0 的分数
    """
    # 未设置预算，不约束
    if daily_budget <= 0:
        return 1.0

    # 免费或未知成本
    if recipe_cost <= 0:
        return 1.0

    per_meal_budget = daily_budget / meals_per_day

    # 在预算内
    if recipe_cost <= per_meal_budget:
        return 1.0

    # 超出预算：每超出 20% 扣 0.2 分，超 100% 归零
    overshoot = (recipe_cost - per_meal_budget) / per_meal_budget  # 超出比例
    return max(0.0, 1.0 - overshoot)


# ─── 3.4.3 Preference Score ──────────────────────

# 各饮食类型对应的菜谱标签关键词
DIET_TAG_KEYWORDS: dict = {
    "keto": ["低碳", "生酮", "高脂"],
    "high_protein": ["高蛋白", "高蛋白质"],
    "gluten_free": ["无麸质"],
    "vegan": ["素食", "纯素"],
    "healthy": ["健康", "轻食"],
    "balanced": [],
}

# 各健康目标对应的菜谱标签关键词
GOAL_TAG_KEYWORDS: dict = {
    "fat_loss": ["减脂", "低脂", "低热量", "轻食"],
    "muscle_gain": ["高蛋白", "增肌"],
    "blood_sugar": ["控糖", "低糖", "低GI"],
    "healthy": ["健康", "减脂"],
}


def preference_score(
    diet_type: str,
    health_goal: str,
    recipe_tags: list,
    cuisine_type: str = "",
    ingredient_categories: list = None,
) -> float:
    """饮食偏好匹配度评分

    通过菜谱标签和食材分类评估与用户饮食偏好的匹配程度。

    评分规则:
      1. 基础分 0.50
      2. 标签匹配 diet_type 关键词 → +0.25（最多 +0.25）
      3. 标签匹配 health_goal 关键词 → +0.25（最多 +0.25）
      4. 标签明显冲突（如 keto 食谱含"高碳水"）→ -0.30
      5. vegan 食谱含肉类/水产食材 → -0.50
      6. cuisine_type 无偏好影响

    Args:
        diet_type: 饮食类型 (balanced/keto/high_protein/gluten_free/vegan/healthy)
        health_goal: 健康目标 (fat_loss/muscle_gain/blood_sugar/healthy)
        recipe_tags: 菜谱标签列表
        cuisine_type: 菜系 (chinese/western)，暂不用于评分
        ingredient_categories: 食材分类列表（用于 vegan 检测）

    Returns:
        0.0 ~ 1.0 的分数
    """
    score = 0.50
    tags_lower = [t.lower() for t in (recipe_tags or [])]

    # 标签匹配 diet_type
    diet_kw = DIET_TAG_KEYWORDS.get(diet_type, [])
    for kw in diet_kw:
        if any(kw in tag for tag in tags_lower):
            score += 0.25
            break

    # 标签匹配 health_goal
    goal_kw = GOAL_TAG_KEYWORDS.get(health_goal, [])
    for kw in goal_kw:
        if any(kw in tag for tag in tags_lower):
            score += 0.25
            break

    # 标签冲突检测
    conflict_tags = {
        "keto": ["高碳水", "主食"],
        "vegan": ["肉", "鸡", "鱼", "虾", "海鲜", "蛋", "奶"],
        "high_protein": ["纯素", "素食"],
    }
    conflicts = conflict_tags.get(diet_type, [])
    for conflict in conflicts:
        if any(conflict in tag for tag in tags_lower):
            score -= 0.30
            break

    # vegan 检测食材分类
    if diet_type == "vegan" and ingredient_categories:
        meat_categories = {"meat", "seafood", "egg", "dairy"}
        if meat_categories & set(ingredient_categories):
            score -= 0.50

    return max(0.0, min(1.0, score))


# ─── 3.4.4 Season Score ──────────────────────────

# 季节映射表（中文 → 英文）
SEASON_MAP = {
    "春季": "spring", "夏天": "summer", "秋季": "autumn", "冬天": "winter",
    "春": "spring", "夏": "summer", "秋": "autumn", "冬": "winter",
}

SEASONS_ORDER = ["春季", "夏季", "秋季", "冬季"]


def season_score(
    ingredient_seasons: list,
    current_season: str,
) -> float:
    """时令匹配度评分

    计算一道菜所用食材与当前季节的匹配度。
    使用当季食材越多，得分越高。

    评分规则:
      - 每种食材单独判断：season_tags 包含 current_season → 当季
      - season_tags 为 None（全年供应）→ 视为当季
      - 得分 = 当季食材数 / 总食材数
      - 没有任何食材有季节数据 → 1.0（无法判断，不扣分）

    Args:
        ingredient_seasons: 食材季节标签列表，每项是 [tags] 或 None
            例如 [["春季", "夏季"], None, ["夏季"], ...]
        current_season: 当前季节，中文 "春季"/"夏季"/"秋季"/"冬季"

    Returns:
        0.0 ~ 1.0 的分数
    """
    if not ingredient_seasons:
        return 1.0

    total = len(ingredient_seasons)
    in_season_count = 0
    has_data = False

    for tags in ingredient_seasons:
        if not tags:
            # None 或空列表：全年供应或未知，不扣分也不作为季节数据
            in_season_count += 1
        elif current_season in tags:
            has_data = True
            in_season_count += 1
        else:
            # 有季节数据但不在当季
            has_data = True

    # 没有任何食材有具体的季节数据 → 不扣分
    if not has_data:
        return 1.0

    return round(in_season_count / total, 4)


# ─── 3.4.5 Variety Score ─────────────────────────


def variety_score(
    recipe_id: int,
    recipe_category: str,
    cuisine_type: str,
    already_selected: list,
    meal_slot: str = "",
) -> float:
    """多样性评分

    评估候选菜谱与已选菜谱相比的多样性。
    避免同一道菜、同类别、同菜系连续重复。

    评分规则:
      - 基础分 1.0
      - 同一道菜已在周计划中出现 → 每出现一次 -0.50
      - 同类别菜谱在同一天出现 → -0.30
      - 同类别菜谱在本周已出现 3 次以上 → 每次额外 -0.10
      - 同菜系在本周出现 4 次以上 → 每次额外 -0.05

    Args:
        recipe_id: 候选菜谱 ID
        recipe_category: 菜谱分类 (main_dish/side_dish/soup/staple/light_meal)
        cuisine_type: 菜系 (chinese/western)
        already_selected: 已选菜谱列表，每项是 dict
            例如 [{"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1, "meal_slot": "lunch"}, ...]
        meal_slot: 当前餐点 (breakfast/lunch/dinner)，可选

    Returns:
        0.0 ~ 1.0 的分数
    """
    if not already_selected:
        return 1.0

    score = 1.0

    # 1. 同菜重复惩罚（同一道菜每出现一次 -0.50）
    same_recipe_count = sum(
        1 for r in already_selected if r.get("recipe_id") == recipe_id
    )
    score -= same_recipe_count * 0.50

    # 2. 同类别惩罚（去掉当前这道菜本身，只看其他菜）
    other_same_category = sum(
        1 for r in already_selected
        if r.get("category") == recipe_category and r.get("recipe_id") != recipe_id
    )
    if other_same_category > 0:
        score -= 0.30
        if other_same_category > 1:
            score -= (other_same_category - 1) * 0.10

    # 3. 同菜系在本周总出现次数惩罚（超过 3 次后递减）
    same_cuisine_total = sum(
        1 for r in already_selected if r.get("cuisine_type") == cuisine_type
    )
    if same_cuisine_total >= 4:
        score -= (same_cuisine_total - 3) * 0.05

    return max(0.0, min(1.0, round(score, 4)))


# ─── 3.4.6 Utilization Score ─────────────────────


def utilization_score(
    recipe_ingredient_ids: list,
    owned_ingredient_ids: list,
) -> float:
    """食材利用率评分

    评估候选菜谱对用户已有食材的覆盖程度。
    已有食材覆盖越多，得分越高，意味着用户不需要额外购买太多。

    评分规则:
      - 没有菜谱食材信息 → 1.0（无法评估）
      - 用户没有已有食材 → 1.0（无法评估，不惩罚）
      - 覆盖率 = 菜谱所需食材中被已有食材覆盖的数量 / 菜谱所需食材总数
        例如：菜谱需要 5 种食材，用户有其中 2 种 → 0.40
      - 覆盖率 ≥ 1.0（用户有这道菜的全部食材）→ 1.0

    Args:
        recipe_ingredient_ids: 这道菜需要的食材 ID 列表
        owned_ingredient_ids: 用户已有的食材 ID 列表

    Returns:
        0.0 ~ 1.0 的分数
    """
    if not recipe_ingredient_ids:
        return 1.0

    if not owned_ingredient_ids:
        return 1.0

    owned_set = set(owned_ingredient_ids)
    covered = sum(1 for rid in recipe_ingredient_ids if rid in owned_set)
    coverage = covered / len(recipe_ingredient_ids)
    return min(1.0, round(coverage, 4))