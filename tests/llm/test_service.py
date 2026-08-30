import asyncio
from collections.abc import Sequence
from typing import Any, Literal

import pytest
from pydantic import BaseModel

from orbyntiq.llm import (
    LLMInvalidResponseError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)
from orbyntiq.services import LLMService


class FakeProvider(LLMProvider):
    def __init__(
        self,
        *,
        text_response: str = "fake response",
        structured_response: str = '{"agent":"research"}',
    ) -> None:
        self.text_response = text_response
        self.structured_response = structured_response
        self.last_messages: Sequence[LLMMessage] = ()

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        self.last_messages = messages

        return LLMResponse(
            content=self.text_response,
            model="fake-model",
            prompt_tokens=10,
            completion_tokens=5,
        )

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        self.last_messages = messages

        return LLMResponse(
            content=self.structured_response,
            model="fake-model",
        )


class RoutingDecision(BaseModel):
    agent: Literal["research", "planner", "executor"]


def test_chat_uses_provider():
    provider = FakeProvider(
        text_response="ORBYNTIQ_TEST_OK",
    )
    service = LLMService(provider)

    response = asyncio.run(
        service.chat("Test request")
    )

    assert response.content == "ORBYNTIQ_TEST_OK"
    assert response.model == "fake-model"
    assert provider.last_messages[-1] == LLMMessage(
        role="user",
        content="Test request",
    )


def test_structured_chat_returns_validated_model():
    provider = FakeProvider(
        structured_response='{"agent":"research"}',
    )
    service = LLMService(provider)

    result = asyncio.run(
        service.chat_structured(
            "Choose an agent",
            RoutingDecision,
        )
    )

    assert result == RoutingDecision(agent="research")


def test_structured_chat_rejects_invalid_schema():
    provider = FakeProvider(
        structured_response='{"agent":"invalid-agent"}',
    )
    service = LLMService(provider)

    with pytest.raises(
        LLMInvalidResponseError,
        match="schema validation",
    ):
        asyncio.run(
            service.chat_structured(
                "Choose an agent",
                RoutingDecision,
            )
        )