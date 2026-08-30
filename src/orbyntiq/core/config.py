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

    llm_provider: Literal["ollama"] = "ollama"
    llm_model: str = "qwen3:4b-instruct"
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=10)
    llm_retry_base_delay_seconds: float = Field(default=0.5, ge=0)

@lru_cache
def get_settings() -> Settings:
    return Settings()

