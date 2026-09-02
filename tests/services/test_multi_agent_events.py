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

        assert [event["event_type"] for event in events] == [
            "execution_started",
            "routing_completed",
            "agent_result",
            "agent_result",
            "execution_completed",
        ]

        assert [event["sequence"] for event in events] == [
            0,
            1,
            2,
            3,
            4,
        ]

        execution_ids = {event["execution_id"] for event in events}

        assert execution_ids == {execution.execution_id}

        assert all(event["request_id"] == "event-test" for event in events)

        assert events[1]["payload"]["route"] == "general"

        assert events[-1]["payload"]["final_response"] == "Embeddings are vectors."

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

        with pytest.raises(asyncio.CancelledError):
            await service.execute(
                "Cancel this.",
                request_id="cancel-event-test",
                event_callback=capture,
            )

        assert [event["event_type"] for event in events] == [
            "execution_started",
            "execution_failed",
        ]

        assert events[1]["sequence"] == 1

        assert events[1]["payload"]["error"] == "Multi-agent execution cancelled."

    asyncio.run(scenario())


class StreamingGraph:
    async def astream(
        self,
        input,
        *,
        stream_mode,
    ):
        assert stream_mode == "values"

        yield dict(input)

        supervisor_state = {
            **input,
            "route": "research",
            "route_reason": "Knowledge request",
            "sources": [],
            "errors": [],
            "agent_results": [],
            "hop_count": 1,
        }

        yield supervisor_state

        research_result = {
            "agent": "research",
            "status": "success",
            "content": "Grounded answer.",
            "metadata": {
                "source_count": 1,
            },
            "sources": [
                {
                    "file_name": "platform.txt",
                }
            ],
            "error": None,
        }

        research_state = {
            **supervisor_state,
            "sources": research_result["sources"],
            "agent_results": [research_result],
            "hop_count": 2,
        }

        yield research_state

        synthesizer_result = {
            "agent": "synthesizer",
            "status": "success",
            "content": "Grounded answer.",
            "metadata": {
                "mode": "passthrough",
            },
            "sources": research_result["sources"],
            "error": None,
        }

        yield {
            **research_state,
            "final_response": "Grounded answer.",
            "agent_results": [
                research_result,
                synthesizer_result,
            ],
            "hop_count": 3,
        }


def test_multi_agent_service_streams_live_graph_events() -> None:
    async def scenario() -> None:
        events: list[dict[str, Any]] = []

        async def capture(
            event: dict[str, Any],
        ) -> None:
            events.append(event)

        service = MultiAgentService(
            StreamingGraph(),  # type: ignore[arg-type]
        )

        execution = await service.execute(
            "Use my knowledge.",
            request_id="live-event-test",
            event_callback=capture,
        )

        assert execution.route == "research"

        assert [event["event_type"] for event in events] == [
            "execution_started",
            "routing_completed",
            "agent_started",
            "agent_result",
            "agent_result",
            "execution_completed",
        ]

        assert [event["sequence"] for event in events] == [
            0,
            1,
            2,
            3,
            4,
            5,
        ]

        assert events[1]["payload"]["route"] == "research"

        assert events[2]["agent_name"] == "research"

        assert events[3]["agent_name"] == "research"

        assert events[-1]["payload"]["final_response"] == "Grounded answer."

    asyncio.run(scenario())
