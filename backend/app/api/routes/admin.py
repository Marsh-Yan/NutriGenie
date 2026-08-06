"""Administrator-only APIs for the management console."""

from pathlib import Path
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ingredient import Ingredient
from app.models.meal_plan import MealPlan
from app.models.profile import Profile
from app.models.recipe import Recipe
from app.models.user import User
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.recipe_ingredient import RecipeIngredient
from app.models.knowledge import KnowledgeDocumentRecord, KnowledgeIngestionJob
from app.api.schemas.admin import IngredientWrite, RecipeWrite, KnowledgeDocumentWrite
from app.rag.document_loader import load_recipe_documents
from app.rag.vector_store import RecipeVectorStore
from app.services.security import require_admin
from app.services.knowledge_index import delete_document
from app.services.knowledge_storage import LocalKnowledgeStorage
from app.services.knowledge_queue import enqueue_index_job

router = APIRouter(tags=["admin"])
KNOWLEDGE_RECIPES_DIR = Path("knowledge_base/recipes")
KNOWLEDGE_FILES_DIR = Path("knowledge_base/documents")
KNOWLEDGE_STORAGE = LocalKnowledgeStorage(KNOWLEDGE_FILES_DIR)
MAX_KNOWLEDGE_FILE_BYTES = 512 * 1024
SUPPORTED_KNOWLEDGE_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".pdf"}


def _ingredient_payload(ingredient: Ingredient, nutrition: IngredientNutrition | None) -> dict:
    return {
        "ingredient_id": ingredient.ingredient_id, "name": ingredient.name,
        "category": ingredient.category, "unit": ingredient.unit,
        "unit_price": float(ingredient.unit_price), "season_tags": ingredient.season_tags,
        "storage_days": ingredient.storage_days,
        "nutrition": {
            "calories": float(nutrition.calories_per_100g) if nutrition else 0,
            "protein": float(nutrition.protein_per_100g) if nutrition else 0,
            "fat": float(nutrition.fat_per_100g) if nutrition else 0,
            "carbs": float(nutrition.carbs_per_100g) if nutrition else 0,
            "fiber": float(nutrition.fiber_per_100g) if nutrition else 0,
        },
    }


def _save_ingredient(db: Session, ingredient: Ingredient, data: IngredientWrite) -> Ingredient:
    ingredient.name = data.name
    ingredient.category = data.category
    ingredient.unit = data.unit
    ingredient.unit_price = data.unit_price
    ingredient.season_tags = data.season_tags
    ingredient.storage_days = data.storage_days
    nutrition = db.query(IngredientNutrition).filter_by(ingredient_id=ingredient.ingredient_id).first()
    if not nutrition:
        nutrition = IngredientNutrition(ingredient_id=ingredient.ingredient_id)
        db.add(nutrition)
    nutrition.calories_per_100g = data.nutrition.calories
    nutrition.protein_per_100g = data.nutrition.protein
    nutrition.fat_per_100g = data.nutrition.fat
    nutrition.carbs_per_100g = data.nutrition.carbs
    nutrition.fiber_per_100g = data.nutrition.fiber
    db.commit(); db.refresh(ingredient)
    return ingredient


