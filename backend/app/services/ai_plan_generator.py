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


PLAN_SYSTEM_PROMPT = """你是 NutriGenie 的 AI 原生饮食规划器。

你的任务是根据用户画像、硬性约束和可选参考资料，生成完整的多日餐单。
必须严格返回符合结构化 schema 的 JSON，不要输出 Markdown 或额外解释。

规则：
1. recipes 是菜谱定义数组；meals 使用 recipe_index 引用 recipes，索引从 0 开始。
2. 每个食材的 nutrition_estimate 和 line_cost_estimate 必须对应当前 quantity 的估算值。
3. 每道菜必须有至少一个食材、一个步骤和可解释的营养与成本估算。
4. 每天必须生成 breakfast、lunch、dinner 三个 slot；可以额外生成 snack。
5. 绝不能使用用户明确过敏、忌口或饮食类型禁止的食材。
6. 预算、热量和蛋白质是目标，不要为了凑数字生成不真实的食材用量。
7. 不要做疾病诊断、治疗承诺或保证性健康结论。
8. 参考资料只用于常识和灵感；如果参考资料与用户硬约束冲突，以用户硬约束为准。
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
) -> str:
    payload = {
        "user_request": user_input,
        "intent": intent or {},
        "constraints": constraints,
        "reference_context": context or "无可用参考资料",
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


async def _invoke_plan(prompt: str, *, temperature: float) -> GeneratedPlan:
    if not settings.LLM_API_KEY:
        raise PlanGenerationError("未配置 LLM_API_KEY，无法生成 AI 原生餐单")

    try:
        llm = get_llm(
            model=settings.PLAN_GENERATION_MODEL or settings.LLM_MODEL,
            temperature=temperature,
            timeout=settings.PLAN_GENERATION_TIMEOUT,
        )
        structured = llm.with_structured_output(
            GeneratedPlan,
            include_raw=True,
        )
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
) -> GeneratedPlan:
    prompt = _prompt_payload(
        user_input=user_input,
        constraints=constraints,
        intent=intent,
        context=context,
        base_plan=base_plan,
        edit_message=edit_message,
        action=action,
    )
    return await _invoke_plan(prompt, temperature=0.7)


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
            "invalid_plan": plan.model_dump(mode="json"),
        },
    )
    return await _invoke_plan(prompt, temperature=0.2)
