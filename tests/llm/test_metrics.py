import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from prometheus_client import REGISTRY, generate_latest
from pydantic import BaseModel

from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.errors import LLMInvalidResponseError
from orbyntiq.llm.models import LLMMessage, LLMResponse
from orbyntiq.services.llm_service import LLMService

MESSAGES = (
    LLMMessage(
        role="user",
        content="Metrics test",
    ),
)


def _sample_value(
    name: str,
    labels: dict[str, str],
) -> float:
    value = REGISTRY.get_sample_value(
        name,
        labels,
    )

    if value is None:
        return 0.0

    return float(value)


class StructuredResult(BaseModel):
    answer: str


class MetricsProvider(LLMProvider):
    def __init__(
        self,
        *,
        fail_generate: bool = False,
        fail_stream: bool = False,
        structured_content: str = (
            '{"answer":"ok"}'
        ),
    ) -> None:
        self.model = "metrics-model"
        self.fail_generate = fail_generate
        self.fail_stream = fail_stream
        self.structured_content = (
            structured_content
        )

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        assert messages

        if self.fail_generate:
            raise RuntimeError(
                "Simulated generate failure."
            )

        return LLMResponse(
            content="metrics response",
            model=self.model,
            prompt_tokens=7,
            completion_tokens=3,
        )

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        assert messages
        assert schema

        return LLMResponse(
            content=self.structured_content,
            model=self.model,
            prompt_tokens=4,
            completion_tokens=2,
        )

    async def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        assert messages

        if self.fail_stream:
            raise RuntimeError(
                "Simulated stream failure."
            )

        yield "first"
        yield "second"


class HangingMetricsProvider(MetricsProvider):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()

    async def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        assert messages

        self.started.set()

        await asyncio.sleep(60)

        if False:
            yield "never"


@pytest.mark.anyio
async def test_generate_records_request_and_tokens() -> None:
    service = LLMService(
        MetricsProvider()
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "generate",
        "status": "success",
    }

    before_requests = _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    )

    before_duration = _sample_value(
        "orbyntiq_llm_request_duration_seconds_count",
        labels,
    )

    prompt_labels = {
        "provider": "other",
        "model": "metrics-model",
        "token_type": "prompt",
    }

    completion_labels = {
        "provider": "other",
        "model": "metrics-model",
        "token_type": "completion",
    }

    before_prompt = _sample_value(
        "orbyntiq_llm_tokens_total",
        prompt_labels,
    )

    before_completion = _sample_value(
        "orbyntiq_llm_tokens_total",
        completion_labels,
    )

    response = await service.generate(
        MESSAGES
    )

    assert response.content == "metrics response"

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    ) == before_requests + 1

    assert _sample_value(
        "orbyntiq_llm_request_duration_seconds_count",
        labels,
    ) == before_duration + 1

    assert _sample_value(
        "orbyntiq_llm_tokens_total",
        prompt_labels,
    ) == before_prompt + 7

    assert _sample_value(
        "orbyntiq_llm_tokens_total",
        completion_labels,
    ) == before_completion + 3


@pytest.mark.anyio
async def test_generate_records_error() -> None:
    service = LLMService(
        MetricsProvider(
            fail_generate=True,
        )
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "generate",
        "status": "error",
    }

    before = _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    )

    with pytest.raises(
        RuntimeError,
        match="generate failure",
    ):
        await service.generate(MESSAGES)

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_structured_records_success() -> None:
    service = LLMService(
        MetricsProvider()
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "structured",
        "status": "success",
    }

    before = _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    )

    result = await service.chat_structured(
        "Return structured data.",
        StructuredResult,
    )

    assert result == StructuredResult(
        answer="ok"
    )

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_structured_validation_failure_records_error() -> None:
    service = LLMService(
        MetricsProvider(
            structured_content='{"wrong":"value"}',
        )
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "structured",
        "status": "error",
    }

    before = _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    )

    with pytest.raises(
        LLMInvalidResponseError
    ):
        await service.chat_structured(
            "Return structured data.",
            StructuredResult,
        )

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_stream_records_chunks_and_duration() -> None:
    service = LLMService(
        MetricsProvider()
    )

    request_labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "stream",
        "status": "success",
    }

    stream_labels = {
        "provider": "other",
        "model": "metrics-model",
        "status": "success",
    }

    chunk_labels = {
        "provider": "other",
        "model": "metrics-model",
    }

    before_requests = _sample_value(
        "orbyntiq_llm_requests_total",
        request_labels,
    )

    before_streams = _sample_value(
        "orbyntiq_llm_streams_total",
        stream_labels,
    )

    before_chunks = _sample_value(
        "orbyntiq_llm_stream_chunks_total",
        chunk_labels,
    )

    chunks = [
        chunk
        async for chunk in service.generate_stream(
            MESSAGES
        )
    ]

    assert chunks == [
        "first",
        "second",
    ]

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        request_labels,
    ) == before_requests + 1

    assert _sample_value(
        "orbyntiq_llm_streams_total",
        stream_labels,
    ) == before_streams + 1

    assert _sample_value(
        "orbyntiq_llm_stream_chunks_total",
        chunk_labels,
    ) == before_chunks + 2


@pytest.mark.anyio
async def test_stream_records_error() -> None:
    service = LLMService(
        MetricsProvider(
            fail_stream=True,
        )
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "status": "error",
    }

    before = _sample_value(
        "orbyntiq_llm_streams_total",
        labels,
    )

    with pytest.raises(
        RuntimeError,
        match="stream failure",
    ):
        async for _ in service.generate_stream(
            MESSAGES
        ):
            pass

    assert _sample_value(
        "orbyntiq_llm_streams_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_stream_cancellation_is_recorded() -> None:
    provider = HangingMetricsProvider()
    service = LLMService(provider)

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "status": "cancelled",
    }

    before = _sample_value(
        "orbyntiq_llm_streams_total",
        labels,
    )

    async def consume() -> None:
        async for _ in service.generate_stream(
            MESSAGES
        ):
            pass

    task = asyncio.create_task(
        consume()
    )

    await provider.started.wait()

    task.cancel()

    with pytest.raises(
        asyncio.CancelledError
    ):
        await task

    assert _sample_value(
        "orbyntiq_llm_streams_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_metrics_can_be_disabled() -> None:
    service = LLMService(
        MetricsProvider(),
        metrics_enabled=False,
    )

    labels = {
        "provider": "other",
        "model": "metrics-model",
        "operation": "generate",
        "status": "success",
    }

    before = _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    )

    await service.generate(MESSAGES)

    assert _sample_value(
        "orbyntiq_llm_requests_total",
        labels,
    ) == before


def test_llm_metrics_are_registered() -> None:
    body = generate_latest(
        REGISTRY
    ).decode("utf-8")

    expected = (
        "orbyntiq_llm_requests_total",
        "orbyntiq_llm_request_duration_seconds",
        "orbyntiq_llm_requests_in_progress",
        "orbyntiq_llm_tokens_total",
        "orbyntiq_llm_streams_total",
        "orbyntiq_llm_stream_chunks_total",
        "orbyntiq_llm_stream_duration_seconds",
    )

    for metric in expected:
        assert metric in body
