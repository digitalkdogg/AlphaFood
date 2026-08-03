import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Source, Recipe, ScrapeRun, ScrapeStatus, SkippedUrl
from app.scrapers import get_adapter
from app.extractors.cleaner import extract_text
from app.extractors.ollama import extract_recipe, warmup as ollama_warmup
from app.config import settings

logger = logging.getLogger(__name__)


def _extract_image_url(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]
    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter and twitter.get("content"):
        return twitter["content"]
    return None


async def _process_url(
    url: str,
    source_id: uuid.UUID,
    adapter,
    run: ScrapeRun,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
):
    async with semaphore:
        try:
            html = await adapter.fetch_raw_html(url)

            image_url = _extract_image_url(html)
            cleaned = extract_text(html)
            if not cleaned:
                existing_skip = await db.execute(select(SkippedUrl).where(SkippedUrl.url == url))
                if not existing_skip.scalar_one_or_none():
                    db.add(SkippedUrl(source_id=source_id, url=url, reason="No extractable text"))
                run.recipes_skipped_non_recipe += 1
                return

            data, skip_reason = await extract_recipe(cleaned)
            if data is None:
                existing_skip = await db.execute(select(SkippedUrl).where(SkippedUrl.url == url))
                if not existing_skip.scalar_one_or_none():
                    db.add(SkippedUrl(source_id=source_id, url=url, reason=skip_reason))
                run.recipes_skipped_non_recipe += 1
                return

            now = datetime.now(timezone.utc)
            result = await db.execute(select(Recipe).where(Recipe.source_url == url))
            existing = result.scalar_one_or_none()

            if existing:
                existing.title = data.get("title", existing.title) or existing.title
                existing.ingredients = data.get("ingredients")
                existing.instructions = data.get("instructions")
                existing.prep_time = data.get("prep_time")
                existing.cook_time = data.get("cook_time")
                existing.servings = data.get("servings")
                existing.image_url = image_url or existing.image_url
                existing.is_dairy_free = data.get("is_dairy_free")
                existing.mentions_mammal_ingredients = data.get("mentions_mammal_ingredients", False)
                existing.needs_review = True
                existing.extracted_at = now
                existing.updated_at = now
                run.recipes_updated += 1
            else:
                recipe = Recipe(
                    source_id=source_id,
                    source_url=url,
                    title=data.get("title", "Untitled Recipe"),
                    ingredients=data.get("ingredients"),
                    instructions=data.get("instructions"),
                    prep_time=data.get("prep_time"),
                    cook_time=data.get("cook_time"),
                    servings=data.get("servings"),
                    image_url=image_url,
                    is_dairy_free=data.get("is_dairy_free"),
                    mentions_mammal_ingredients=data.get("mentions_mammal_ingredients", False),
                    needs_review=True,
                    published=False,
                    extracted_at=now,
                )
                db.add(recipe)
                run.recipes_added += 1

        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
        finally:
            if settings.ollama_cooldown_seconds > 0:
                await asyncio.sleep(settings.ollama_cooldown_seconds)


async def run_scrape_for_source(source_id: str, run_id: str, db: AsyncSession):
    result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == uuid.UUID(run_id)))
    run = result.scalar_one_or_none()
    if not run:
        return

    src_result = await db.execute(select(Source).where(Source.id == uuid.UUID(source_id)))
    source = src_result.scalar_one_or_none()
    if not source:
        run.status = ScrapeStatus.error
        run.error_message = "Source not found"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return

    try:
        await ollama_warmup()
        adapter = get_adapter(source)
        candidate_urls = await adapter.fetch_candidate_urls()

        # Deduplicate against existing recipes and previously skipped URLs
        existing_result = await db.execute(
            select(Recipe.source_url).where(Recipe.source_id == source.id)
        )
        existing_urls = {row[0] for row in existing_result.all()}

        skipped_result = await db.execute(
            select(SkippedUrl.url).where(SkippedUrl.source_id == source.id)
        )
        skipped_urls = {row[0] for row in skipped_result.all()}

        new_urls = [u for u in candidate_urls if u not in existing_urls and u not in skipped_urls]

        run.recipes_found = len(new_urls)
        await db.commit()

        semaphore = asyncio.Semaphore(settings.scrape_concurrency)
        tasks = [
            _process_url(url, source.id, adapter, run, db, semaphore)
            for url in new_urls
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        source.last_scraped_at = datetime.now(timezone.utc)
        run.status = ScrapeStatus.success
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as e:
        logger.error(f"Scrape failed for source {source_id}: {e}")
        run.status = ScrapeStatus.error
        run.error_message = str(e)
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()


async def run_scrape_all_active(run_id: str, db: AsyncSession):
    result = await db.execute(select(Source).where(Source.active == True))  # noqa: E712
    sources = result.scalars().all()

    for source in sources:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as source_db:
            run = ScrapeRun(source_id=source.id, status=ScrapeStatus.running)
            source_db.add(run)
            await source_db.commit()
            await source_db.refresh(run)
            await run_scrape_for_source(str(source.id), str(run.id), source_db)

    # Mark the global run complete
    global_run_result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == uuid.UUID(run_id)))
    global_run = global_run_result.scalar_one_or_none()
    if global_run:
        global_run.status = ScrapeStatus.success
        global_run.finished_at = datetime.now(timezone.utc)
        await db.commit()
