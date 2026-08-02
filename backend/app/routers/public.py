from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Source
from app.schemas import SourceOut

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/sources", response_model=list[SourceOut])
async def list_public_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.active == True).order_by(Source.name))  # noqa: E712
    return result.scalars().all()
