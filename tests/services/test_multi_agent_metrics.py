import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from prometheus_client import REGISTRY, generate_latest

from orbyntiq.observability.agent_metrics import (
    InstrumentedMultiAgentService,
)

EventCallback = Callable[
    [dict[str, Any]],
    Awaitable[None],
]


def _sample_value(
    name: str,
    labels: dict[str, str] | None = None,
) -> float:
    value = REGISTRY.get_sample_value(
        name,
        labels or {},
    )

    if value is None:
        return 0.0

    return float(value)


class SuccessfulService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> object:
        del request_id
        del conversation_id
        del max_hops

        assert user_query == "Explain embeddings."

        events = [
            {
                "event_type": "execution_started",
                "agent_name": "supervisor",
                "payload": {},
            },
            {
                "event_type": "routing_completed",
                "agent_name": "supervisor",
                "payload": {
                    "route": "general",
                },
            },
            {
                "event_type": "agent_result",
                "agent_name": "general",
                "payload": {
                    "agent": "general",
                    "status": "success",
                },
            },
            {
                "event_type": "agent_result",
                "agent_name": "synthesizer",
                "payload": {
                    "agent": "synthesizer",
                    "status": "success",
                },
            },
            {
                "event_type": "execution_completed",
                "agent_name": "synthesizer",
                "payload": {},
            },
        ]

        if event_callback is not None:
            for event in events:
                await event_callback(event)

        return object()


class FailingService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> object:
        del user_query
        del request_id
        del conversation_id
        del max_hops

        if event_callback is not None:
            await event_callback(
                {
                    "event_type": "execution_started",
                    "agent_name": "supervisor",
                    "payload": {},
                }
            )

            await event_callback(
                {
                    "event_type": "execution_failed",
                    "agent_name": "supervisor",
                    "payload": {
                        "error": "failure",
                    },
                }
            )

        raise RuntimeError("simulated failure")


class FailedAgentResultService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> object:
        del user_query
        del request_id
        del conversation_id
        del max_hops

        if event_callback is not None:
            await event_callback(
                {
                    "event_type": "agent_result",
                    "agent_name": "research",
                    "payload": {
                        "agent": "research",
                        "status": "failed",
                    },
                }
            )

        return object()


class CancelledService:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> object:
        del user_query
        del request_id
        del conversation_id
        del max_hops
        del event_callback

        self.started.set()

        await asyncio.sleep(60)

        return object()


@pytest.mark.anyio
async def test_execution_records_success_and_duration() -> None:
    service = InstrumentedMultiAgentService(
        SuccessfulService()
    )

    labels = {
        "status": "success",
    }

    before_total = _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    )

    before_duration = _sample_value(
        "orbyntiq_agent_execution_duration_seconds_count",
        labels,
    )

    before_progress = _sample_value(
        "orbyntiq_agent_executions_in_progress"
    )

    await service.execute(
        "Explain embeddings."
    )

    assert _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    ) == before_total + 1

    assert _sample_value(
        "orbyntiq_agent_execution_duration_seconds_count",
        labels,
    ) == before_duration + 1

    assert _sample_value(
        "orbyntiq_agent_executions_in_progress"
    ) == before_progress


@pytest.mark.anyio
async def test_agent_steps_and_results_are_recorded() -> None:
    service = InstrumentedMultiAgentService(
        SuccessfulService()
    )

    step_labels = {
        "event_type": "agent_result",
        "agent": "general",
    }

    result_labels = {
        "agent": "general",
        "status": "success",
    }

    before_steps = _sample_value(
        "orbyntiq_agent_steps_total",
        step_labels,
    )

    before_results = _sample_value(
        "orbyntiq_agent_results_total",
        result_labels,
    )

    await service.execute(
        "Explain embeddings."
    )

    assert _sample_value(
        "orbyntiq_agent_steps_total",
        step_labels,
    ) == before_steps + 1

    assert _sample_value(
        "orbyntiq_agent_results_total",
        result_labels,
    ) == before_results + 1


@pytest.mark.anyio
async def test_execution_error_is_recorded() -> None:
    service = InstrumentedMultiAgentService(
        FailingService()
    )

    execution_labels = {
        "status": "error",
    }

    error_labels = {
        "agent": "supervisor",
        "error_kind": "execution_failed",
    }

    before_execution = _sample_value(
        "orbyntiq_agent_executions_total",
        execution_labels,
    )

    before_errors = _sample_value(
        "orbyntiq_agent_errors_total",
        error_labels,
    )

    with pytest.raises(
        RuntimeError,
        match="simulated failure",
    ):
        await service.execute("Fail.")

    assert _sample_value(
        "orbyntiq_agent_executions_total",
        execution_labels,
    ) == before_execution + 1

    assert _sample_value(
        "orbyntiq_agent_errors_total",
        error_labels,
    ) == before_errors + 1


@pytest.mark.anyio
async def test_failed_agent_result_records_error() -> None:
    service = InstrumentedMultiAgentService(
        FailedAgentResultService()
    )

    result_labels = {
        "agent": "research",
        "status": "failed",
    }

    error_labels = {
        "agent": "research",
        "error_kind": "agent_result",
    }

    before_result = _sample_value(
        "orbyntiq_agent_results_total",
        result_labels,
    )

    before_error = _sample_value(
        "orbyntiq_agent_errors_total",
        error_labels,
    )

    await service.execute("Fail agent.")

    assert _sample_value(
        "orbyntiq_agent_results_total",
        result_labels,
    ) == before_result + 1

    assert _sample_value(
        "orbyntiq_agent_errors_total",
        error_labels,
    ) == before_error + 1


@pytest.mark.anyio
async def test_execution_cancellation_is_recorded() -> None:
    inner = CancelledService()

    service = InstrumentedMultiAgentService(
        inner
    )

    labels = {
        "status": "cancelled",
    }

    before = _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    )

    task = asyncio.create_task(
        service.execute("Cancel.")
    )

    await inner.started.wait()

    task.cancel()

    with pytest.raises(
        asyncio.CancelledError
    ):
        await task

    assert _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    ) == before + 1


@pytest.mark.anyio
async def test_original_event_callback_is_preserved() -> None:
    captured: list[dict[str, Any]] = []

    async def capture(
        event: dict[str, Any],
    ) -> None:
        captured.append(event)

    service = InstrumentedMultiAgentService(
        SuccessfulService()
    )

    await service.execute(
        "Explain embeddings.",
        event_callback=capture,
    )

    assert [
        event["event_type"]
        for event in captured
    ] == [
        "execution_started",
        "routing_completed",
        "agent_result",
        "agent_result",
        "execution_completed",
    ]


@pytest.mark.anyio
async def test_agent_metrics_can_be_disabled() -> None:
    service = InstrumentedMultiAgentService(
        SuccessfulService(),
        metrics_enabled=False,
    )

    labels = {
        "status": "success",
    }

    before = _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    )

    await service.execute(
        "Explain embeddings."
    )

    assert _sample_value(
        "orbyntiq_agent_executions_total",
        labels,
    ) == before


def test_agent_metrics_are_registered() -> None:
    body = generate_latest(
        REGISTRY
    ).decode("utf-8")

    expected = (
        "orbyntiq_agent_executions_total",
        "orbyntiq_agent_execution_duration_seconds",
        "orbyntiq_agent_executions_in_progress",
        "orbyntiq_agent_steps_total",
        "orbyntiq_agent_results_total",
        "orbyntiq_agent_errors_total",
    )

    for metric in expected:
        assert metric in body
