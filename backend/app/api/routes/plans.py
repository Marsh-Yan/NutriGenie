"""饮食规划 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.meal_plan import MealPlan
from app.api.schemas.plan import (
    PlanCreate, PlanCreateResponse,
    PlanStatusResponse, PlanResultResponse, PlanRunningResponse,
    PlanListItem, ProgressInfo, StepInfo,
)
from app.tasks.plan_task import start_plan_task, STEPS
from app.models.profile import Profile
from app.models.user import User
from app.services.security import get_current_user

router = APIRouter(tags=["plans"])


def _can_access_plan(db: Session, plan: MealPlan, user: User) -> bool:
    if user.role == "admin":
        return True
    profile = db.get(Profile, plan.profile_id)
    return bool(profile and profile.user_id == user.user_id)


@router.post("/plans", response_model=PlanCreateResponse, status_code=202)
def api_create_plan(data: PlanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建饮食规划任务（异步）"""
    # 验证用户画像存在
    from app.services.profile_service import get_profile
    profile = get_profile(db, data.profile_id)
    if not profile or (current_user.role != "admin" and profile.user_id != current_user.user_id):
        raise HTTPException(status_code=400, detail="profile_id 不存在")

    plan = MealPlan(
        profile_id=data.profile_id,
        user_input=data.user_input,
        duration_days=data.duration_days,
        total_budget=data.total_budget,
        status="pending",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # 异步执行规划
    start_plan_task(plan.plan_id)

    return PlanCreateResponse(
        plan_id=plan.plan_id,
        status=plan.status,
        created_at=plan.created_at,
        links={
            "status": f"/api/v1/plans/{plan.plan_id}/status",
            "result": f"/api/v1/plans/{plan.plan_id}",
        },
    )


@router.get("/plans", response_model=list[PlanListItem])
def api_list_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """按时间倒序返回当前用户的历史方案。"""
    query = db.query(MealPlan).join(Profile, Profile.profile_id == MealPlan.profile_id)
    if current_user.role != "admin":
        query = query.filter(Profile.user_id == current_user.user_id)
    plans = query.order_by(MealPlan.created_at.desc(), MealPlan.plan_id.desc()).all()
    return [
        PlanListItem(
            plan_id=plan.plan_id,
            status=plan.status,
            user_input=plan.user_input,
            duration_days=plan.duration_days or 7,
            total_budget=float(plan.total_budget or 0),
            created_at=plan.created_at,
            completed_at=plan.completed_at,
        )
        for plan in plans
    ]


@router.get("/plans/{plan_id}/status", response_model=PlanStatusResponse)
def api_get_plan_status(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取规划任务状态"""
    plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).first()
    if not plan or not _can_access_plan(db, plan, current_user):
        raise HTTPException(status_code=404, detail="规划任务不存在")

    response = PlanStatusResponse(
        plan_id=plan.plan_id,
        status=plan.status,
        current_node=plan.current_node,
        created_at=plan.created_at,
        completed_at=plan.completed_at,
    )

    # 状态进度信息
    if plan.status in ("pending", "running"):
        completed = 0
        node_order = _find_step_order(plan.current_node or "")
        current_step = node_order
        steps = []
        for s in STEPS:
            step_status = "pending"
            if s["order"] == node_order:
                step_status = "running"
            elif s["order"] < node_order:
                step_status = "completed"
                completed += 1
            steps.append(StepInfo(name=s["name"], status=step_status, order=s["order"]))

        response.progress = ProgressInfo(
            total_steps=len(STEPS),
            completed_steps=completed,
            current_step=current_step,
            step_name=(STEPS[node_order - 1]["name"] if node_order else "等待开始"),
            steps=steps,
        )

    if plan.status == "failed":
        response.error = plan.error_message

    return response


@router.get("/plans/{plan_id}")
def api_get_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取规划完整结果"""
    plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).first()
    if not plan or not _can_access_plan(db, plan, current_user):
        raise HTTPException(status_code=404, detail="规划任务不存在")

    if plan.status == "running":
        return PlanRunningResponse(
            plan_id=plan.plan_id,
            status="running",
            current_node=plan.current_node,
        )

    if plan.status == "pending":
        return PlanRunningResponse(
            plan_id=plan.plan_id,
            status="pending",
            current_node=None,
        )

    return {
        "plan_id": plan.plan_id,
        "status": plan.status,
        "profile_id": plan.profile_id,
        "user_input": plan.user_input,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "result": plan.result_json,
    }


# node_name → step order 映射
NODE_STEP_MAP = {
    "intent_analyzer": 1, "意图分析": 1,
    "constraint": 2, "constraint_analyzer": 2, "约束分析": 2,
    "recommendation": 3, "recommendation_engine": 3, "混合推荐": 3,
    "aggregator": 4, "计划聚合": 4,
    "validation": 5, "plan_validation": 5, "结果校验": 5,
    "summary": 6, "summary_generator": 6, "生成总结": 6,
}


def _find_step_order(node_name: str) -> int:
    """根据节点名称查找步骤序号"""
    if not node_name:
        return 0
    return NODE_STEP_MAP.get(node_name, 0)
