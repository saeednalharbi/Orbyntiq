from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

from orbyntiq.llm.base import LLMProvider
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

        return response_model.model_validate_json(response.content)