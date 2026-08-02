import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Recipe
from app.schemas import RecipeOut, RecipeListItem, RecipesPage
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
