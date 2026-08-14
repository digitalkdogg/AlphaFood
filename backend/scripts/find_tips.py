#!/usr/bin/env python3
"""
Find published recipes that have substitution tips.

Usage:
  docker-compose exec backend python scripts/find_tips.py
  docker-compose exec backend python scripts/find_tips.py --limit 25
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main(limit: int = 10):
    from app.database import AsyncSessionLocal
    from app.models import Recipe
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Recipe.id, Recipe.title, Recipe.substitution_tips)
            .where(Recipe.substitution_tips.isnot(None))
            .where(Recipe.published == True)  # noqa: E712
            .limit(limit)
        )
        rows = result.all()

    if not rows:
        print("No recipes with substitution tips found.")
        return

    print(f"Found {len(rows)} recipe(s) with substitution tips:\n")
    for row in rows:
        print(f"  {row.title}")
        print(f"  http://192.168.2.172:3003/recipes/{row.id}")
        for tip in (row.substitution_tips or []):
            print(f"  💡 {tip}")
        print()


if __name__ == "__main__":
    limit = 10
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        try:
            limit = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Invalid --limit value, using default of 10")

    asyncio.run(main(limit))
