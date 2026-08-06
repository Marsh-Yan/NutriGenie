"""LLM 路径测试 — Mock 模拟 LLM 调用，无需真实 API Key"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workflow.state import WorkflowState


@pytest.mark.asyncio
async def test_intent_analyzer_llm_path():
    """Mock LLM 调用，验证 IntentAnalyzer 的 LLM 路径"""
    from app.workflow.nodes.intent_analyzer import analyze_intent

    state = WorkflowState(
        profile_id=1,
        user_input="减脂一周，预算300元，家里有鸡蛋和番茄",
        duration_days=7,
        total_budget=300,
    )

    # Mock LLM 返回结果 — 正确处理 bind_tools 链式调用
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {
            "name": "IntentOutput",
            "args": {
                "health_goal": "fat_loss",
                "diet_type": "balanced",
                "duration_days": 7,
                "total_budget": 300.0,
                "owned_ingredients": ["鸡蛋", "番茄"],
                "allergies_or_concerns": None,
                "meal_count_per_day": 3,
                "additional_notes": None,
            },
        }
    ]

    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.bind_tools.return_value = mock_bound

    with patch("app.workflow.nodes.intent_analyzer.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-mock-key"
        mock_settings.LLM_API_BASE = "https://api.deepseek.com"
        mock_settings.LLM_MODEL = "deepseek-chat"
        mock_settings.LLM_TIMEOUT = 30

        with patch("app.workflow.nodes.intent_analyzer.get_llm", return_value=mock_llm):
            result = await analyze_intent(state)

    # 验证结果
    assert result.intent_analysis is not None
    assert result.intent_analysis["health_goal"] == "fat_loss"
    assert result.intent_analysis["duration_days"] == 7
    assert result.intent_analysis["total_budget"] == 300.0
    assert "鸡蛋" in result.intent_analysis["owned_ingredients"]
    assert result.intent_explanation is not None
    assert "减脂" in result.intent_explanation
    assert result.current_node == "intent_analyzer"


@pytest.mark.asyncio
async def test_intent_analyzer_llm_fallback_to_rules():
    """LLM 调用失败时降级到规则解析"""
    from app.workflow.nodes.intent_analyzer import analyze_intent

    state = WorkflowState(
        profile_id=1,
        user_input="减脂一周，预算300元",
        duration_days=7,
        total_budget=300,
    )

    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(side_effect=Exception("API timeout"))
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound

    with patch("app.workflow.nodes.intent_analyzer.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-mock-key"
        mock_settings.LLM_API_BASE = "https://api.deepseek.com"
        mock_settings.LLM_MODEL = "deepseek-chat"
        mock_settings.LLM_TIMEOUT = 30

        with patch("app.workflow.nodes.intent_analyzer.get_llm", return_value=mock_llm):
            result = await analyze_intent(state)

    # 降级到规则解析，结果应该正确
    assert result.intent_analysis is not None
    assert result.intent_analysis["health_goal"] == "fat_loss"
    assert result.intent_analysis["duration_days"] == 7
    assert result.intent_analysis["total_budget"] == 300.0
    # 降级时 intent_error 应该记录原始错误
    assert result.intent_error is not None


@pytest.mark.asyncio
async def test_summary_generator_llm_path():
    """Mock LLM 调用，验证 SummaryGenerator 的 LLM 路径"""
    from app.workflow.nodes.summary_generator import generate_summary

    state = WorkflowState(
        profile_id=1,
        user_input="减脂一周，预算300元",
        duration_days=7,
        total_budget=300,
        aggregated_result={
            "top5": [
                {"name": "番茄炒蛋", "total_score": 0.85, "estimated_cost": 6.5,
                 "scores": {"health": 0.88}, "nutrition": {"calories": 150}},
                {"name": "西兰花炒虾仁", "total_score": 0.82, "estimated_cost": 18.5,
                 "scores": {"health": 0.92}, "nutrition": {"calories": 180}},
            ],
            "nutrition_report": {
                "avg_daily_calories": 1650, "total_calories": 11550,
                "protein_g": 95, "fat_g": 48, "carbs_g": 198, "fiber_g": 25,
                "protein_pct": 0.34, "fat_pct": 0.26, "carbs_pct": 0.40,
                "recommendation": "蛋白质占比 34%，有助于减脂期保留肌肉。",
            },
            "shopping_list": {
                "total_cost": 285.5, "items": [], "by_category": {},
            },
        },
    )

    mock_response = MagicMock()
    mock_response.content = "📋 你的减脂饮食计划已生成！预算300元内可完成采购，推荐番茄炒蛋和西兰花炒虾仁。💪 坚持一周效果显著！"
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.workflow.nodes.summary_generator.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-mock-key"
        mock_settings.LLM_API_BASE = "https://api.deepseek.com"
        mock_settings.LLM_MODEL = "deepseek-chat"
        mock_settings.LLM_TIMEOUT = 30

        with patch("app.workflow.nodes.summary_generator.get_llm", return_value=mock_llm):
            result = await generate_summary(state)

    assert result.summary is not None
    assert len(result.summary) > 20
    assert "减脂" in result.summary


@pytest.mark.asyncio
async def test_summary_generator_llm_fallback():
    """LLM 总结失败时降级到模板"""
    from app.workflow.nodes.summary_generator import generate_summary

    state = WorkflowState(
        profile_id=1,
        user_input="减脂一周，预算300元",
        duration_days=7,
        total_budget=300,
        aggregated_result={
            "top5": [{"name": "番茄炒蛋", "total_score": 0.85}],
            "nutrition_report": {
                "avg_daily_calories": 1650, "total_calories": 11550,
                "protein_g": 95, "fat_g": 48, "carbs_g": 198,
                "protein_pct": 0.34, "fat_pct": 0.26, "carbs_pct": 0.40,
                "recommendation": "蛋白质占比 34%。",
            },
            "shopping_list": {"total_cost": 285.5, "items": [], "by_category": {}},
        },
    )

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

    with patch("app.workflow.nodes.summary_generator.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-mock-key"
        mock_settings.LLM_API_BASE = "https://api.deepseek.com"
        mock_settings.LLM_MODEL = "deepseek-chat"
        mock_settings.LLM_TIMEOUT = 30

        with patch("app.workflow.nodes.summary_generator.get_llm", return_value=mock_llm):
            result = await generate_summary(state)

    assert result.summary is not None
    assert len(result.summary) > 30
    assert "📋" in result.summary
