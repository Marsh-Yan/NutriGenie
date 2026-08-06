"""为现有种子菜谱生成可人工审阅的 RAG 增强描述初稿。

该脚本只写入风味、场景和烹饪特点；MySQL 中的结构化营养、成本、食材用量
仍是唯一权威来源。已有 Markdown 文件默认不覆盖，方便人工修改后安全重跑。
"""

from __future__ import annotations

import json
from pathlib import Path


CATEGORY_CONTEXT = {
    "main_dish": ("适合午餐或晚餐作为主菜", "可搭配主食和蔬菜组成完整一餐"),
    "side_dish": ("适合搭配主菜或主食", "单独食用时建议补充蛋白质或主食"),
    "soup": ("适合搭配午餐或晚餐", "可作为热食搭配，提高一餐的丰富度"),
    "staple": ("适合早餐或时间紧张的一餐", "建议搭配蛋白质和蔬菜，使营养更完整"),
    "light_meal": ("适合早餐、轻午餐或控制烹饪时间的场景", "可根据饥饿感搭配主食或蛋白质"),
}


def _traits(recipe: dict) -> list[str]:
    tags = set(recipe.get("tags") or [])
    text = recipe.get("description") or ""
    traits: list[str] = [text]
    if "快手菜" in tags or recipe.get("prep_time", 0) + recipe.get("cook_time", 0) <= 20:
        traits.append("整体步骤相对精简，适合工作日快速完成。")
    if "清淡" in tags or "清爽" in text or "低脂" in tags:
        traits.append("风味相对清爽，调味和用油量可按个人习惯进一步控制。")
    if "下饭" in tags:
        traits.append("味道更有存在感，适合搭配米饭、杂粮饭或其他主食。")
    if "高蛋白" in tags:
        traits.append("适合希望提高一餐蛋白质占比的场景。")
    if "素食" in tags or "素食可选" in tags:
        traits.append("可作为素食取向的选择；具体是否严格素食以 MySQL 食材清单为准。")
    return traits


def _render(recipe: dict) -> str:
    duration = recipe.get("prep_time", 0) + recipe.get("cook_time", 0)
    scenario, pairing = CATEGORY_CONTEXT.get(recipe.get("category"), CATEGORY_CONTEXT["main_dish"])
    traits = "\n\n".join(_traits(recipe))
    tags = "、".join(recipe.get("tags") or []) or "家常菜"
    return f"""---
recipe_id: {recipe['recipe_id']}
content_version: 1
---

# {recipe['name']}

## 风味与口感

{traits}

## 适合场景

- {scenario}。
- 全部准备与烹饪时间约 {duration} 分钟。
- {pairing}。

## 烹饪特点

- 难度：{recipe.get('difficulty', 'medium')}；菜系：{recipe.get('cuisine_type', 'chinese')}。
- 可根据个人口味调整油、盐和辛辣程度；营养与成本以系统结构化计算结果为准。

## 检索关键词

{tags}
"""


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    recipes_path = backend_dir / "app" / "db" / "seed_data" / "recipes.json"
    target_dir = backend_dir / "knowledge_base" / "recipes"
    target_dir.mkdir(parents=True, exist_ok=True)
    recipes = json.loads(recipes_path.read_text(encoding="utf-8"))

    created = 0
    skipped = 0
    for recipe in recipes:
        path = target_dir / f"recipe_{recipe['recipe_id']:02d}.md"
        if path.exists():
            skipped += 1
            continue
        path.write_text(_render(recipe), encoding="utf-8")
        created += 1
    print(f"已生成 {created} 篇菜谱增强文档，保留 {skipped} 篇已有文档。")


if __name__ == "__main__":
    main()
