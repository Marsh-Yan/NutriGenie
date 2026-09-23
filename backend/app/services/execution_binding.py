"""Keep execution state attached to the meal the user actually recorded."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.plan_execution_event import PlanExecutionArchive, PlanExecutionEvent


def meal_keys(result: dict | None) -> dict[tuple[int, str], str]:
    keys: dict[tuple[int, str], str] = {}
    for day in (result or {}).get("weekly_plan") or []:
        day_number = int(day.get("day") or 0)
        for slot, meal in (day.get("meals") or {}).items():
            # Legacy plans did not assign recipe keys. Their name is the best
            # available identity, and must not match a newly generated key.
            keys[(day_number, slot)] = meal.get("recipe_key") or f"legacy:{day_number}:{slot}:{meal.get('name', '')}"
    return keys


def reconcile_execution(
    db: Session,
    *,
    plan_id: int,
    old_result: dict | None,
    old_version_id: int | None,
    new_result: dict,
) -> None:
    """Archive only slots whose recipe changed or disappeared."""
    old_keys = meal_keys(old_result)
    new_keys = meal_keys(new_result)
    events = db.query(PlanExecutionEvent).filter(PlanExecutionEvent.plan_id == plan_id).with_for_update().all()
    for event in events:
        slot = (event.day, event.meal_slot)
        bound_key = event.recipe_key or old_keys.get(slot)
        if bound_key == new_keys.get(slot):
            if event.recipe_key is None:
                event.recipe_key = bound_key
                event.version_id = old_version_id
            continue
        db.add(PlanExecutionArchive(
            plan_id=plan_id,
            user_id=event.user_id,
            day=event.day,
            meal_slot=event.meal_slot,
            version_id=event.version_id or old_version_id,
            recipe_key=bound_key,
            status=event.status,
            note=event.note,
        ))
        db.delete(event)
    db.flush()
