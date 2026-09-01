from orbyntiq.core.config import Settings
from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.ollama import OllamaProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured LLM provider."""

    if settings.llm_provider == "ollama":
        return OllamaProvider(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            retry_base_delay=(settings.llm_retry_base_delay_seconds),
            max_concurrency=settings.llm_max_concurrency,
            max_connections=settings.llm_http_max_connections,
            max_keepalive_connections=(settings.llm_http_max_keepalive_connections),
            keepalive_expiry=(settings.llm_http_keepalive_expiry_seconds),
            keep_alive=settings.ollama_keep_alive,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
