import asyncio
from typing import Any

import pytest

from orbyntiq.services.multi_agent_service import (
    MultiAgentService,
)


class SuccessfulGraph:
    async def ainvoke(
        self,
        input,
    ) -> dict[str, Any]:
        return {
            "request_id": input["request_id"],
            "route": "general",
            "route_reason": "Direct LLM request",
            "final_response": "Embeddings are vectors.",
            "sources": [],
            "errors": [],
            "agent_results": [
                {
                    "agent": "general",
                    "status": "success",
                    "content": "Embeddings are vectors.",
                    "metadata": {},
                    "sources": [],
                    "error": None,
                },
                {
                    "agent": "synthesizer",
                    "status": "success",
                    "content": "Embeddings are vectors.",
                    "metadata": {
                        "mode": "passthrough",
                    },
                    "sources": [],
                    "error": None,
                },
            ],
            "hop_count": 3,
        }


class CancelledGraph:
    async def ainvoke(
        self,
        input,
    ) -> dict[str, Any]:
        del input
        raise asyncio.CancelledError


def test_multi_agent_service_emits_workflow_events() -> None:
    async def scenario() -> None:
        events: list[dict[str, Any]] = []

        async def capture(
            event: dict[str, Any],
        ) -> None:
            events.append(event)

        service = MultiAgentService(
            SuccessfulGraph(),  # type: ignore[arg-type]
        )

        execution = await service.execute(
            "Explain embeddings.",
            request_id="event-test",
            event_callback=capture,
        )

        assert execution.route == "general"

        assert [
            event["event_type"]
            for event in events
        ] == [
            "execution_started",
            "routing_completed",
            "agent_result",
            "agent_result",
            "execution_completed",
        ]

        assert [
            event["sequence"]
            for event in events
        ] == [
            0,
            1,
            2,
            3,
            4,
        ]

        execution_ids = {
            event["execution_id"]
            for event in events
        }

        assert execution_ids == {
            execution.execution_id
        }

        assert all(
            event["request_id"] == "event-test"
            for event in events
        )

        assert (
            events[1]["payload"]["route"]
            == "general"
        )

        assert (
            events[-1]["payload"]["final_response"]
            == "Embeddings are vectors."
        )

    asyncio.run(scenario())


def test_multi_agent_service_emits_failure_when_cancelled() -> None:
    async def scenario() -> None:
        events: list[dict[str, Any]] = []

        async def capture(
            event: dict[str, Any],
        ) -> None:
            events.append(event)

        service = MultiAgentService(
            CancelledGraph(),  # type: ignore[arg-type]
        )

        with pytest.raises(
            asyncio.CancelledError
        ):
            await service.execute(
                "Cancel this.",
                request_id="cancel-event-test",
                event_callback=capture,
            )

        assert [
            event["event_type"]
            for event in events
        ] == [
            "execution_started",
            "execution_failed",
        ]

        assert events[1]["sequence"] == 1

        assert (
            events[1]["payload"]["error"]
            == "Multi-agent execution cancelled."
        )

    asyncio.run(scenario())
