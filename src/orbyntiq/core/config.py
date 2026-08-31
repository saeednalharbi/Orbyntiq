from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
