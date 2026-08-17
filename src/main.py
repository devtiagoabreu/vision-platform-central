import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Vision Platform Central starting | central_id=%s",
        settings.central_id,
    )
    yield
    logger.info("Vision Platform Central shutting down")


app = FastAPI(
    title="Vision Platform Central",
    version="0.1.0",
    description="Central collector service for GeoFissura Vision Platform",
    lifespan=lifespan,
)

app.include_router(router)
