"""LangGraph Workflow 装配测试

验证 Graph 可编译、可运行、状态流转正确。
"""

import pytest
from app.workflow.graph import (
    build_workflow,
    route_after_intent,
    route_after_constraint,
    route_after_recommendation,
    route_after_aggregation,
)
from app.workflow.state import WorkflowState


class TestGraphCompilation:
    """验证 Graph 编译"""

    def test_graph_compiles(self):
        workflow = build_workflow()
        compiled = workflow.compile()
        assert compiled is not None
        assert compiled.get_graph() is not None

    def test_graph_has_all_nodes(self):
        workflow = build_workflow()
        compiled = workflow.compile()
        nodes = list(compiled.get_graph().nodes.keys())
        for name in ["intent_analyzer", "constraint", "recommendation",
                      "aggregator", "validation", "summary", "finalize", "error_end"]:
            assert name in nodes, f"Missing node: {name}"


class TestRouting:
    """验证条件路由"""

    def test_intent_success_goes_to_constraint(self):
        state = WorkflowState(intent_analysis={"health_goal": "fat_loss"})
        assert route_after_intent(state) == "constraint"

    def test_intent_error_routes_to_error(self):
        state = WorkflowState(intent_error="LLM failed")
        assert route_after_intent(state) == "error_end"

    def test_constraint_success(self):
        state = WorkflowState(constraints={"target_calories": 2000})
        assert route_after_constraint(state) == "recommendation"

    def test_constraint_error(self):
        state = WorkflowState(constraint_error="Profile not found")
        assert route_after_constraint(state) == "error_end"

    def test_recommendation_success(self):
        state = WorkflowState(ranked_recipes=[{"recipe_id": 1}])
        assert route_after_recommendation(state) == "aggregator"

    def test_recommendation_error(self):
        state = WorkflowState(recommendation_error="No recipes found")
        assert route_after_recommendation(state) == "error_end"

    def test_aggregation_success(self):
        state = WorkflowState(aggregated_result={"top5": []})
        assert route_after_aggregation(state) == "validation"

    def test_aggregation_error(self):
        state = WorkflowState(aggregation_error="DB error")
        assert route_after_aggregation(state) == "error_end"


class TestWorkflowExecution:
    """验证完整 Workflow 执行"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_runs_with_real_data(self):
        """使用真实数据库数据运行完整 Workflow"""
        import json
        from app.db.database import SessionLocal, init_db

        # 确保数据库表存在
        init_db()

        db = SessionLocal()
        try:
            profile = db.query(type('_', (), {'profile_id': int})).from_statement(
                type('_', (), {'__text__': 'SELECT 1'})
            ).all()
        except Exception:
            pass
        finally:
            db.close()

        state = WorkflowState(
            profile_id=1,
            user_input="减脂一周，预算300元，家里有鸡蛋和番茄",
            duration_days=3,
            total_budget=300.0,
        )

        workflow = build_workflow()
        compiled = workflow.compile()

        # 运行（StateGraph 返回 dict）
        result = await compiled.ainvoke(state)

        # 验证结果结构
        assert result is not None

        final = result.get("final_result", {})
        assert "status" in final

        # 成功或失败都应返回友好结果
        if final["status"] == "completed":
            aggregated = result.get("aggregated_result", {})
            assert aggregated
            assert len(aggregated.get("top5", [])) > 0
            assert len(aggregated.get("weekly_plan", [])) > 0
        else:
            # 失败时应有错误信息
            errors = result.get("errors", [])
            assert "error" in final or len(errors) > 0

        print(f"\n=== Workflow Result ===")
        print(f"Status: {final['status']}")
        if final["status"] == "completed":
            aggregated = result.get("aggregated_result", {})
            top5 = aggregated.get("top5", [])
            print(f"TOP5: {[t['name'] for t in top5[:3]]}")
            summary = result.get("summary", "")
            print(f"Summary ({len(summary)} chars)")
        else:
            print(f"Errors: {result.get('errors', [])}")
