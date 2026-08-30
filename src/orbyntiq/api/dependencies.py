from functools import lru_cache

from orbyntiq.core.config import get_settings
from orbyntiq.llm import create_llm_provider
from orbyntiq.services import LLMService


@lru_cache
def get_llm_service() -> LLMService:
    settings = get_settings()
    provider = create_llm_provider(settings)

    return LLMService(provider)