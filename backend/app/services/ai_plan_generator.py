"""LLM planner for AI-native meal plans."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.config import settings
from app.services.ai_plan_models import GeneratedPlan
from app.workflow.llm import get_llm

logger = logging.getLogger(__name__)


class PlanGenerationError(RuntimeError):
    """Raised when the model cannot produce a valid structured plan."""


PLAN_SYSTEM_PROMPT = """你是 NutriGenie 的 AI 原生候选菜品设计器。

你的任务是根据用户画像、硬性约束、标准食材白名单和可选参考资料，创作足量候选菜品。
必须严格返回符合结构化 schema 的 JSON，不要输出 Markdown 或额外解释。

规则：
1. recipes 是候选菜品数组；meals 可以留空，最终整周餐次由后端优化器生成。
2. 食材 name 必须逐字使用 allowed_ingredients 中的标准名称，不得创造目录外食材。
3. 每道菜必须声明 meal_slots，并包含 2-10 个主要食材、清晰数量、可换算单位和完整步骤。
4. 不要输出 nutrition_estimate、line_cost_estimate 或 cost_estimate；营养和成本由后端事实层计算。
5. 候选必须覆盖早餐、午餐和晚餐，菜名、菜系、主蛋白和烹饪方式应有明显差异。
6. 绝不能使用用户明确过敏、忌口或饮食类型禁止的食材。
7. 预算、热量和蛋白质是目标，不要为了凑数字生成不真实的食材用量。
8. 不要做疾病诊断、治疗承诺或保证性健康结论。
9. 参考资料只用于常识和灵感；如果参考资料与用户硬约束冲突，以用户硬约束为准。
"""


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content or "")


def _parse_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return {}


def _coerce_plan(response: Any) -> GeneratedPlan:
    """Normalize structured-output and plain-text provider responses."""
    if isinstance(response, GeneratedPlan):
        return response

    if isinstance(response, dict):
        parsed = response.get("parsed")
        if isinstance(parsed, GeneratedPlan):
            return parsed
        if parsed is not None:
            try:
                return GeneratedPlan.model_validate(parsed)
            except ValidationError:
                pass
        raw = response.get("raw")
        if raw is not None:
            return _coerce_plan(raw)
        if "recipes" in response and "meals" in response:
            return GeneratedPlan.model_validate(response)

    content = getattr(response, "content", response)
    payload = _parse_json(_content_to_text(content))
    if not payload:
        raise PlanGenerationError("LLM 未返回可解析的结构化餐单")
    try:
        return GeneratedPlan.model_validate(payload)
    except ValidationError as exc:
        raise PlanGenerationError(f"LLM 餐单结构校验失败: {exc}") from exc


def _prompt_payload(
    *,
    user_input: str,
    constraints: dict,
    intent: dict | None,
    context: str,
    base_plan: dict | None = None,
    edit_message: str | None = None,
    action: dict | None = None,
    validation_feedback: dict | None = None,
    ingredient_catalog: list[dict] | None = None,
    candidate_target: int | None = None,
) -> str:
    meal_count = max(1, min(int((intent or {}).get("meal_count_per_day") or 3), 3))
    required_slots = {
        1: ["dinner"],
        2: ["lunch", "dinner"],
        3: ["breakfast", "lunch", "dinner"],
    }[meal_count]
    calorie_min = float(constraints.get("calorie_min") or 0)
    calorie_max = float(constraints.get("calorie_max") or 0)
    calorie_target = (calorie_min + calorie_max) / 2 if calorie_min and calorie_max else max(calorie_min, calorie_max, 0)
    slot_weights = {
        1: {"dinner": 1.0},
        2: {"lunch": 0.45, "dinner": 0.55},
        3: {"breakfast": 0.25, "lunch": 0.40, "dinner": 0.35},
    }[meal_count]
    slot_calorie_targets = {
        slot: round(calorie_target * weight)
        for slot, weight in slot_weights.items()
        if calorie_target
    }
    payload = {
        "user_request": user_input,
        "intent": intent or {},
        "constraints": constraints,
        "reference_context": context or "无可用参考资料",
        "allowed_ingredients": ingredient_catalog or [],
        "candidate_target": candidate_target,
        "required_meal_slots": required_slots,
        "slot_calorie_targets": slot_calorie_targets,
        "output_instruction": "只输出符合 output_schema 的 JSON 对象；只生成候选 recipes；meals 留空，由后端优化器编排。",
        # DeepSeek exposes JSON Object mode rather than OpenAI's strict
        # json_schema response format. LangChain therefore needs the schema in
        # the prompt when method=json_mode is selected below.
        "output_schema": GeneratedPlan.model_json_schema(),
    }
    if base_plan is not None:
        payload["current_plan"] = base_plan
    if edit_message:
        payload["edit_request"] = edit_message
    if action:
        payload["structured_action"] = action
    if validation_feedback:
        payload["validation_feedback"] = validation_feedback
    return json.dumps(payload, ensure_ascii=False, default=str)


def _creative_plan_payload(plan: GeneratedPlan) -> dict:
    """Return a compact creative summary for repair without trusted facts.

    The validation feedback already identifies exact failures. Re-sending every
    step and quantity made 7-day repair prompts unnecessarily large and could
    push otherwise valid JSON beyond a provider's output limit.
    """
    return {
        "candidate_count": len(plan.recipes),
        "recipes": [
            {
                "name": recipe.name,
                "meal_slots": recipe.meal_slots,
                "ingredient_names": [item.input_name or item.name for item in recipe.ingredients],
            }
            for recipe in plan.recipes
        ],
    }


def _output_was_truncated(exc: Exception) -> bool:
    return (
        type(exc).__name__ == "LengthFinishReasonError"
        or "length limit was reached" in str(exc).lower()
        or "finish_reason=length" in str(exc).lower()
    )


async def _invoke_plan(prompt: str, *, temperature: float) -> GeneratedPlan:
    if not settings.LLM_API_KEY:
        raise PlanGenerationError("未配置 LLM_API_KEY，无法生成 AI 原生餐单")

    try:
        llm = get_llm(
            model=settings.PLAN_GENERATION_MODEL or settings.LLM_MODEL,
            temperature=temperature,
            timeout=settings.PLAN_GENERATION_TIMEOUT,
            max_tokens=settings.PLAN_GENERATION_MAX_TOKENS,
        )
        structured_options = {"include_raw": True}
        if "deepseek" in (settings.LLM_API_BASE or "").lower():
            structured_options["method"] = "json_mode"
        structured = llm.with_structured_output(GeneratedPlan, **structured_options)
        response = await structured.ainvoke(
            [
                SystemMessage(content=PLAN_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        return _coerce_plan(response)
    except PlanGenerationError:
        raise
    except Exception as exc:
        logger.exception("AI plan generation failed")
        if _output_was_truncated(exc):
            raise PlanGenerationError("LLM 输出达到长度上限，结构化餐单未完整返回") from exc
        raise PlanGenerationError(f"LLM 餐单生成失败: {str(exc)[:500]}") from exc


async def generate_plan(
    *,
    user_input: str,
    constraints: dict,
    intent: dict | None = None,
    context: str = "",
    base_plan: dict | None = None,
    edit_message: str | None = None,
    action: dict | None = None,
    ingredient_catalog: list[dict] | None = None,
    candidate_target: int | None = None,
) -> GeneratedPlan:
    prompt = _prompt_payload(
        user_input=user_input,
        constraints=constraints,
        intent=intent,
        context=context,
        base_plan=base_plan,
        edit_message=edit_message,
        action=action,
        ingredient_catalog=ingredient_catalog,
        candidate_target=candidate_target,
    )
    try:
        return await _invoke_plan(prompt, temperature=0.7)
    except PlanGenerationError as exc:
        if "输出达到长度上限" not in str(exc) or not candidate_target or candidate_target <= 8:
            raise
        # A shorter complete answer is safer than trying to parse truncated JSON.
        reduced_target = max(8, int(candidate_target * 0.7))
        logger.warning("Plan output truncated; retrying with %s candidates", reduced_target)
        compact_prompt = _prompt_payload(
            user_input=user_input,
            constraints=constraints,
            intent=intent,
            context=context,
            base_plan=base_plan,
            edit_message=edit_message,
            action=action,
            ingredient_catalog=ingredient_catalog,
            candidate_target=reduced_target,
        )
        return await _invoke_plan(compact_prompt, temperature=0.4)


async def repair_plan(
    *,
    plan: GeneratedPlan,
    user_input: str,
    constraints: dict,
    intent: dict | None = None,
    context: str = "",
    base_plan: dict | None = None,
    edit_message: str | None = None,
    action: dict | None = None,
    validation_feedback: dict,
    ingredient_catalog: list[dict] | None = None,
    candidate_target: int | None = None,
) -> GeneratedPlan:
    prompt = _prompt_payload(
        user_input=user_input,
        constraints=constraints,
        intent=intent,
        context=context,
        base_plan=base_plan,
        edit_message=edit_message,
        action=action,
        validation_feedback={
            **validation_feedback,
            "invalid_plan": _creative_plan_payload(plan),
        },
        ingredient_catalog=ingredient_catalog,
        candidate_target=candidate_target,
    )
    return await _invoke_plan(prompt, temperature=0.2)
