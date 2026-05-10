from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import logging
    from app.services.notification import run_daily_notifications

    logger = logging.getLogger(__name__)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_notifications, CronTrigger(hour=9, minute=0))
    scheduler.start()
    try:
        await run_daily_notifications()
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_daily_notifications failed at startup (will retry at 09:00): %s", exc)
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
