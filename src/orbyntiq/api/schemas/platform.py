from typing import Literal

from pydantic import BaseModel

ComponentState = Literal[
    "healthy",
    "degraded",
    "unavailable",
    "configured",
    "disabled",
]

PlatformState = Literal[
    "healthy",
    "degraded",
]


class PlatformComponentStatus(BaseModel):
    status: ComponentState
    detail: str | None = None


class LLMComponentStatus(PlatformComponentStatus):
    provider: str
    model: str


class MCPComponentStatus(PlatformComponentStatus):
    retriever_configured: bool
    rag_configured: bool


class ObservabilityComponentStatus(PlatformComponentStatus):
    metrics_enabled: bool
    tracing_enabled: bool


class PlatformComponents(BaseModel):
    api: PlatformComponentStatus
    redis: PlatformComponentStatus
    mongodb: PlatformComponentStatus
    qdrant: PlatformComponentStatus
    multi_agent: PlatformComponentStatus
    mcp: MCPComponentStatus
    llm: LLMComponentStatus
    observability: ObservabilityComponentStatus


class PlatformRuntimeConfig(BaseModel):
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int

    qdrant_collection: str

    rag_retrieval_limit: int
    rag_chunk_character_limit: int
    rag_max_output_tokens: int

    llm_max_concurrency: int
    ollama_keep_alive: str

    metrics_path: str
    otel_service_name: str
    otel_exporter_enabled: bool


class PlatformStatusResponse(BaseModel):
    status: PlatformState
    service: str
    environment: str
    components: PlatformComponents
    runtime: PlatformRuntimeConfig
