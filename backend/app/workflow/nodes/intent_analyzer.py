"""意图分析节点

使用 LLM（DeepSeek）Function Calling 将用户自然语言解析为结构化意图。
LLM 不可用时降级为规则解析。
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from app.config import settings
from app.workflow.llm import get_llm
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

BUDGET_PATTERN = re.compile(
    r"(?:总)?预算\s*(?:(?:改为|调整为|降至|降到|降低至|提高到|约|大概)\s*)?"
    r"(\d+(?:\.\d+)?)\s*(?:元|块)?"
)


def explicit_budget(text: str) -> float | None:
    """Return the latest stated budget, including amounts without a currency suffix."""
    matches = list(BUDGET_PATTERN.finditer(text or ""))
    return float(matches[-1].group(1)) if matches else None


def explicit_duration_days(text: str) -> int | None:
    matches = list(re.finditer(r"(\d+|[一二两三四五六七八九十]+)\s*(天|周|个月)", text or ""))
    if not matches:
        return None
    amount, unit = matches[-1].groups()
    numbers = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if amount.isdigit():
        days = int(amount)
    elif amount.startswith("十") and len(amount) == 2:
        days = 10 + numbers[amount[1]]
    elif "十" in amount and len(amount) == 3:
        days = numbers[amount[0]] * 10 + numbers[amount[2]]
    else:
        days = numbers.get(amount, 0)
    return days * {"天": 1, "周": 7, "个月": 30}[unit]

# ─── 结构化输出 Schema ───────────────────────────


class IntentOutput(BaseModel):
    """LLM 函数调用输出的结构化意图"""
    health_goal: str = Field(description="fat_loss|muscle_gain|blood_sugar|healthy")
    diet_type: str = Field(description="balanced|keto|high_protein|gluten_free|vegan|healthy")
    duration_days: int = Field(description="规划天数")
    total_budget: float = Field(description="总预算，0 表示不限制")
    owned_ingredients: List[str] = Field(description="已有食材列表")
    allergies_or_concerns: Optional[str] = Field(description="过敏或忌口，无则 null")
    meal_count_per_day: int = Field(description="每日餐数")
    additional_notes: Optional[str] = Field(description="补充说明")


def _load_prompt() -> str:
    """加载意图分析 System Prompt"""
    try:
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "intent_system.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "你是一个饮食规划意图分析助手。从用户输入中提取健康目标、饮食类型、天数、预算等信息。"


def _rule_based_parse(user_input: str) -> dict:
    """规则解析：当 LLM 不可用时的降级方案

    从用户输入中提取关键信息。
    """
    text = user_input.lower()

    # 健康目标
    health_goal = "healthy"
    if any(kw in text for kw in ["减脂", "减肥", "瘦", "减重", "fat_loss", "减"]):
        health_goal = "fat_loss"
    elif any(kw in text for kw in ["增肌", "增重", "长肌肉", "muscle_gain", "增"]):
        health_goal = "muscle_gain"
    elif any(kw in text for kw in ["控糖", "血糖", "blood_sugar", "糖尿病"]):
        health_goal = "blood_sugar"

    # 饮食类型
    diet_type = "balanced"
    if any(kw in text for kw in ["生酮", "keto"]):
        diet_type = "keto"
    elif any(kw in text for kw in ["高蛋白", "high_protein"]):
        diet_type = "high_protein"
    elif any(kw in text for kw in ["无麸质", "gluten_free"]):
        diet_type = "gluten_free"
    elif any(kw in text for kw in ["素食", "vegan", "纯素"]):
        diet_type = "vegan"
    elif any(kw in text for kw in ["健康饮食", "healthy"]):
        diet_type = "healthy"

    # 天数（系统单次规划上限 30 天）
    duration_days = 7
    requested_days = explicit_duration_days(text)
    if requested_days is not None:
        duration_days = min(requested_days, 30)
    else:
        # 中文数字匹配
        cn_num_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                      "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for cn, num in cn_num_map.items():
            if f"{cn}天" in text:
                duration_days = num
                break
            if f"{cn}周" in text:
                duration_days = min(num * 7, 30)
                break
            if f"{cn}个月" in text:
                duration_days = min(num * 30, 30)
                break

    # 预算
    total_budget = 0.0
    explicit_amount = explicit_budget(text)
    if explicit_amount is not None:
        total_budget = explicit_amount

    # 已有食材
    owned_ingredients = []
    # 匹配"有"后面的内容（简单字符串分割，避免正则字符集编码问题）
    have_keywords = ["有", "现有", "家里有", "我有", "还有"]
    have_pos = -1
    for kw in have_keywords:
        idx = text.find(kw)
        if idx >= 0:
            after = idx + len(kw)
            if after > have_pos:
                have_pos = after
    if have_pos >= 0:
        raw = text[have_pos:]
        # 截断到关键词为止
        for stop in ["预算", "不吃", "不要", "不能", "过敏", "忌口", "帮我", "我想", "我要", "准备", "打算"]:
            idx = raw.find(stop)
            if idx >= 0:
                raw = raw[:idx]
        items = re.split(r"[、，,和与]", raw)
        for item in items:
            item = item.strip()
            if item and len(item) <= 10:
                owned_ingredients.append(item)

    # 过敏/忌口
    allergies_or_concerns = None
    for kw in ["不吃", "过敏", "忌口", "不能吃", "不要"]:
        if kw in text:
            idx = text.index(kw)
            after = text[idx + len(kw):].strip().split("，")[0].split("。")[0]
            if after and len(after) <= 20:
                allergies_or_concerns = after.strip()
                break

    # 每日餐数（当前计划支持 1-3 餐，未说明时为早/午/晚三餐）
    meal_count_per_day = 3
    meal_match = re.search(r"(?:每天|每日|只吃|一天)?\s*([123一二两三])\s*(?:餐|顿)", text)
    if meal_match:
        count_map = {"一": 1, "二": 2, "两": 2, "三": 3}
        raw_count = meal_match.group(1)
        meal_count_per_day = max(1, min(int(raw_count) if raw_count.isdigit() else count_map[raw_count], 3))

    return {
        "health_goal": health_goal,
        "diet_type": diet_type,
        "duration_days": duration_days,
        "total_budget": total_budget,
        "owned_ingredients": owned_ingredients,
        "allergies_or_concerns": allergies_or_concerns,
        "meal_count_per_day": meal_count_per_day,
        "additional_notes": None,
    }


def _apply_explicit_intent_overrides(user_input: str, llm_intent: dict) -> dict:
    """Keep explicit user constraints authoritative when an LLM disagrees.

    A model may return a plausible but incorrect generic goal.  Health goal and
    diet keywords are safety-relevant constraints, so an explicit keyword in
    the user's text takes precedence over the model's inferred value.
    """
    merged = dict(llm_intent)
    rule_intent = _rule_based_parse(user_input)
    if rule_intent["health_goal"] != "healthy":
        merged["health_goal"] = rule_intent["health_goal"]
    if rule_intent["diet_type"] != "balanced":
        merged["diet_type"] = rule_intent["diet_type"]
    if explicit_duration_days(user_input) is not None:
        merged["duration_days"] = rule_intent["duration_days"]
    if explicit_budget(user_input) is not None:
        merged["total_budget"] = rule_intent["total_budget"]
    if rule_intent.get("allergies_or_concerns"):
        merged["allergies_or_concerns"] = rule_intent["allergies_or_concerns"]
    if re.search(r"(?:每天|每日|只吃|一天)?\s*[123一二两三]\s*(?:餐|顿)", user_input):
        merged["meal_count_per_day"] = rule_intent["meal_count_per_day"]
    return merged


def _merge_edit_intent(previous: dict, parsed: dict, edit_text: str) -> dict:
    """Apply only fields explicitly changed by the newest edit."""
    merged = dict(previous)
    lowered = edit_text.lower()
    if any(token in lowered for token in ("减脂", "减肥", "增肌", "控糖", "健康目标", "fat_loss", "muscle_gain")):
        merged["health_goal"] = parsed.get("health_goal", merged.get("health_goal"))
    if any(token in lowered for token in ("生酮", "高蛋白", "无麸质", "素食", "纯素", "均衡饮食", "keto", "vegan")):
        merged["diet_type"] = parsed.get("diet_type", merged.get("diet_type"))
    if explicit_duration_days(edit_text) is not None:
        merged["duration_days"] = parsed.get("duration_days", merged.get("duration_days"))
    if explicit_budget(edit_text) is not None:
        merged["total_budget"] = parsed.get("total_budget", merged.get("total_budget"))
    if any(token in edit_text for token in ("过敏", "忌口", "不吃", "不能吃")):
        concern = str(parsed.get("allergies_or_concerns") or "").strip()
        prior = str(previous.get("allergies_or_concerns") or "").strip()
        if concern and concern not in prior:
            merged["allergies_or_concerns"] = "、".join(filter(None, (prior, concern)))
    if re.search(r"(?:每天|每日|只吃|一天)?\s*[123一二两三]\s*(?:餐|顿)", edit_text):
        merged["meal_count_per_day"] = parsed.get("meal_count_per_day", merged.get("meal_count_per_day"))
    if parsed.get("owned_ingredients") and any(token in edit_text for token in ("已有", "家里有", "现有")):
        merged["owned_ingredients"] = list(dict.fromkeys(
            list(previous.get("owned_ingredients") or []) + list(parsed["owned_ingredients"])
        ))
    return merged


def _sync_explicit_constraints_to_state(
    state: WorkflowState, intent_data: dict
) -> None:
    """Make explicit natural-language constraints authoritative over defaults."""
    if explicit_duration_days(state.user_input) is not None:
        state.duration_days = max(1, min(int(intent_data.get("duration_days", state.duration_days)), 30))
    if explicit_budget(state.user_input) is not None:
        state.total_budget = max(0.0, float(intent_data.get("total_budget", state.total_budget) or 0))


async def analyze_intent(state: WorkflowState) -> WorkflowState:
    """意图分析节点

    依次尝试：
    1. LLM + Function Calling
    2. 规则解析（降级）
    """
    state.current_node = "intent_analyzer"

    if state.skip_intent and state.intent_analysis:
        return state

    if not state.user_input:
        state.intent_error = "用户输入为空"
        state.errors.append(state.intent_error)
        return state

    # ── 尝试 LLM Function Calling ──
    if settings.LLM_API_KEY:
        try:
            llm = get_llm(temperature=0.1)
            system_prompt = _load_prompt()

            # 绑定函数调用工具
            llm_with_tools = llm.bind_tools([IntentOutput], tool_choice="IntentOutput")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state.user_input),
            ]

            response = await llm_with_tools.ainvoke(messages)

            # 解析工具调用结果
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                intent_data = tool_call.get("args", {})
            else:
                # 没有工具调用，尝试从 content 中解析 JSON
                content = response.content
                intent_data = _parse_json_from_text(content) if content else {}

            if intent_data:
                intent_data = _apply_explicit_intent_overrides(
                    state.user_input, intent_data
                )
                if state.is_edit and state.intent_analysis:
                    intent_data = _merge_edit_intent(state.intent_analysis, intent_data, state.user_input)
                state.intent_analysis = intent_data
                _sync_explicit_constraints_to_state(state, intent_data)
                state.intent_explanation = _generate_intent_explanation(intent_data)
                logger.info(f"Intent analyzed via LLM: {intent_data.get('health_goal')}")
                return state

        except Exception as e:
            logger.warning(f"LLM intent analysis failed, falling back to rules: {e}")
            state.intent_error = str(e)

    # ── 降级：规则解析 ──
    intent_data = _rule_based_parse(state.user_input)
    if state.is_edit and state.intent_analysis:
        intent_data = _merge_edit_intent(state.intent_analysis, intent_data, state.user_input)
    state.intent_analysis = intent_data
    _sync_explicit_constraints_to_state(state, intent_data)
    state.intent_explanation = _generate_intent_explanation(intent_data) + "（基于规则解析）"
    logger.info(f"Intent analyzed via rules: {intent_data.get('health_goal')}")

    return state


def _parse_json_from_text(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    # 尝试找 ```json ... ``` 块
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试直接找第一个 { 到最后一个 }
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def _generate_intent_explanation(intent: dict) -> str:
    """生成意图分析的可解释文本"""
    goal_names = {
        "fat_loss": "减脂", "muscle_gain": "增肌",
        "blood_sugar": "控糖", "healthy": "健康饮食",
    }
    diet_names = {
        "balanced": "均衡饮食", "keto": "生酮饮食",
        "high_protein": "高蛋白饮食", "gluten_free": "无麸质饮食",
        "vegan": "素食", "healthy": "健康饮食",
    }

    goal = goal_names.get(intent.get("health_goal", ""), "健康饮食")
    diet = diet_names.get(intent.get("diet_type", ""), "均衡饮食")
    days = intent.get("duration_days", 7)
    budget = intent.get("total_budget", 0)

    parts = [f"目标：{goal}，饮食类型：{diet}，规划天数：{days}天"]
    if budget > 0:
        parts.append(f"总预算：{budget}元")
    if intent.get("owned_ingredients"):
        parts.append(f"已有食材：{'、'.join(intent['owned_ingredients'][:3])}")
    if intent.get("allergies_or_concerns"):
        parts.append(f"忌口：{intent['allergies_or_concerns']}")

    return "，".join(parts)
