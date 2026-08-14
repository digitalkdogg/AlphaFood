#!/usr/bin/env python3
"""
Regenerate substitution tips for one or all recipes.

Usage:
  # Regenerate tips for a single recipe by ID:
  docker-compose exec backend python scripts/regenerate_tips.py <recipe-id>

  # Regenerate tips for ALL published recipes (clears existing tips first):
  docker-compose exec backend python scripts/regenerate_tips.py --all
"""
import asyncio
import sys
import uuid

from sqlalchemy import select, update


async def regenerate_one(recipe_id: str):
    from app.database import AsyncSessionLocal
    from app.models import Recipe
    from app.extractors.ollama import generate_substitution_tips

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
        recipe = result.scalar_one_or_none()
        if not recipe:
            print(f"Recipe not found: {recipe_id}")
            return

        print(f"Regenerating tips for: {recipe.title}")
        tips = await generate_substitution_tips(recipe.title, recipe.ingredients or [])
        recipe.substitution_tips = tips
        await db.commit()

        if tips:
            print(f"Generated {len(tips)} tip(s):")
            for tip in tips:
                print(f"  💡 {tip}")
        else:
            print("No substitution tips needed for this recipe.")


async def regenerate_all():
    from app.database import AsyncSessionLocal
    from app.models import Recipe
    from app.worker.tips import run_substitution_tips

    print("Clearing all existing tips...")
    async with AsyncSessionLocal() as db:
        await db.execute(update(Recipe).values(substitution_tips=None))
        await db.commit()

    print("Running tip generation for all published recipes...")
    await run_substitution_tips()
    print("Done.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        asyncio.run(regenerate_all())
    else:
        asyncio.run(regenerate_one(arg))


if __name__ == "__main__":
    main()
