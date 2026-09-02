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

    async def generate_with_options(
        self,
        messages: Sequence[LLMMessage],
        *,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate with optional runtime constraints."""

        del max_tokens

        return await self.generate(messages)

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        """Generate a response constrained to a JSON schema."""

        del messages, schema

        raise NotImplementedError("Structured generation is not supported by this LLM provider.")

    def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        """Stream text chunks from the provider."""

        del messages
        raise NotImplementedError("Streaming is not supported by this LLM provider.")

    async def close(self) -> None:  # noqa: B027
        """Release resources owned by the provider."""
