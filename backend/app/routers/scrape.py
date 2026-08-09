import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional

from app.database import get_db
from app.models import ScrapeRun, Source, ScrapeStatus
from app.schemas import ScrapeRunOut, ScrapeStartResponse
from app.deps import get_current_user

router = APIRouter(prefix="/api/admin/scrape", tags=["admin-scrape"])


@router.post("/all", response_model=ScrapeStartResponse)
async def scrape_all_sources(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    run = ScrapeRun(source_id=None, status=ScrapeStatus.running)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    run_id = str(run.id)
    background_tasks.add_task(_do_scrape_all, run_id)
    return ScrapeStartResponse(run_id=run_id)


async def _do_scrape_all(run_id: str):
    from app.database import AsyncSessionLocal
    from app.worker.runner import run_scrape_all_active
    async with AsyncSessionLocal() as db:
        await run_scrape_all_active(run_id, db)


@router.get("/runs", response_model=list[ScrapeRunOut])
async def list_runs(
    source_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(100)
    if source_id:
        q = q.where(ScrapeRun.source_id == source_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/runs/{run_id}/cancel", response_model=ScrapeRunOut)
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from app.worker.runner import request_cancel
    result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    if run.status != ScrapeStatus.running:
        raise HTTPException(status_code=400, detail="Run is not currently running")
    request_cancel(str(run_id))
    return run


@router.get("/runs/{run_id}", response_model=ScrapeRunOut)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scrape run not found")
    return run


@router.get("/schedule")
async def get_schedule(_=Depends(get_current_user)):
    from app.worker.scheduler import scheduler
    from app.config import settings
    job = scheduler.get_job("scrape_all")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "next_run_at": next_run,
        "interval_hours": settings.scrape_interval_hours,
    }
