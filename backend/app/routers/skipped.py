import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SkippedUrl
from app.schemas import SkippedUrlOut, SkippedUrlsPage
from app.deps import get_current_user

router = APIRouter(prefix="/api/admin/skipped", tags=["admin-skipped"])


@router.get("/", response_model=SkippedUrlsPage)
async def list_skipped_urls(
    source_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(SkippedUrl)
    if source_id:
        q = q.where(SkippedUrl.source_id == source_id)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(SkippedUrl.skipped_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()
    return SkippedUrlsPage(items=items, total=total, page=page, limit=limit)


@router.delete("/{skipped_id}", status_code=204)
async def remove_skipped_url(
    skipped_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(SkippedUrl).where(SkippedUrl.id == skipped_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()
