from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Observability
    observability_enabled: bool = True
    metrics_enabled: bool = True
    tracing_enabled: bool = True

    otel_service_name: str = "orbyntiq-api"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_enabled: bool = False
    otel_exporter_otlp_insecure: bool = True
    otel_export_timeout_seconds: float = 5.0
    otel_trace_sample_ratio: float = 1.0

    metrics_path: str = "/metrics"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ORBYNTIQ_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Orbyntiq"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    websocket_idle_timeout_seconds: float = Field(default=120.0, gt=0)

    llm_provider: Literal["ollama"] = "ollama"
    llm_model: str = "qwen3:4b-instruct"
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=10)
    llm_retry_base_delay_seconds: float = Field(default=0.5, ge=0)
    llm_max_concurrency: int = Field(default=2, ge=1, le=32)
    llm_http_max_connections: int = Field(default=4, ge=1, le=100)
    llm_http_max_keepalive_connections: int = Field(
        default=2,
        ge=1,
        le=100,
    )
    llm_http_keepalive_expiry_seconds: float = Field(default=30.0, gt=0)
    ollama_keep_alive: str = "30m"

    embedding_provider: Literal["ollama"] = "ollama"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dimension: int = Field(default=1024, gt=0)
    embedding_timeout_seconds: float = Field(default=60.0, gt=0)

    # RAG runtime performance defaults.
    # These remain configurable so larger/deeper
    # research modes can use higher budgets later.
    rag_retrieval_limit: int = Field(
        default=3,
        ge=1,
        le=50,
    )
    rag_chunk_character_limit: int = Field(
        default=700,
        ge=100,
        le=20_000,
    )
    rag_max_output_tokens: int = Field(
        default=160,
        ge=32,
        le=4_096,
    )

    redis_url: str = "redis://localhost:6379/0"
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0)
    redis_operation_timeout_seconds: float = Field(default=2.0, gt=0)

    redis_session_ttl_seconds: int = Field(default=86_400, gt=0)
    redis_conversation_ttl_seconds: int = Field(default=21_600, gt=0)
    redis_agent_state_ttl_seconds: int = Field(default=3_600, gt=0)
    redis_cache_ttl_seconds: int = Field(default=300, gt=0)

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "orbyntiq"
    mongodb_connect_timeout_seconds: float = Field(default=3.0, gt=0)
    mongodb_server_selection_timeout_seconds: float = Field(default=3.0, gt=0)
    mongodb_operation_timeout_seconds: float = Field(default=5.0, gt=0)

    qdrant_url: str = "http://localhost:6333"
    qdrant_grpc_port: int = Field(default=6334, ge=1, le=65_535)
    qdrant_prefer_grpc: bool = False
    qdrant_timeout_seconds: float = Field(default=5.0, gt=0)
    qdrant_collection: str = "orbyntiq_documents"

    knowledge_storage_dir: str = "data/knowledge"
    knowledge_max_upload_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
