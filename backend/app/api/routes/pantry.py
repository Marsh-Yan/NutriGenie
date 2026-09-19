"""User-owned pantry records with server-side canonical unit enforcement."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.v21 import PantryItemCreate, PantryItemUpdate
from app.db.database import get_db
from app.models.ingredient import Ingredient
from app.models.pantry_item import PantryItem
from app.models.user import User
from app.services.security import get_current_user

router = APIRouter(tags=["pantry"])

UNIT_FACTORS = {
    "g": ("mass", 1), "克": ("mass", 1), "kg": ("mass", 1000), "千克": ("mass", 1000),
    "斤": ("mass", 500), "两": ("mass", 50),
    "ml": ("volume", 1), "毫升": ("volume", 1), "L": ("volume", 1000), "升": ("volume", 1000),
}


def _canonical_quantity(quantity: float, unit: str, ingredient: Ingredient) -> float:
    """Convert only exact mass/volume units; never assume a count-to-gram factor."""
    requested = unit.strip()
    target = ingredient.unit
    if requested == target:
        converted = round(quantity, 2)
        if converted <= 0:
            raise HTTPException(status_code=422, detail="换算后的数量必须大于零")
        return converted
    source_info = UNIT_FACTORS.get(requested)
    target_info = UNIT_FACTORS.get(target)
    if not source_info or not target_info or source_info[0] != target_info[0]:
        raise HTTPException(status_code=422, detail=f"该食材仅接受 {target}；暂不支持跨类型单位换算")
    converted = round(quantity * source_info[1] / target_info[1], 2)
    if converted <= 0 or converted > 100000:
        raise HTTPException(status_code=422, detail="换算后的数量超出支持范围")
    return converted


def _item_payload(item: PantryItem) -> dict:
    return {
        "pantry_item_id": item.pantry_item_id,
        "ingredient_id": item.ingredient_id,
        "quantity": float(item.quantity),
        "unit": item.unit,
        "expires_at": item.expires_at,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _owned_item(db: Session, item_id: int, user_id: int) -> PantryItem:
    item = db.get(PantryItem, item_id)
    if not item or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="库存项不存在")
    return item


@router.get("/pantry")
def api_get_pantry(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(PantryItem).filter(PantryItem.user_id == current_user.user_id).order_by(PantryItem.pantry_item_id).all()
    return {"items": [_item_payload(item) for item in items]}


@router.post("/pantry/items", status_code=201)
def api_create_pantry_item(
    data: PantryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ingredient = db.get(Ingredient, data.ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="食材不存在")
    quantity = _canonical_quantity(data.quantity, data.unit, ingredient)
    existing = db.query(PantryItem).filter(
        PantryItem.user_id == current_user.user_id,
        PantryItem.ingredient_id == data.ingredient_id,
        PantryItem.expires_at == data.expires_at,
    ).with_for_update().first()
    if existing:
        raise HTTPException(status_code=409, detail="相同食材和有效期的库存项已存在，请更新数量")
    item = PantryItem(
        user_id=current_user.user_id, ingredient_id=data.ingredient_id,
        quantity=quantity, unit=ingredient.unit, expires_at=data.expires_at,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="相同食材和有效期的库存项已存在") from exc
    db.refresh(item)
    return _item_payload(item)


@router.put("/pantry/items/{item_id}")
def api_update_pantry_item(
    item_id: int,
    data: PantryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _owned_item(db, item_id, current_user.user_id)
    ingredient = db.get(Ingredient, item.ingredient_id)
    if "expires_at" in data.model_fields_set:
        duplicate = db.query(PantryItem).filter(
            PantryItem.user_id == current_user.user_id,
            PantryItem.ingredient_id == item.ingredient_id,
            PantryItem.expires_at == data.expires_at,
            PantryItem.pantry_item_id != item_id,
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="相同食材和有效期的库存项已存在")
        item.expires_at = data.expires_at
    if data.quantity is not None or data.unit is not None:
        if data.unit is not None and data.quantity is None and data.unit != item.unit:
            raise HTTPException(status_code=422, detail="更改单位时必须同时提供该单位下的数量")
        item.quantity = _canonical_quantity(
            data.quantity if data.quantity is not None else float(item.quantity),
            data.unit or item.unit,
            ingredient,
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="相同食材和有效期的库存项已存在") from exc
    db.refresh(item)
    return _item_payload(item)


@router.delete("/pantry/items/{item_id}", status_code=204)
def api_delete_pantry_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _owned_item(db, item_id, current_user.user_id)
    db.delete(item)
    db.commit()
