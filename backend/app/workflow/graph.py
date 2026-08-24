"""LangGraph workflow for AI-native meal plan generation.

The legacy graph names are kept where they are part of the current status and
test contract, but the recommendation node now means LLM plan generation and
the summary node is a deterministic pass-through.
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.workflow.nodes.ai_native_nodes import (
    ai_aggregation_node,
    ai_validation_node,
    generation_context_node,
    plan_generation_node,
    plan_repair_node,
    route_after_ai_validation,
    summary_passthrough_node,
)
from app.workflow.nodes.phase3_nodes import constraint_node
from app.workflow.nodes.intent_analyzer import analyze_intent
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def route_after_intent(state: WorkflowState) -> Literal["constraint", "error_end"]:
    if state.skip_intent:
        return "constraint"
    if state.intent_error and not state.intent_analysis:
        return "error_end"
    return "constraint"


def route_after_constraint(state: WorkflowState) -> Literal["recommendation", "error_end"]:
    if state.constraint_error and not state.constraints:
        return "error_end"
    return "recommendation"


def route_after_recommendation(state: WorkflowState) -> Literal["aggregator", "error_end"]:
    """Legacy routing helper retained for existing callers and tests."""
    if state.recommendation_error and not state.ranked_recipes:
        return "error_end"
    return "aggregator"


def route_after_generation(state: WorkflowState) -> Literal["validation", "error_end"]:
    if state.generation_error and not state.generated_plan:
        return "error_end"
    if not state.generated_plan:
        return "error_end"
    return "validation"


def route_after_aggregation(state: WorkflowState) -> Literal["validation", "error_end"]:
    """Legacy routing helper retained for existing callers and tests."""
    if state.aggregation_error and not state.aggregated_result:
        return "error_end"
    return "validation"


def route_after_ai_aggregation(state: WorkflowState) -> Literal["summary", "error_end"]:
    if state.aggregation_error and not state.aggregated_result:
        return "error_end"
    return "summary"


def build_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("intent_analyzer", analyze_intent)
    workflow.add_node("constraint", constraint_node)
    workflow.add_node("generation_context", generation_context_node)
    # Keep the public node name used by progress APIs while changing its role.
    workflow.add_node("recommendation", plan_generation_node)
    workflow.add_node("validation", ai_validation_node)
    workflow.add_node("repair", plan_repair_node)
    workflow.add_node("aggregator", ai_aggregation_node)
    workflow.add_node("summary", summary_passthrough_node)
    workflow.add_node("error_end", _error_end)
    workflow.add_node("finalize", _finalize)

    workflow.set_entry_point("intent_analyzer")
    workflow.add_conditional_edges(
        "intent_analyzer",
        route_after_intent,
        {"constraint": "constraint", "error_end": "error_end"},
    )
    workflow.add_conditional_edges(
        "constraint",
        route_after_constraint,
        {"recommendation": "generation_context", "error_end": "error_end"},
    )
    workflow.add_edge("generation_context", "recommendation")
    workflow.add_conditional_edges(
        "recommendation",
        route_after_generation,
        {"validation": "validation", "error_end": "error_end"},
    )
    workflow.add_conditional_edges(
        "validation",
        route_after_ai_validation,
        {"repair": "repair", "aggregator": "aggregator", "error_end": "error_end"},
    )
    workflow.add_edge("repair", "validation")
    workflow.add_conditional_edges(
        "aggregator",
        route_after_ai_aggregation,
        {"summary": "summary", "error_end": "error_end"},
    )
    workflow.add_edge("summary", "finalize")
    workflow.add_edge("finalize", END)
    workflow.add_edge("error_end", END)
    return workflow


async def _error_end(state: WorkflowState) -> WorkflowState:
    state.current_node = "error"
    state.final_result = {
        "status": "failed",
        "error": state.errors[-1] if state.errors else "未知错误",
        "errors": state.errors,
    }
    logger.error("Workflow failed: %s", state.errors)
    return state


async def _finalize(state: WorkflowState) -> WorkflowState:
    state.current_node = "completed"
    result = {
        "status": "completed",
        "user_input": state.user_input,
        "intent_explanation": state.intent_explanation,
        "summary": state.summary,
    }
    if state.aggregated_result:
        result.update(state.aggregated_result)
        result["summary"] = state.summary or state.aggregated_result.get("summary", "")
    state.final_result = result
    return state


graph = build_workflow()
compiled_graph = graph.compile()
