import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.database import engine, AsyncSessionLocal, Base
from app.config import settings
from app.models import User
from app.auth import hash_password
from app.routers.auth import router as auth_router
from app.routers.sources import router as sources_router
from app.routers.scrape import router as scrape_router
from app.routers.recipes import admin_router as admin_recipes_router
from app.routers.recipes import public_router as public_recipes_router
from app.routers.public import router as public_router
from app.routers.skipped import router as skipped_router
from app.worker.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _seed_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        if result.first() is None:
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Seeded admin user: {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wait briefly for DB to be ready, then seed
    import asyncio
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            if attempt == 9:
                raise
            logger.warning(f"DB not ready (attempt {attempt+1}/10), retrying in 2s: {e}")
            await asyncio.sleep(2)

    await _seed_admin()
    start_scheduler()
    logger.info("Alphafood backend started")
    yield
    from app.worker.scheduler import scheduler
    scheduler.shutdown(wait=False)


app = FastAPI(title="Alphafood API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sources_router)
app.include_router(scrape_router)
app.include_router(admin_recipes_router)
app.include_router(public_recipes_router)
app.include_router(public_router)
app.include_router(skipped_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
