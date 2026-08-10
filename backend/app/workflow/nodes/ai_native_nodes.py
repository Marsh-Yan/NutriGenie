"""LangGraph nodes for AI-native plan generation."""

from __future__ import annotations

import logging

from app.config import settings
from app.services.ai_plan_generator import PlanGenerationError, generate_plan, repair_plan
from app.services.generation_context import retrieve_generation_context
from app.services.plan_aggregator import aggregate_generated_plan
from app.services.plan_validator import validate_plan
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


async def generation_context_node(state: WorkflowState) -> WorkflowState:
    state.current_node = "generation_context"
    if not state.constraints:
        state.generation_error = "缺少约束集，无法准备生成上下文"
        state.errors.append(state.generation_error)
        return state
    result = await retrieve_generation_context(
        user_input=state.user_input,
        intent=state.intent_analysis,
        constraints=state.constraints,
        edit_message=state.edit_message,
    )
    state.generation_context = result.get("text", "")
    state.generation_meta = result.get("meta", {})
    return state


async def plan_generation_node(state: WorkflowState) -> WorkflowState:
    state.current_node = "plan_generation"
    if not state.constraints:
        state.generation_error = "缺少约束集，无法生成餐单"
        state.errors.append(state.generation_error)
        return state
    try:
        state.generated_plan = await generate_plan(
            user_input=state.user_input,
            constraints=state.constraints,
            intent=state.intent_analysis,
            context=state.generation_context,
            base_plan=state.base_plan,
            edit_message=state.edit_message,
            action=state.edit_action,
        )
    except PlanGenerationError as exc:
        state.generation_error = str(exc)
        state.errors.append(state.generation_error)
        logger.warning("AI plan generation failed: %s", exc)
    return state


async def plan_repair_node(state: WorkflowState) -> WorkflowState:
    state.current_node = "plan_repair"
    if not state.generated_plan or not state.validation_result:
        state.generation_error = "缺少待修复方案或校验结果"
        state.errors.append(state.generation_error)
        return state
    state.repair_attempts += 1
    try:
        state.generated_plan = await repair_plan(
            plan=state.generated_plan,
            user_input=state.user_input,
            constraints=state.constraints or {},
            intent=state.intent_analysis,
            context=state.generation_context,
            base_plan=state.base_plan,
            edit_message=state.edit_message,
            action=state.edit_action,
            validation_feedback=state.validation_result,
        )
    except PlanGenerationError as exc:
        state.generation_error = str(exc)
        state.errors.append(state.generation_error)
        logger.warning("AI plan repair failed: %s", exc)
    return state


def ai_validation_node(state: WorkflowState) -> WorkflowState:
    state.current_node = "plan_validation"
    if not state.generated_plan:
        state.generation_error = state.generation_error or "LLM 未生成餐单"
        if state.generation_error not in state.errors:
            state.errors.append(state.generation_error)
        return state
    result = validate_plan(
        state.generated_plan,
        state.constraints or {},
        intent=state.intent_analysis,
        duration_days=state.duration_days,
    )
    state.validation_result = result.model_dump(mode="json")
    state.plan_validation = state.validation_result
    return state


def route_after_ai_validation(state: WorkflowState) -> str:
    if state.generation_error and not state.generated_plan:
        return "error_end"
    validation = state.validation_result or {}
    has_errors = validation.get("status") == "failed"
    if has_errors and state.repair_attempts < settings.PLAN_REPAIR_MAX_ATTEMPTS:
        return "repair"
    if has_errors:
        error_messages = [
            item.get("message", "方案校验失败")
            for item in validation.get("issues", [])
            if item.get("severity") == "error"
        ]
        message = "；".join(error_messages[:3]) or "方案校验失败"
        if message not in state.errors:
            state.errors.append(message)
        state.generation_error = message
        return "error_end"
    return "aggregator"


def ai_aggregation_node(state: WorkflowState) -> WorkflowState:
    state.current_node = "plan_aggregation"
    if not state.generated_plan or not state.validation_result:
        state.aggregation_error = "缺少 AI 生成方案或校验结果"
        state.errors.append(state.aggregation_error)
        return state
    from app.services.ai_plan_models import PlanValidationResult

    validation = PlanValidationResult.model_validate(state.validation_result)
    state.generated_result = aggregate_generated_plan(
        state.generated_plan,
        validation,
        duration_days=state.duration_days,
        intent=state.intent_analysis,
        constraints=state.constraints,
        rag_meta=state.generation_meta,
        repair_attempts=state.repair_attempts,
    )
    state.aggregated_result = state.generated_result
    return state


def summary_passthrough_node(state: WorkflowState) -> WorkflowState:
    """Keep the legacy graph step while avoiding a second LLM summary call."""
    state.current_node = "summary"
    if state.generated_result:
        state.summary = state.generated_result.get("summary", "")
    return state
