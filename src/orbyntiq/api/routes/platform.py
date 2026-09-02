from fastapi import APIRouter, Request

from orbyntiq.api.schemas.platform import (
    LLMComponentStatus,
    MCPComponentStatus,
    ObservabilityComponentStatus,
    PlatformComponents,
    PlatformComponentStatus,
    PlatformStatusResponse,
)
from orbyntiq.core.config import get_settings
from orbyntiq.mcp.runtime import get_mcp_services

router = APIRouter(
    prefix="/api/v1/platform",
    tags=["platform"],
)

settings = get_settings()


def _dependency_status(
    available: bool,
    *,
    healthy_detail: str,
    unavailable_detail: str,
) -> PlatformComponentStatus:
    if available:
        return PlatformComponentStatus(
            status="healthy",
            detail=healthy_detail,
        )

    return PlatformComponentStatus(
        status="unavailable",
        detail=unavailable_detail,
    )


@router.get(
    "/status",
    response_model=PlatformStatusResponse,
)
def platform_status(
    request: Request,
) -> PlatformStatusResponse:
    redis_available = bool(
        getattr(
            request.app.state,
            "redis_available",
            False,
        )
    )

    mongodb_available = bool(
        getattr(
            request.app.state,
            "mongodb_available",
            False,
        )
    )

    qdrant_available = bool(
        getattr(
            request.app.state,
            "qdrant_available",
            False,
        )
    )

    multi_agent_available = (
        getattr(
            request.app.state,
            "multi_agent_service",
            None,
        )
        is not None
    )

    mcp_services = get_mcp_services()

    retriever_configured = (
        mcp_services.retriever is not None
    )

    rag_configured = (
        mcp_services.rag_service is not None
    )

    if retriever_configured and rag_configured:
        mcp_status = "healthy"
        mcp_detail = (
            "MCP retrieval and RAG services are configured."
        )
    elif retriever_configured or rag_configured:
        mcp_status = "degraded"
        mcp_detail = (
            "MCP is only partially configured."
        )
    else:
        mcp_status = "unavailable"
        mcp_detail = (
            "MCP retrieval and RAG services are unavailable."
        )

    if settings.observability_enabled:
        observability_status = "configured"
        observability_detail = (
            "Observability is enabled."
        )
    else:
        observability_status = "disabled"
        observability_detail = (
            "Observability is disabled."
        )

    components = PlatformComponents(
        api=PlatformComponentStatus(
            status="healthy",
            detail="FastAPI application is responding.",
        ),
        redis=_dependency_status(
            redis_available,
            healthy_detail="Redis is connected.",
            unavailable_detail="Redis is unavailable.",
        ),
        mongodb=_dependency_status(
            mongodb_available,
            healthy_detail="MongoDB is connected.",
            unavailable_detail="MongoDB is unavailable.",
        ),
        qdrant=_dependency_status(
            qdrant_available,
            healthy_detail="Qdrant is connected.",
            unavailable_detail="Qdrant is unavailable.",
        ),
        multi_agent=_dependency_status(
            multi_agent_available,
            healthy_detail=(
                "Multi-agent orchestration is configured."
            ),
            unavailable_detail=(
                "Multi-agent orchestration is unavailable."
            ),
        ),
        mcp=MCPComponentStatus(
            status=mcp_status,
            detail=mcp_detail,
            retriever_configured=retriever_configured,
            rag_configured=rag_configured,
        ),
        llm=LLMComponentStatus(
            status="configured",
            detail=(
                "Local LLM runtime is configured. "
                "This endpoint does not perform an inference probe."
            ),
            provider=settings.llm_provider,
            model=settings.llm_model,
        ),
        observability=ObservabilityComponentStatus(
            status=observability_status,
            detail=observability_detail,
            metrics_enabled=(
                settings.observability_enabled
                and settings.metrics_enabled
            ),
            tracing_enabled=(
                settings.observability_enabled
                and settings.tracing_enabled
            ),
        ),
    )

    critical_states = (
        components.redis.status,
        components.mongodb.status,
        components.qdrant.status,
        components.multi_agent.status,
        components.mcp.status,
    )

    overall_status = (
        "healthy"
        if all(
            state == "healthy"
            for state in critical_states
        )
        else "degraded"
    )

    return PlatformStatusResponse(
        status=overall_status,
        service=settings.app_name,
        environment=settings.environment,
        components=components,
    )
