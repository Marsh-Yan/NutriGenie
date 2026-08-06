"""用户画像 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.services.profile_service import get_profile, create_profile, update_profile
from app.services.tdee import calculate_tdee, calculate_bmi, get_bmi_category
from app.models.user import User
from app.models.profile import Profile
from app.services.security import get_current_user

router = APIRouter(tags=["profiles"])


def _enrich_profile(profile, db: Session) -> dict:
    """在 profile 响应中附加 TDEE/BMI 计算值"""
    data = {
        "profile_id": profile.profile_id,
        "age": profile.age,
        "gender": profile.gender,
        "height": float(profile.height),
        "weight": float(profile.weight),
        "diet_type": profile.diet_type,
        "health_goal": profile.health_goal,
        "allergies": profile.allergies,
        "daily_budget": float(profile.daily_budget),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "tdee": calculate_tdee(
            gender=profile.gender,
            weight_kg=float(profile.weight),
            height_cm=float(profile.height),
            age=profile.age,
        ),
        "bmi": calculate_bmi(
            weight_kg=float(profile.weight),
            height_cm=float(profile.height),
        ),
    }
    return data


@router.post("/profiles", response_model=ProfileResponse, status_code=201)
def api_create_profile(data: ProfileCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = create_profile(db, {**data.model_dump(), "user_id": current_user.user_id})
    return _enrich_profile(profile, db)


@router.get("/profiles/id/{profile_id}", response_model=ProfileResponse)
def api_get_profile(profile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = get_profile(db, profile_id)
    if not profile or (current_user.role != "admin" and profile.user_id != current_user.user_id):
        raise HTTPException(status_code=404, detail="用户画像不存在")
    return _enrich_profile(profile, db)


@router.get("/profiles/me", response_model=ProfileResponse)
def api_get_my_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="尚未创建用户画像")
    return _enrich_profile(profile, db)


@router.put("/profiles/id/{profile_id}", response_model=ProfileResponse)
def api_update_profile(profile_id: int, data: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = get_profile(db, profile_id)
    if not existing or (current_user.role != "admin" and existing.user_id != current_user.user_id):
        raise HTTPException(status_code=404, detail="用户画像不存在")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    profile = update_profile(db, profile_id, update_data)
    if not profile:
        raise HTTPException(status_code=404, detail="用户画像不存在")
    return _enrich_profile(profile, db)
