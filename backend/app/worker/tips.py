import asyncio
import logging

from sqlalchemy import select

from app.extractors.ollama import generate_substitution_tips

logger = logging.getLogger(__name__)


async def run_substitution_tips():
    """Find all published recipes missing substitution tips and generate them."""
    from app.database import AsyncSessionLocal
    from app.models import Recipe

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Recipe).where(
                Recipe.published == True,  # noqa: E712
                Recipe.substitution_tips.is_(None),
            )
        )
        recipes = result.scalars().all()

    logger.info(f"Substitution tips job: {len(recipes)} recipes to process")

    for recipe in recipes:
        try:
            tips = await generate_substitution_tips(
                recipe.title,
                recipe.ingredients or [],
            )
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Recipe).where(Recipe.id == recipe.id))
                r = result.scalar_one_or_none()
                if r:
                    r.substitution_tips = tips
                    await db.commit()
            logger.info(f"Tips generated for '{recipe.title}': {len(tips)} tip(s)")
        except Exception as e:
            logger.error(f"Failed to generate tips for recipe {recipe.id}: {e}")
        await asyncio.sleep(1)

    logger.info("Substitution tips job complete")
