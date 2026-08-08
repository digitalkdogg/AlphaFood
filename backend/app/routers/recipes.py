import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Recipe, ScrapeRun, ScrapeStatus
from app.schemas import RecipeOut, RecipeListItem, RecipesPage, ImportRequest, ImportResult
from app.deps import get_current_user

admin_router = APIRouter(prefix="/api/admin/recipes", tags=["admin-recipes"])
public_router = APIRouter(prefix="/api/recipes", tags=["recipes"])


# ── Admin endpoints ──────────────────────────────────────────────────────────

@admin_router.get("/", response_model=RecipesPage)
async def admin_list_recipes(
    needs_review: Optional[bool] = None,
    published: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(Recipe)
    if needs_review is not None:
        q = q.where(Recipe.needs_review == needs_review)
    if published is not None:
        q = q.where(Recipe.published == published)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Recipe.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()
    return RecipesPage(items=items, total=total, page=page, limit=limit)


@admin_router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe_admin(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@admin_router.put("/{recipe_id}/publish", response_model=RecipeOut)
async def publish_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.needs_review = False
    recipe.published = True
    recipe.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@admin_router.put("/{recipe_id}/reject", response_model=RecipeOut)
async def reject_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.published = False
    recipe.needs_review = True
    recipe.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@admin_router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.delete(recipe)
    await db.commit()


@admin_router.post("/import", response_model=ImportResult)
async def import_recipe(
    body: ImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from app.worker.runner import _ensure_manual_source, run_import_background
    source = await _ensure_manual_source(db)
    run = ScrapeRun(source_id=source.id, status=ScrapeStatus.running, recipes_found=1)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(run_import_background, body.url.strip(), str(run.id))
    return ImportResult(status="queued", run_id=str(run.id))


@admin_router.post("/{recipe_id}/reprocess", response_model=RecipeOut)
async def reprocess_recipe(
    recipe_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    background_tasks.add_task(_do_reprocess, str(recipe_id))
    recipe.needs_review = True
    recipe.published = False
    recipe.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(recipe)
    return recipe


async def _do_reprocess(recipe_id: str):
    from app.database import AsyncSessionLocal
    from app.worker.runner import _process_url, _extract_image_url
    from app.extractors.cleaner import extract_text
    from app.extractors.ollama import extract_recipe
    from app.scrapers.base import HEADERS
    from app.worker.runner import _to_int_minutes, _to_str_list
    import httpx

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
        recipe = result.scalar_one_or_none()
        if not recipe:
            return
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
                r = await client.get(recipe.source_url)
                r.raise_for_status()
                html = r.text

            image_url = _extract_image_url(html)
            cleaned = extract_text(html)
            if not cleaned:
                return

            data, _ = await extract_recipe(cleaned)
            if data is None:
                return

            now = datetime.now(timezone.utc)
            raw_mammal = data.get("mentions_mammal_ingredients", False)
            mentions_mammal = bool(raw_mammal) if not isinstance(raw_mammal, bool) else raw_mammal
            raw_servings = data.get("servings")

            recipe.title = data.get("title") or recipe.title
            recipe.ingredients = data.get("ingredients")
            recipe.instructions = _to_str_list(data.get("instructions"))
            recipe.prep_time = _to_int_minutes(data.get("prep_time"))
            recipe.cook_time = _to_int_minutes(data.get("cook_time"))
            recipe.servings = str(raw_servings) if raw_servings is not None else None
            recipe.image_url = image_url or recipe.image_url
            recipe.is_dairy_free = data.get("is_dairy_free")
            recipe.mentions_mammal_ingredients = mentions_mammal
            recipe.needs_review = True
            recipe.published = False
            recipe.extracted_at = now
            recipe.updated_at = now
            await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Reprocess failed for {recipe_id}: {e}")


# ── Public endpoints ─────────────────────────────────────────────────────────

@public_router.get("/", response_model=RecipesPage)
async def list_recipes(
    q: Optional[str] = None,
    source_id: Optional[uuid.UUID] = None,
    is_dairy_free: Optional[bool] = None,
    max_time: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Recipe).where(Recipe.published == True)  # noqa: E712

    if q:
        search_term = f"%{q}%"
        query = query.where(Recipe.title.ilike(search_term))

    if source_id:
        query = query.where(Recipe.source_id == source_id)

    if is_dairy_free is not None:
        query = query.where(Recipe.is_dairy_free == is_dairy_free)

    if max_time is not None:
        query = query.where(
            (Recipe.prep_time + Recipe.cook_time) <= max_time
        )

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.order_by(Recipe.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return RecipesPage(items=items, total=total, page=page, limit=limit)


@public_router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.published == True)  # noqa: E712
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe
