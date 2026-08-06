"""用户画像相关数据查询服务"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.profile import Profile


def get_profile(db: Session, profile_id: int) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.profile_id == profile_id).first()


def create_profile(db: Session, data: dict) -> Profile:
    profile = Profile(**data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, profile_id: int, data: dict) -> Optional[Profile]:
    profile = get_profile(db, profile_id)
    if not profile:
        return None

    for key, value in data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile
