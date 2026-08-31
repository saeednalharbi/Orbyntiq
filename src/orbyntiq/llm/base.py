from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from typing import Any

from orbyntiq.llm.models import LLMMessage, LLMResponse


class LLMProvider(ABC):
    """Base contract for all Orbyntiq LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        """Generate a normal text response."""

    @abstractmethod
    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        """Generate a response constrained to a JSON schema."""

    def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        """Stream text chunks from the provider."""

        del messages
        raise NotImplementedError(
            "Streaming is not supported by this LLM provider."
        )
