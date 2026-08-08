import asyncio
import logging
import re
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

_cancel_flags: set[str] = set()


def request_cancel(run_id: str) -> None:
    _cancel_flags.add(run_id)


def _is_cancelled(run_id: str) -> bool:
    return run_id in _cancel_flags


def _to_int_minutes(val) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        m = re.search(r'\d+', val)
        return int(m.group()) if m else None
    return None


_VALID_CATEGORIES = {
    "breakfast", "lunch", "dinner", "snack", "dessert",
    "appetizer", "side dish", "soup", "salad", "drink",
}


def _parse_category(val) -> Optional[str]:
    if not val:
        return None
    cat = str(val).strip().lower()
    return cat if cat in _VALID_CATEGORIES else None


def _clean_ingredients(val) -> Optional[list]:
    if not isinstance(val, list):
        return None
    cleaned = [
        ing for ing in val
        if isinstance(ing, dict) and any(str(v).strip() for v in ing.values())
    ]
    return cleaned or None


def _to_str_list(val) -> Optional[list]:
    if val is None:
        return None
    if isinstance(val, list):
        return [str(item) for item in val if item is not None and str(item).strip()]
    return None


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
        if _is_cancelled(str(run.id)):
            return
        try:
            html = await adapter.fetch_raw_html(url)

            image_url = _extract_image_url(html)
            cleaned = extract_text(html)
            if not cleaned:
                async with db.begin_nested():
                    existing_skip = await db.execute(select(SkippedUrl).where(SkippedUrl.url == url))
                    if not existing_skip.scalar_one_or_none():
                        db.add(SkippedUrl(source_id=source_id, url=url, reason="No extractable text"))
                run.recipes_skipped_non_recipe += 1
                await db.commit()
                return

            data, skip_reason = await extract_recipe(cleaned)
            if data is None:
                async with db.begin_nested():
                    existing_skip = await db.execute(select(SkippedUrl).where(SkippedUrl.url == url))
                    if not existing_skip.scalar_one_or_none():
                        db.add(SkippedUrl(source_id=source_id, url=url, reason=skip_reason))
                run.recipes_skipped_non_recipe += 1
                await db.commit()
                return

            now = datetime.now(timezone.utc)

            mammal_status = str(data.get("mammal_status", "safe")).lower()
            if mammal_status not in ("safe", "questionable", "contains_mammal"):
                mammal_status = "safe"

            if mammal_status == "contains_mammal":
                async with db.begin_nested():
                    existing_skip = await db.execute(select(SkippedUrl).where(SkippedUrl.url == url))
                    if not existing_skip.scalar_one_or_none():
                        db.add(SkippedUrl(source_id=source_id, url=url, reason="Contains mammal ingredients"))
                run.recipes_skipped_non_recipe += 1
                await db.commit()
                return

            mentions_mammal = mammal_status == "questionable"
            if mammal_status == "questionable":
                flagged = [
                    str(i).strip() for i in data.get("questionable_ingredients", [])
                    if str(i).strip()
                ]
                if flagged:
                    ingredient_list = ", ".join(flagged)
                    disclaimer = (
                        f"The following ingredient(s) may be mammal-derived depending on the brand: "
                        f"{ingredient_list}. Verify that plant-based versions are used before serving "
                        f"to someone with Alpha-Gal Syndrome."
                    )
                else:
                    disclaimer = (
                        "One or more ingredients in this recipe may be mammal-derived depending on the "
                        "brand used. Verify that plant-based versions are used before serving to someone "
                        "with Alpha-Gal Syndrome."
                    )
            else:
                disclaimer = None

            raw_servings = data.get("servings")
            servings = str(raw_servings) if raw_servings is not None else None

            async with db.begin_nested():
                result = await db.execute(select(Recipe).where(Recipe.source_url == url))
                existing = result.scalar_one_or_none()

                if existing:
                    existing.title = data.get("title", existing.title) or existing.title
                    existing.ingredients = _clean_ingredients(data.get("ingredients"))
                    existing.instructions = _to_str_list(data.get("instructions"))
                    existing.prep_time = _to_int_minutes(data.get("prep_time"))
                    existing.cook_time = _to_int_minutes(data.get("cook_time"))
                    existing.servings = servings
                    existing.image_url = image_url or existing.image_url
                    existing.is_dairy_free = data.get("is_dairy_free")
                    existing.meal_category = _parse_category(data.get("meal_category"))
                    existing.mentions_mammal_ingredients = mentions_mammal
                    existing.disclaimer = disclaimer
                    existing.needs_review = True
                    existing.extracted_at = now
                    existing.updated_at = now
                    run.recipes_updated += 1
                else:
                    recipe = Recipe(
                        source_id=source_id,
                        source_url=url,
                        title=data.get("title", "Untitled Recipe"),
                        ingredients=_clean_ingredients(data.get("ingredients")),
                        instructions=_to_str_list(data.get("instructions")),
                        prep_time=_to_int_minutes(data.get("prep_time")),
                        cook_time=_to_int_minutes(data.get("cook_time")),
                        servings=servings,
                        image_url=image_url,
                        is_dairy_free=data.get("is_dairy_free"),
                        meal_category=_parse_category(data.get("meal_category")),
                        mentions_mammal_ingredients=mentions_mammal,
                        disclaimer=disclaimer,
                        needs_review=True,
                        published=False,
                        extracted_at=now,
                    )
                    db.add(recipe)
                    run.recipes_added += 1

            await db.commit()

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
        run_id_str = str(run.id)
        if _is_cancelled(run_id_str):
            _cancel_flags.discard(run_id_str)
            run.status = ScrapeStatus.cancelled
        else:
            run.status = ScrapeStatus.success
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as e:
        logger.error(f"Scrape failed for source {source_id}: {e}")
        run.status = ScrapeStatus.error
        run.error_message = str(e)
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()


