import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.collector.local_client import LocalClient
from src.collector.sync import collect_from_local
from src.config.settings import settings
from src.storage.database import SessionLocal, create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

_poll_task: asyncio.Task | None = None


async def _poll_loop():
    interval_s = max(settings.collector_interval_ms / 1000, 30)
    while True:
        try:
            client = LocalClient()
            db = SessionLocal()
            try:
                result = collect_from_local(client=client, db=db)
                if result.get("observations_collected", 0) > 0:
                    logger.info("Poll cycle: %s", result)
            finally:
                db.close()
        except Exception as e:
            logger.error("Poll loop error: %s", e)
        await asyncio.sleep(interval_s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poll_task
    logger.info(
        "Vision Platform Central starting | central_id=%s",
        settings.central_id,
    )
    create_tables()
    logger.info("Database tables verified")
    _poll_task = asyncio.create_task(_poll_loop())
    yield
    _poll_task.cancel()
    logger.info("Vision Platform Central shutting down")


app = FastAPI(
    title="Vision Platform Central",
    version="0.1.0",
    description="Central collector service for GeoFissura Vision Platform",
    lifespan=lifespan,
)

app.include_router(router)
