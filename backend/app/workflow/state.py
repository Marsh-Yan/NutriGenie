"""LangGraph Workflow State 定义

定义整个 AI Workflow 中流转的 State 数据结构。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowState:
    """AI Workflow 全局状态

    贯穿 IntentAnalyze → ConstraintAnalyze → RecommendationEngine
    → NutritionAnalyze → ShoppingAnalyze → GPT Summary 的完整数据。
    """
    # ─── 输入 ─────────────────────────────────────
    profile_id: int = 0
    user_input: str = ""
    duration_days: int = 7
    total_budget: float = 0.0
    owned_ingredient_ids: List[int] = field(default_factory=list)

    # ─── 意图分析结果 ─────────────────────────────
    intent_analysis: Optional[Dict[str, Any]] = None  # { goal, diet_type, meal_count_per_day, concerns }
    intent_error: Optional[str] = None

    # ─── 约束分析结果 ─────────────────────────────
    constraints: Optional[Dict[str, Any]] = None  # ConstraintSet.to_dict()
    constraint_error: Optional[str] = None

    # ─── 推荐引擎结果 ─────────────────────────────
    ranked_recipes: List[Dict[str, Any]] = field(default_factory=list)  # TOP15
    recommendation_error: Optional[str] = None

    # ─── RAG 检索状态 ─────────────────────────────
    rag_enabled: bool = True
    rag_retrieval_error: Optional[str] = None
    recommendation_meta: Dict[str, Any] = field(default_factory=dict)

    # ─── 聚合结果（TOP5 + 周计划 + 营养报告等）─────
    aggregated_result: Optional[Dict[str, Any]] = None
    aggregation_error: Optional[str] = None
    plan_validation: Optional[Dict[str, Any]] = None

    # ─── LLM 生成结果 ────────────────────────────
    intent_explanation: Optional[str] = None
    summary: Optional[str] = None
    llm_error: Optional[str] = None

    # ─── 最终输出 ─────────────────────────────────
    final_result: Optional[Dict[str, Any]] = None

    # ─── 工作流状态跟踪 ──────────────────────────
    current_node: str = "intent_analyzer"
    errors: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
