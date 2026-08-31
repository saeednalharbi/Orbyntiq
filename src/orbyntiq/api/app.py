from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orbyntiq.api.error_handlers import register_error_handlers
from orbyntiq.api.routes.llm import router as llm_router
from orbyntiq.api.routes.websocket import router as websocket_router
from orbyntiq.core.config import get_settings
from orbyntiq.core.logging import configure_logging, get_logger
from orbyntiq.core.redis import (
    RedisUnavailableError,
    close_redis_client,
    create_redis_client,
    verify_redis_connection,
)

settings = get_settings()

configure_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_client = create_redis_client(settings)
    redis_connected = False

    app.state.redis = None
    app.state.redis_available = False

    try:
        try:
            await verify_redis_connection(redis_client)
        except RedisUnavailableError as exc:
            logger.warning(
                "Redis unavailable; application continuing in degraded mode: %s",
                exc,
            )
            await close_redis_client(redis_client)
        else:
            app.state.redis = redis_client
            app.state.redis_available = True
            redis_connected = True

            logger.info("Redis connection established")

        yield
    finally:
        if redis_connected:
            await close_redis_client(redis_client)
            logger.info("Redis connection closed")

        app.state.redis = None
        app.state.redis_available = False


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(llm_router)
app.include_router(websocket_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }
