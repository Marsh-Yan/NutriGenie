"""输出代表性查询的 RAG Top 5，用于人工验收语义召回。"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.recipe_retriever import retrieve_recipes


CASES = [
    {
        "title": "暖胃但不油腻",
        "intent": {
            "goal": "fat_loss",
            "semantic_preferences": {
                "flavor": ["暖胃", "清淡"],
                "scenarios": ["工作日晚餐"],
                "free_text": "想吃热乎的，不想太油腻",
            },
        },
    },
    {
        "title": "下班20分钟快手菜",
        "intent": {
            "goal": "healthy",
            "semantic_preferences": {
                "flavor": [],
                "scenarios": ["下班后", "快手"],
                "free_text": "20分钟内完成",
            },
        },
    },
    {
        "title": "不想吃水煮菜的减脂餐",
        "intent": {
            "goal": "fat_loss",
            "semantic_preferences": {
                "flavor": ["有满足感"],
                "scenarios": [],
                "free_text": "不想吃水煮菜，希望味道丰富一些",
            },
        },
    },
]


def main() -> None:
    for case in CASES:
        print(f"\n## {case['title']}")
        results = retrieve_recipes(case["intent"], constraints={}, limit=5)
        for index, item in enumerate(results, start=1):
            print(f"{index}. recipe_id={item.recipe_id}, similarity={item.similarity_score:.3f}")


if __name__ == "__main__":
    main()
