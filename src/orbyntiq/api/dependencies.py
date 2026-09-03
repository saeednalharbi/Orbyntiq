from functools import lru_cache

from fastapi import HTTPException, Request, status
from pymongo.asynchronous.database import AsyncDatabase

from orbyntiq.core.config import get_settings
from orbyntiq.core.mongodb import MongoDocument
from orbyntiq.llm import create_llm_provider
from orbyntiq.services import (
    LLMService,
    MultiAgentService,
    MultiAgentUnavailableError,
)


@lru_cache
def get_llm_service() -> LLMService:
    settings = get_settings()
    provider = create_llm_provider(settings)

    return LLMService(
        provider,
        metrics_enabled=(settings.observability_enabled and settings.metrics_enabled),
    )


async def close_llm_service() -> None:
    """Close and clear the cached LLM service, when initialized."""
    if get_llm_service.cache_info().currsize == 0:
        return

    service = get_llm_service()
    await service.close()
    get_llm_service.cache_clear()


def get_multi_agent_service(
    request: Request,
) -> MultiAgentService:
    service = getattr(
        request.app.state,
        "multi_agent_service",
        None,
    )

    if service is None:
        raise MultiAgentUnavailableError("Multi-agent service is unavailable.")

    return service


def get_mongodb_database(
    request: Request,
) -> AsyncDatabase[MongoDocument]:
    database = getattr(
        request.app.state,
        "mongodb_database",
        None,
    )

    available = bool(
        getattr(
            request.app.state,
            "mongodb_available",
            False,
        )
    )

    if database is None or not available:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("Execution history database is unavailable."),
        )

    return database
