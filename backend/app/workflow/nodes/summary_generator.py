"""总结生成节点

使用 LLM 生成可解释的规划总结文案。
LLM 不可用时降级为规则模板。
"""

import json
import logging
import os
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.workflow.llm import get_llm
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def _load_prompt() -> str:
    """加载总结 System Prompt"""
    try:
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "summary_system.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "根据以下饮食规划数据，生成友好的总结文案（300字以内）。"


def _build_llm_input(state: WorkflowState) -> str:
    """从 state 构建 LLM 输入：关键数据摘要"""
    result = state.aggregated_result or {}
    report = result.get("nutrition_report", {})
    shopping = result.get("shopping_list", {})
    top5 = result.get("top5", [])
    constraints = state.constraints or {}

    top_names = [t.get("name", "") for t in top5[:3]]

    lines = [
        f"用户原始输入：{state.user_input}",
        f"健康目标：{constraints.get('health_goal', '未指定')}",
        f"饮食类型：{constraints.get('diet_type', 'balanced')}",
        f"规划天数：{state.duration_days} 天",
        f"总预算：{state.total_budget} 元",
    ]

    if state.intent_analysis:
        owned = state.intent_analysis.get("owned_ingredients", [])
        if owned:
            lines.append(f"已有食材：{'、'.join(owned)}")

    lines.extend([
        f"\n--- TOP{len(top5)} 推荐菜谱 ---",
    ])
    for t in top5:
        s = t.get("scores", {})
        lines.append(
            f"- {t.get('name')} (总分 {t.get('total_score', 0):.2f}, "
            f"热量 {t.get('nutrition', {}).get('calories', 0):.0f}kcal, "
            f"预估 {t.get('estimated_cost', 0):.1f} 元)"
        )

    lines.extend([
        f"\n--- 营养概览 ---",
        f"日均热量：{report.get('avg_daily_calories', 0):.0f} kcal",
        f"蛋白质：{report.get('protein_g', 0):.0f}g/天",
        f"脂肪：{report.get('fat_g', 0):.0f}g/天",
        f"碳水：{report.get('carbs_g', 0):.0f}g/天",
        f"\n--- 采购清单 ---",
        f"预计采购总花费：{shopping.get('total_cost', 0):.1f} 元",
    ])

    return "\n".join(lines)


def _template_summary(state: WorkflowState) -> str:
    """模板降级：生成基础总结文案"""
    result = state.aggregated_result or {}
    report = result.get("nutrition_report", {})
    shopping = result.get("shopping_list", {})
    top5 = result.get("top5", [])

    top_names = [t.get("name", "") for t in top5[:3]]
    shopping_cost = shopping.get("total_cost", 0)
    avg_cal = report.get("avg_daily_calories", 0)
    total_budget = state.total_budget

    budget_info = f"总预算 {total_budget} 元" if total_budget > 0 else "未指定预算"
    cost_info = f"，预计采购花费约 {shopping_cost:.1f} 元" if shopping_cost > 0 else ""
    budget_check = "，在预算范围内" if total_budget > 0 and shopping_cost <= total_budget else ""
    if total_budget > 0 and shopping_cost > total_budget:
        budget_check = f"，超出预算 {shopping_cost - total_budget:.1f} 元，建议适当调整"

    lines = [
        f"📋 饮食规划已为你生成完毕！\n",
        f"{budget_info}{cost_info}{budget_check}。\n",
        f"\n本周重点推荐「{'」、「'.join(top_names)}」等菜谱。\n",
    ]

    if avg_cal > 0:
        lines.append(
            f"\n💪 每日平均摄入 {avg_cal:.0f}kcal，"
        )
        rec = report.get("recommendation", "")
        if rec:
            lines.append(f"{rec}\n")

    lines.append("\n📌 采购建议：周末集中采购一次，肉类和蔬菜可冷藏保存 3-4 天。")
    lines.append("\n🍳 祝您用餐愉快，坚持就是胜利！")

    return "".join(lines)


async def generate_summary(state: WorkflowState) -> WorkflowState:
    """总结生成节点

    依次尝试：
    1. LLM（基于聚合结果数据生成总结）
    2. 模板降级
    """
    state.current_node = "summary_generator"

    if not state.aggregated_result:
        state.summary = "暂无可用数据生成总结。"
        return state

    # ── 尝试 LLM ──
    if settings.LLM_API_KEY:
        try:
            llm = get_llm(temperature=0.7)
            system_prompt = _load_prompt()
            llm_input = _build_llm_input(state)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=llm_input),
            ]

            response = await llm.ainvoke(messages)
            content = response.content

            if content and isinstance(content, str) and len(content.strip()) > 20:
                state.summary = content.strip()
                logger.info("Summary generated via LLM")
                return state

        except Exception as e:
            logger.warning(f"LLM summary failed, falling back to template: {e}")
            state.llm_error = str(e)

    # ── 降级：模板 ──
    state.summary = _template_summary(state)
    logger.info("Summary generated via template")

    return state
