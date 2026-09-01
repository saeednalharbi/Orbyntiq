import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, Protocol

from prometheus_client import Counter, Gauge, Histogram

from orbyntiq.observability.spans import traced_span

AGENT_EXECUTIONS_TOTAL = Counter(
    "orbyntiq_agent_executions_total",
    "Total number of Orbyntiq multi-agent executions.",
    ("status",),
)

AGENT_EXECUTION_DURATION_SECONDS = Histogram(
    "orbyntiq_agent_execution_duration_seconds",
    "Duration of Orbyntiq multi-agent executions in seconds.",
    ("status",),
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
    ),
)

AGENT_EXECUTIONS_IN_PROGRESS = Gauge(
    "orbyntiq_agent_executions_in_progress",
    "Number of Orbyntiq multi-agent executions currently running.",
)

AGENT_STEPS_TOTAL = Counter(
    "orbyntiq_agent_steps_total",
    "Total number of Orbyntiq multi-agent workflow events.",
    ("event_type", "agent"),
)

AGENT_RESULTS_TOTAL = Counter(
    "orbyntiq_agent_results_total",
    "Total number of Orbyntiq agent results.",
    ("agent", "status"),
)

AGENT_ERRORS_TOTAL = Counter(
    "orbyntiq_agent_errors_total",
    "Total number of Orbyntiq multi-agent errors.",
    ("agent", "error_kind"),
)


KNOWN_AGENTS = {
    "supervisor",
    "research",
    "mcp",
    "general",
    "synthesizer",
}

KNOWN_EVENT_TYPES = {
    "execution_started",
    "routing_completed",
    "agent_result",
    "execution_completed",
    "execution_failed",
}

KNOWN_RESULT_STATUSES = {
    "success",
    "failed",
}


EventCallback = Callable[
    [dict[str, Any]],
    Awaitable[None],
]


class MultiAgentExecutor(Protocol):
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> Any: ...


def normalize_agent_name(value: object) -> str:
    if isinstance(value, str) and value in KNOWN_AGENTS:
        return value

    return "system"


def normalize_event_type(value: object) -> str:
    if (
        isinstance(value, str)
        and value in KNOWN_EVENT_TYPES
    ):
        return value

    return "unknown"


def normalize_result_status(value: object) -> str:
    if (
        isinstance(value, str)
        and value in KNOWN_RESULT_STATUSES
    ):
        return value

    return "unknown"


def record_agent_event(
    event: dict[str, Any],
) -> None:
    event_type = normalize_event_type(
        event.get("event_type")
    )

    agent = normalize_agent_name(
        event.get("agent_name")
    )

    AGENT_STEPS_TOTAL.labels(
        event_type=event_type,
        agent=agent,
    ).inc()

    if event_type == "agent_result":
        payload = event.get("payload")

        if not isinstance(payload, dict):
            payload = {}

        result_agent = normalize_agent_name(
            payload.get("agent")
            or event.get("agent_name")
        )

        result_status = normalize_result_status(
            payload.get("status")
        )

        AGENT_RESULTS_TOTAL.labels(
            agent=result_agent,
            status=result_status,
        ).inc()

        if result_status == "failed":
            AGENT_ERRORS_TOTAL.labels(
                agent=result_agent,
                error_kind="agent_result",
            ).inc()

    elif event_type == "execution_failed":
        AGENT_ERRORS_TOTAL.labels(
            agent=agent,
            error_kind="execution_failed",
        ).inc()


class InstrumentedMultiAgentService:
    """Add metrics and tracing around a MultiAgentService."""

    def __init__(
        self,
        service: MultiAgentExecutor,
        *,
        metrics_enabled: bool = True,
    ) -> None:
        self.service = service
        self.metrics_enabled = metrics_enabled

    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ) -> Any:
        status = "success"
        started_at = perf_counter()

        if self.metrics_enabled:
            AGENT_EXECUTIONS_IN_PROGRESS.inc()

        async def observed_callback(
            event: dict[str, Any],
        ) -> None:
            if self.metrics_enabled:
                record_agent_event(
                    event
                )

            if event_callback is not None:
                await event_callback(
                    event
                )

        callback = (
            observed_callback
            if self.metrics_enabled
            else event_callback
        )

        with traced_span(
            "agent.execute",
            tracer_name="orbyntiq.agents",
            attributes={
                "gen_ai.operation.name": "invoke_workflow",
                "gen_ai.workflow.name": "orbyntiq_multi_agent",
                "orbyntiq.agent.max_hops": max_hops,
            },
        ) as span:
            try:
                result = await self.service.execute(
                    user_query,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    max_hops=max_hops,
                    event_callback=callback,
                )

            except asyncio.CancelledError:
                status = "cancelled"
                raise

            except Exception:
                status = "error"
                raise

            else:
                route = getattr(
                    result,
                    "route",
                    None,
                )

                if route in {
                    "research",
                    "mcp",
                    "general",
                }:
                    span.set_attribute(
                        "orbyntiq.agent.route",
                        route,
                    )

                hop_count = getattr(
                    result,
                    "hop_count",
                    None,
                )

                if isinstance(
                    hop_count,
                    int,
                ):
                    span.set_attribute(
                        "orbyntiq.agent.hop_count",
                        hop_count,
                    )

                return result

            finally:
                span.set_attribute(
                    "orbyntiq.execution.status",
                    status,
                )

                if self.metrics_enabled:
                    duration = (
                        perf_counter()
                        - started_at
                    )

                    AGENT_EXECUTIONS_TOTAL.labels(
                        status=status,
                    ).inc()

                    AGENT_EXECUTION_DURATION_SECONDS.labels(
                        status=status,
                    ).observe(
                        duration
                    )

                    AGENT_EXECUTIONS_IN_PROGRESS.dec()
