import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def start_scheduler():
    scheduler.add_job(
        _scrape_all_job,
        "interval",
        hours=settings.scrape_interval_hours,
        id="scrape_all",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(f"Scheduler started: scraping every {settings.scrape_interval_hours}h")


async def _scrape_all_job():
    from app.database import AsyncSessionLocal
    from app.models import ScrapeRun, ScrapeStatus
    from app.worker.runner import run_scrape_all_active

    async with AsyncSessionLocal() as db:
        run = ScrapeRun(source_id=None, status=ScrapeStatus.running)
        db.add(run)
        await db.commit()
        await db.refresh(run)
        await run_scrape_all_active(str(run.id), db)
