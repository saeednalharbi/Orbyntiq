from functools import lru_cache

from fastapi import Request

from orbyntiq.core.config import get_settings
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

    return LLMService(provider)


def get_multi_agent_service(
    request: Request,
) -> MultiAgentService:
    service = getattr(
        request.app.state,
        "multi_agent_service",
        None,
    )

    if service is None:
        raise MultiAgentUnavailableError(
            "Multi-agent service is unavailable."
        )

    return service
