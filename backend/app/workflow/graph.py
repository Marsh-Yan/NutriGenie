"""LangGraph AI Workflow 装配

将各节点按顺序连接成完整 Graph：

    User Input
        ↓
    IntentAnalyzer  (LLM / 规则降级)
        ↓
    ConstraintNode  (纯代码)
        ↓
    RecommendationNode  (纯代码: 召回→排除→评分→排序)
        ↓
    AggregateNode  (纯代码: TOP5 + 周计划 + 营养报告 + 采购清单)
        ↓
    SummaryGenerator  (LLM / 模板降级)
        ↓
    FinalResult
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.workflow.nodes.intent_analyzer import analyze_intent
from app.workflow.nodes.summary_generator import generate_summary
from app.workflow.nodes.phase3_nodes import (
    constraint_node,
    recommendation_node,
    aggregate_node,
    validation_node,
)
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

# ─── 节点路由函数 ─────────────────────────────────


def route_after_intent(state: WorkflowState) -> Literal["constraint", "error_end"]:
    """意图分析后路由：成功→约束分析，失败→错误结束"""
    if state.intent_error and not state.intent_analysis:
        return "error_end"
    return "constraint"


def route_after_constraint(state: WorkflowState) -> Literal["recommendation", "error_end"]:
    """约束分析后路由"""
    if state.constraint_error and not state.constraints:
        return "error_end"
    return "recommendation"


def route_after_recommendation(state: WorkflowState) -> Literal["aggregator", "error_end"]:
    """推荐引擎后路由"""
    if state.recommendation_error and not state.ranked_recipes:
        return "error_end"
    return "aggregator"


def route_after_aggregation(state: WorkflowState) -> Literal["validation", "error_end"]:
    """聚合后路由"""
    if state.aggregation_error and not state.aggregated_result:
        return "error_end"
    return "validation"


def route_after_summary(state: WorkflowState) -> Literal["final", "final"]:
    """总结后→最终输出"""
    return "final"


def build_workflow() -> StateGraph:
    """构建完整的 LangGraph Workflow"""

    workflow = StateGraph(WorkflowState)

    # ── 注册节点 ──
    workflow.add_node("intent_analyzer", analyze_intent)
    workflow.add_node("constraint", constraint_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("aggregator", aggregate_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("summary", generate_summary)
    workflow.add_node("error_end", _error_end)

    # ── 注册边 ──
    workflow.set_entry_point("intent_analyzer")

    workflow.add_conditional_edges(
        "intent_analyzer",
        route_after_intent,
        {"constraint": "constraint", "error_end": "error_end"},
    )

    workflow.add_conditional_edges(
        "constraint",
        route_after_constraint,
        {"recommendation": "recommendation", "error_end": "error_end"},
    )

    workflow.add_conditional_edges(
        "recommendation",
        route_after_recommendation,
        {"aggregator": "aggregator", "error_end": "error_end"},
    )

    workflow.add_conditional_edges(
        "aggregator",
        route_after_aggregation,
        {"validation": "validation", "error_end": "error_end"},
    )

    workflow.add_edge("validation", "summary")

    workflow.add_edge("summary", "finalize")

    workflow.add_node("finalize", _finalize)
    workflow.add_edge("finalize", END)

    workflow.add_edge("error_end", END)

    return workflow


async def _error_end(state: WorkflowState) -> WorkflowState:
    """错误结束节点：记录错误信息"""
    state.current_node = "error"
    state.final_result = {
        "status": "failed",
        "error": state.errors[-1] if state.errors else "未知错误",
        "errors": state.errors,
    }
    logger.error(f"Workflow failed: {state.errors}")
    return state


async def _finalize(state: WorkflowState) -> WorkflowState:
    """最终节点：组装结果"""
    state.current_node = "completed"

    result = {
        "status": "completed",
        "user_input": state.user_input,
        "intent_explanation": state.intent_explanation,
        "summary": state.summary,
    }

    if state.aggregated_result:
        result["top5"] = state.aggregated_result.get("top5", [])
        result["weekly_plan"] = state.aggregated_result.get("weekly_plan", [])
        result["nutrition_report"] = state.aggregated_result.get("nutrition_report", {})
        result["shopping_list"] = state.aggregated_result.get("shopping_list", {})
        result["plan_validation"] = state.aggregated_result.get("plan_validation", {})
        result["summary_text"] = state.summary or state.aggregated_result.get("summary", "")

    if state.ranked_recipes:
        result["ranked_recipes"] = state.ranked_recipes[:5]

    state.final_result = result
    return state


# ─── 编译图 ───────────────────────────────────────

graph = build_workflow()
compiled_graph = graph.compile()
