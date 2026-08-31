from collections.abc import AsyncIterator, Sequence

import pytest

from orbyntiq.llm.messages import build_messages
from orbyntiq.llm.models import LLMMessage
from orbyntiq.services.llm_service import LLMService


class StreamingProvider:
    def __init__(self) -> None:
        self.received_messages: Sequence[LLMMessage] = ()

    async def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        self.received_messages = messages

        yield "Orbyntiq"
        yield " streaming"
        yield " works"


@pytest.mark.anyio
async def test_generate_stream_yields_provider_chunks() -> None:
    provider = StreamingProvider()
    service = LLMService(provider)  # type: ignore[arg-type]

    messages = build_messages("Hello")

    chunks = [
        chunk
        async for chunk in service.generate_stream(messages)
    ]

    assert chunks == [
        "Orbyntiq",
        " streaming",
        " works",
    ]


@pytest.mark.anyio
async def test_chat_stream_builds_messages_and_yields_chunks() -> None:
    provider = StreamingProvider()
    service = LLMService(provider)  # type: ignore[arg-type]

    chunks = [
        chunk
        async for chunk in service.chat_stream("Hello Orbyntiq")
    ]

    assert chunks == [
        "Orbyntiq",
        " streaming",
        " works",
    ]

    assert provider.received_messages[-1].role == "user"
    assert provider.received_messages[-1].content == "Hello Orbyntiq"