async def _ensure_manual_source(db: AsyncSession):
    from app.models import Source, ScraperType
    src_result = await db.execute(select(Source).where(Source.name == "Manual Imports"))
    source = src_result.scalar_one_or_none()
    if not source:
        source = Source(
            name="Manual Imports",
            url="manual://import",
            scraper_type=ScraperType.single_page,
            active=False,
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)
    return source


async def run_import_background(url: str, run_id: str) -> None:
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        run_result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == uuid.UUID(run_id)))
        run = run_result.scalar_one_or_none()
        if not run:
            return
        try:
            source = await _ensure_manual_source(db)
            result = await import_single_url(url, source.id, db)
            if result["status"] == "imported":
                run.recipes_added = 1
            elif result["status"] == "updated":
                run.recipes_updated = 1
            else:
                run.recipes_skipped_non_recipe = 1
                run.error_message = result["reason"]
            run.status = ScrapeStatus.success if result["status"] != "skipped" else ScrapeStatus.partial
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.error(f"Background import failed for {url}: {e}")
            run.status = ScrapeStatus.error
            run.error_message = str(e)
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()


async def import_single_url(url: str, source_id: uuid.UUID, db: AsyncSession) -> dict:
    """Fetch, extract, and save a single recipe URL. Returns {status, reason, recipe}."""

    from app.scrapers.base import HEADERS
    import httpx

    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        return {"status": "skipped", "reason": f"Could not fetch URL: {e}", "recipe": None}

    image_url = _extract_image_url(html)
    cleaned = extract_text(html)
    if not cleaned:
        return {"status": "skipped", "reason": "No extractable text found on that page", "recipe": None}

    await ollama_warmup()
    data, skip_reason = await extract_recipe(cleaned)
    if data is None:
        return {"status": "skipped", "reason": skip_reason or "Ollama did not find a recipe on that page", "recipe": None}

    mammal_status = str(data.get("mammal_status", "safe")).lower()
    if mammal_status not in ("safe", "questionable", "contains_mammal"):
        mammal_status = "safe"

    if mammal_status == "contains_mammal":
        return {"status": "skipped", "reason": "Contains mammal ingredients — recipe not safe for Alpha-Gal Syndrome", "recipe": None}

    mentions_mammal = mammal_status == "questionable"
    if mammal_status == "questionable":
        flagged = [
            str(i).strip() for i in data.get("questionable_ingredients", [])
            if str(i).strip()
        ]
        if flagged:
            ingredient_list = ", ".join(flagged)
            disclaimer = (
                f"The following ingredient(s) may be mammal-derived depending on the brand: "
                f"{ingredient_list}. Verify that plant-based versions are used before serving "
                f"to someone with Alpha-Gal Syndrome."
            )
        else:
            disclaimer = (
                "One or more ingredients in this recipe may be mammal-derived depending on the "
                "brand used. Verify that plant-based versions are used before serving to someone "
                "with Alpha-Gal Syndrome."
            )
    else:
        disclaimer = None

    now = datetime.now(timezone.utc)
    raw_servings = data.get("servings")
    servings = str(raw_servings) if raw_servings is not None else None

    async with db.begin_nested():
        existing_result = await db.execute(select(Recipe).where(Recipe.source_url == url))
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.title = data.get("title") or existing.title
            existing.ingredients = _clean_ingredients(data.get("ingredients"))
            existing.instructions = _to_str_list(data.get("instructions"))
            existing.prep_time = _to_int_minutes(data.get("prep_time"))
            existing.cook_time = _to_int_minutes(data.get("cook_time"))
            existing.servings = servings
            existing.image_url = image_url or existing.image_url
            existing.is_dairy_free = data.get("is_dairy_free")
            existing.meal_category = _parse_category(data.get("meal_category"))
            existing.mentions_mammal_ingredients = mentions_mammal
            existing.disclaimer = disclaimer
            existing.needs_review = True
            existing.extracted_at = now
            existing.updated_at = now
            await db.commit()
            return {"status": "updated", "reason": None, "recipe": existing}
        else:
            recipe = Recipe(
                source_id=source_id,
                source_url=url,
                title=data.get("title", "Untitled Recipe"),
                ingredients=_clean_ingredients(data.get("ingredients")),
                instructions=_to_str_list(data.get("instructions")),
                prep_time=_to_int_minutes(data.get("prep_time")),
                cook_time=_to_int_minutes(data.get("cook_time")),
                servings=servings,
                image_url=image_url,
                is_dairy_free=data.get("is_dairy_free"),
                meal_category=_parse_category(data.get("meal_category")),
                mentions_mammal_ingredients=mentions_mammal,
                disclaimer=disclaimer,
                needs_review=True,
                published=False,
                extracted_at=now,
            )
            db.add(recipe)
            await db.commit()
            await db.refresh(recipe)
            return {"status": "imported", "reason": None, "recipe": recipe}


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