@router.get("/admin/overview")
def get_overview(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Return only aggregate counts; no user private data is exposed."""
    return {
        "users": db.query(User).count(),
        "profiles": db.query(Profile).count(),
        "recipes": db.query(Recipe).count(),
        "ingredients": db.query(Ingredient).count(),
        "plans": db.query(MealPlan).count(),
    }


@router.get("/admin/ingredients")
def list_ingredients(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ingredients = db.query(Ingredient).order_by(Ingredient.ingredient_id.desc()).all()
    nutrition = {item.ingredient_id: item for item in db.query(IngredientNutrition).all()}
    return [_ingredient_payload(item, nutrition.get(item.ingredient_id)) for item in ingredients]


@router.post("/admin/ingredients", status_code=status.HTTP_201_CREATED)
def create_ingredient(data: IngredientWrite, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ingredient = Ingredient(name=data.name, category=data.category, unit=data.unit, unit_price=data.unit_price,
                            season_tags=data.season_tags, storage_days=data.storage_days)
    db.add(ingredient); db.flush()
    ingredient = _save_ingredient(db, ingredient, data)
    nutrition = db.query(IngredientNutrition).filter_by(ingredient_id=ingredient.ingredient_id).first()
    return _ingredient_payload(ingredient, nutrition)


@router.put("/admin/ingredients/{ingredient_id}")
def update_ingredient(ingredient_id: int, data: IngredientWrite, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ingredient = _save_ingredient(db, ingredient, data)
    nutrition = db.query(IngredientNutrition).filter_by(ingredient_id=ingredient_id).first()
    return _ingredient_payload(ingredient, nutrition)


@router.delete("/admin/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if db.query(RecipeIngredient).filter_by(ingredient_id=ingredient_id).first():
        raise HTTPException(status_code=409, detail="Ingredient is still used by a recipe")
    nutrition = db.query(IngredientNutrition).filter_by(ingredient_id=ingredient_id).first()
    if nutrition: db.delete(nutrition)
    db.delete(ingredient); db.commit()


def _save_recipe(db: Session, recipe: Recipe, data: RecipeWrite) -> Recipe:
    ingredient_ids = [item.ingredient_id for item in data.ingredients]
    if len(ingredient_ids) != len(set(ingredient_ids)):
        raise HTTPException(status_code=422, detail="Duplicate ingredient in recipe")
    found_ids = {row[0] for row in db.query(Ingredient.ingredient_id).filter(Ingredient.ingredient_id.in_(ingredient_ids)).all()} if ingredient_ids else set()
    if found_ids != set(ingredient_ids):
        raise HTTPException(status_code=422, detail="Recipe contains an unknown ingredient")
    for key in ("name", "description", "category", "cuisine_type", "difficulty", "prep_time", "cook_time", "servings", "steps", "image_url", "tags"):
        setattr(recipe, key, getattr(data, key))
    recipe.total_calories = data.nutrition.calories; recipe.total_protein = data.nutrition.protein
    recipe.total_fat = data.nutrition.fat; recipe.total_carbs = data.nutrition.carbs; recipe.total_fiber = data.nutrition.fiber
    db.query(RecipeIngredient).filter_by(recipe_id=recipe.recipe_id).delete()
    for item in data.ingredients:
        db.add(RecipeIngredient(recipe_id=recipe.recipe_id, ingredient_id=item.ingredient_id,
                                quantity=item.quantity, unit=item.unit, is_optional=int(item.is_optional)))
    db.commit(); db.refresh(recipe)
    return recipe


@router.post("/admin/recipes", status_code=status.HTTP_201_CREATED)
def create_recipe(data: RecipeWrite, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    recipe = Recipe(name=data.name, category=data.category, cuisine_type=data.cuisine_type, prep_time=data.prep_time, cook_time=data.cook_time, steps=[])
    db.add(recipe); db.flush()
    recipe = _save_recipe(db, recipe, data)
    return {"recipe_id": recipe.recipe_id}


@router.put("/admin/recipes/{recipe_id}")
def update_recipe(recipe_id: int, data: RecipeWrite, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe: raise HTTPException(status_code=404, detail="Recipe not found")
    _save_recipe(db, recipe, data)
    return {"recipe_id": recipe.recipe_id}


@router.delete("/admin/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe: raise HTTPException(status_code=404, detail="Recipe not found")
    db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).delete()
    db.delete(recipe); db.commit()


@router.get("/admin/knowledge/documents")
def list_knowledge_documents(_: User = Depends(require_admin)):
    """List Markdown documents that are eligible for the recipe RAG index."""
    documents = load_recipe_documents(KNOWLEDGE_RECIPES_DIR)
    return [{"recipe_id": doc.metadata["recipe_id"], "source_file": doc.metadata["source_file"],
             "content_hash": doc.metadata["content_hash"], "preview": doc.content[:180]} for doc in documents]


@router.get("/admin/knowledge/documents/{recipe_id}")
def get_knowledge_document(recipe_id: int, _: User = Depends(require_admin)):
    target = KNOWLEDGE_RECIPES_DIR / f"recipe_{recipe_id:02d}.md"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return {"recipe_id": recipe_id, "content": target.read_text(encoding="utf-8")}


@router.put("/admin/knowledge/documents/{recipe_id}")
def save_knowledge_document(recipe_id: int, data: KnowledgeDocumentWrite,
                            db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if recipe_id != data.recipe_id or not db.get(Recipe, recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not data.content.startswith("---") or f"recipe_id: {recipe_id}" not in data.content.split("---", 2)[1]:
        raise HTTPException(status_code=422, detail="Markdown frontmatter must contain the matching recipe_id")
    KNOWLEDGE_RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    target = KNOWLEDGE_RECIPES_DIR / f"recipe_{recipe_id:02d}.md"
    previous_content = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(data.content, encoding="utf-8")
    try:
        load_recipe_documents(KNOWLEDGE_RECIPES_DIR)
    except ValueError as exc:
        if previous_content is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(previous_content, encoding="utf-8")
        raise HTTPException(status_code=422, detail=str(exc))
    return {"recipe_id": recipe_id, "source_file": target.name, "reindex_required": True}


@router.post("/admin/knowledge/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """Import one UTF-8 recipe Markdown file; indexing remains an explicit action."""
    filename = file.filename or ""
    if not filename.lower().endswith(".md"):
        raise HTTPException(status_code=415, detail="Only .md files can be uploaded")
    raw = await file.read(MAX_KNOWLEDGE_FILE_BYTES + 1)
    if len(raw) > MAX_KNOWLEDGE_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Markdown file must be 512 KB or smaller")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Markdown must use UTF-8 encoding")
    match = re.search(r"^recipe_id:\s*(\d+)\s*$", content, flags=re.MULTILINE)
    if not content.startswith("---") or not match:
        raise HTTPException(status_code=422, detail="Frontmatter must contain an integer recipe_id")
    recipe_id = int(match.group(1))
    if not db.get(Recipe, recipe_id):
        raise HTTPException(status_code=422, detail="The referenced recipe_id does not exist")
    target = KNOWLEDGE_RECIPES_DIR / f"recipe_{recipe_id:02d}.md"
    KNOWLEDGE_RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    previous_content = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(content, encoding="utf-8")
    try:
        load_recipe_documents(KNOWLEDGE_RECIPES_DIR)
    except ValueError as exc:
        if previous_content is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(previous_content, encoding="utf-8")
        raise HTTPException(status_code=422, detail=str(exc))
    return {"recipe_id": recipe_id, "source_file": target.name, "reindex_required": True}


@router.post("/admin/knowledge/rebuild")
def rebuild_knowledge_index(_: User = Depends(require_admin)):
    """Rebuild the Chroma index. This intentionally makes remote embedding calls."""
    documents = load_recipe_documents(KNOWLEDGE_RECIPES_DIR)
    count = RecipeVectorStore().rebuild(documents)
    return {"indexed_documents": count}


@router.get("/admin/knowledge/files")
def list_knowledge_files(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """列出通用知识文档及其索引状态。"""
    records = db.query(KnowledgeDocumentRecord).order_by(KnowledgeDocumentRecord.document_id.desc()).all()
    return [
        {
            "document_id": item.document_id,
            "source_file": item.source_file,
            "file_type": item.file_type,
            "content_hash": item.content_hash,
            "version": item.version,
            "status": item.status,
            "indexed_chunks": item.indexed_chunks,
            "embedding_provider": item.embedding_provider,
            "embedding_model": item.embedding_model,
            "embedding_dimensions": item.embedding_dimensions,
            "embedding_version": item.embedding_version,
            "error_message": item.error_message,
        }
        for item in records
    ]


@router.delete("/admin/knowledge/files/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_file(document_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    record = db.get(KnowledgeDocumentRecord, document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    try:
        delete_document(db, record, KNOWLEDGE_FILES_DIR, storage=KNOWLEDGE_STORAGE)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge document: {exc}") from exc


@router.post("/admin/knowledge/files/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_file(
    file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """上传已完成清洗/OCR 的 Markdown、TXT 或带文本层 PDF。"""
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in SUPPORTED_KNOWLEDGE_SUFFIXES:
        raise HTTPException(status_code=415, detail="Only Markdown, TXT, or text-layer PDF files are supported")
    raw = await file.read(MAX_KNOWLEDGE_FILE_BYTES + 1)
    if len(raw) > MAX_KNOWLEDGE_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Knowledge file must be 512 KB or smaller")
    if suffix != ".pdf":
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="Markdown/TXT must use UTF-8 encoding")
    import hashlib

    content_hash = hashlib.sha256(raw).hexdigest()
    target = KNOWLEDGE_STORAGE.path(filename)
    record = db.query(KnowledgeDocumentRecord).filter_by(source_file=filename).first()
    if record:
        if record.content_hash == content_hash:
            return {"document_id": record.document_id, "status": record.status, "changed": False}
        record.version += 1
        record.content_hash = content_hash
        record.status = "pending"
    else:
        record = KnowledgeDocumentRecord(
            source_file=filename, file_type=suffix.lstrip("."), content_hash=content_hash, status="pending"
        )
        db.add(record)
    KNOWLEDGE_STORAGE.save(filename, raw)
    db.commit()
    db.refresh(record)
    return {
        "document_id": record.document_id,
        "source_file": filename,
        "version": record.version,
        "status": record.status,
        "reindex_required": True,
    }


@router.post("/admin/knowledge/files/{document_id}/index", status_code=status.HTTP_202_ACCEPTED)
def index_knowledge_file(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    record = db.get(KnowledgeDocumentRecord, document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    if not KNOWLEDGE_STORAGE.exists(record.source_file):
        record.status = "failed"
        record.error_message = "Source file is missing"
        db.commit()
        raise HTTPException(status_code=409, detail="Source file is missing")
    if record.status == "processing":
        return {"document_id": document_id, "status": "processing", "queued": False}
    record.status = "processing"
    record.error_message = None
    job = KnowledgeIngestionJob(document_id=document_id, status="queued", stage="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        queue_backend = enqueue_index_job(background_tasks, document_id, KNOWLEDGE_FILES_DIR, job.job_id)
    except RuntimeError as exc:
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"document_id": document_id, "job_id": job.job_id, "status": "processing", "queued": True, "queue_backend": queue_backend}


@router.get("/admin/knowledge/files/{document_id}/status")
def get_knowledge_file_status(document_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    record = db.get(KnowledgeDocumentRecord, document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    job = db.query(KnowledgeIngestionJob).filter_by(document_id=document_id).order_by(KnowledgeIngestionJob.job_id.desc()).first()
    return {
        "document_id": record.document_id,
        "status": record.status,
        "version": record.version,
        "indexed_chunks": record.indexed_chunks,
        "embedding_provider": record.embedding_provider,
        "embedding_model": record.embedding_model,
        "embedding_dimensions": record.embedding_dimensions,
        "embedding_version": record.embedding_version,
        "error_message": record.error_message,
        "job": {
            "job_id": job.job_id,
            "status": job.status,
            "stage": job.stage,
            "indexed_chunks": job.indexed_chunks,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
        } if job else None,
    }


@router.get("/admin/knowledge/jobs/{job_id}")
def get_knowledge_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    job = db.get(KnowledgeIngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return {
        "job_id": job.job_id,
        "document_id": job.document_id,
        "status": job.status,
        "stage": job.stage,
        "indexed_chunks": job.indexed_chunks,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.post("/admin/knowledge/jobs/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_knowledge_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    job = db.get(KnowledgeIngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    if job.status in {"queued", "running"}:
        return {"job_id": job.job_id, "status": job.status, "queued": False}
    if job.retry_count >= job.max_retries:
        raise HTTPException(status_code=409, detail="Maximum retries reached")
    record = db.get(KnowledgeDocumentRecord, job.document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    record.status = "processing"
    record.error_message = None
    retry = KnowledgeIngestionJob(document_id=record.document_id, status="queued", stage="queued")
    db.add(retry)
    db.commit()
    db.refresh(retry)
    try:
        queue_backend = enqueue_index_job(background_tasks, record.document_id, KNOWLEDGE_FILES_DIR, retry.job_id)
    except RuntimeError as exc:
        retry.status = "failed"
        retry.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"job_id": retry.job_id, "document_id": record.document_id, "status": "processing", "queued": True, "queue_backend": queue_backend}
