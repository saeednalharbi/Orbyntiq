from collections.abc import AsyncIterator, Sequence
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.errors import LLMInvalidResponseError
from orbyntiq.llm.messages import build_messages
from orbyntiq.llm.models import LLMMessage, LLMResponse
from orbyntiq.llm.prompts import BASE_SYSTEM_PROMPT

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMService:
    """Application service for interacting with language models."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        return await self.provider.generate(messages)

    async def generate_stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        """Stream text chunks from the configured LLM provider."""

        async for chunk in self.provider.stream(messages):
            yield chunk

    async def chat(
        self,
        prompt: str,
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> LLMResponse:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        return await self.generate(messages)

    async def chat_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> AsyncIterator[str]:
        """Build chat messages and stream the generated response."""

        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        async for chunk in self.generate_stream(messages):
            yield chunk

    async def chat_structured(
        self,
        prompt: str,
        response_model: type[ResponseModelT],
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> ResponseModelT:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        response = await self.provider.generate_structured(
            messages,
            response_model.model_json_schema(),
        )

        try:
            return response_model.model_validate_json(response.content)
        except ValidationError as exc:
            raise LLMInvalidResponseError(
                "LLM structured response failed schema validation."
            ) from exc
